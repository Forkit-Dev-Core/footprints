"""Build and smoke-test the portable Windows x64 Footprints archive."""

import argparse
import hashlib
import json
import re
import shutil
import socket
import subprocess
import sys
import sysconfig
import tempfile
import time
import urllib.request
import venv
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
PYTHON_VERSION = "3.14.10"
PYTHON_SHA256 = "90905e64a840557d8c1bc4f5b74db3d7ee85e3ffb217611cac1c7813acea4159"
ASSET = "Footprints-Windows-x64.zip"


def install_runtime(runtime: Path, stage: Path) -> None:
    filename = f"python-{PYTHON_VERSION}-embed-amd64.zip"
    url = f"https://www.python.org/ftp/python/{PYTHON_VERSION}/{filename}"
    runtime_archive = stage / filename
    with urllib.request.urlopen(url, timeout=60) as download, runtime_archive.open("wb") as file:
        shutil.copyfileobj(download, file)
    if hashlib.sha256(runtime_archive.read_bytes()).hexdigest() != PYTHON_SHA256:
        raise SystemExit("The downloaded Python runtime failed its SHA-256 check.")
    with ZipFile(runtime_archive) as archive:
        archive.extractall(runtime)

    build_env = stage / "build-env"
    venv.EnvBuilder(with_pip=True).create(build_env)
    pip = [
        str(build_env / "Scripts" / "python.exe"), "-m", "pip", "--isolated", "install",
        "--disable-pip-version-check", "--index-url", "https://pypi.org/simple", "--require-hashes",
    ]
    subprocess.run(
        [*pip, "-r", "scripts/windows-build-requirements.txt"],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        [
            *pip, "--no-build-isolation", "--no-compile",
            "--target", str(runtime / "site-packages"), "-r", "scripts/windows-runtime-requirements.txt",
        ],
        cwd=ROOT,
        check=True,
    )
    (runtime / "python314._pth").write_text(
        "python314.zip\n.\nsite-packages\n../app\n", encoding="ascii"
    )


def verify_sample_passport(origin: str, bundle: Path, registry: Path) -> None:
    sample = bundle / "sample-artifact.txt"
    digest = hashlib.sha256(sample.read_bytes()).hexdigest()
    payload = {
        "name": "footprints-sample",
        "version": "1.0.0",
        "creator": {"name": "Footprints example"},
        "task_type": "other",
        "architecture": "other",
        "artifact_hash": digest,
        "artifact_files": [sample.name],
    }
    create = urllib.request.Request(
        origin + "/models",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Origin": origin},
        method="POST",
    )
    with urllib.request.urlopen(create, timeout=5) as response:
        if response.status != 201:
            raise RuntimeError("The extracted app did not create the sample passport.")
        passport_id = json.load(response)["id"]
    if not re.fullmatch(r"[0-9a-f]{64}", passport_id):
        raise RuntimeError("The extracted app returned an invalid passport ID.")

    verify = urllib.request.Request(
        f"{origin}/verify/{passport_id}", headers={"Origin": origin}, method="POST"
    )
    with urllib.request.urlopen(verify, timeout=5) as response:
        result = json.load(response)
        if result["valid"] is not True or result["stored_id"] != passport_id:
            raise RuntimeError("The extracted app did not verify the sample passport.")
    stored = json.loads((registry / "models" / f"{passport_id}.json").read_text(encoding="utf-8"))
    if stored["artifact_hash"] != digest:
        raise RuntimeError("The stored passport hash does not match the bundled sample.")


def smoke_test(bundle: Path, stage: Path) -> None:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]

    registry = stage / "test registry"
    command = [
        str(bundle / "runtime" / "python.exe"), "-B", str(bundle / "app" / "serve.py"),
        "--port", str(port), "--registry-root", str(registry),
    ]
    with subprocess.Popen(command, cwd=bundle) as server:
        try:
            origin = f"http://127.0.0.1:{port}"
            for _ in range(40):
                if server.poll() is not None:
                    raise RuntimeError("The bundled server exited during startup.")
                try:
                    with urllib.request.urlopen(origin + "/footprints/", timeout=1) as response:
                        if b'id="passport-form"' in response.read():
                            break
                except OSError:
                    pass
                time.sleep(0.25)
            else:
                raise RuntimeError("The bundled Footprints page did not become ready.")

            for asset in ("passport.js", "styles.css"):
                with urllib.request.urlopen(f"{origin}/footprints/{asset}", timeout=2) as response:
                    if not response.read():
                        raise RuntimeError(f"The bundled {asset} is empty.")
            verify_sample_passport(origin, bundle, registry)
        finally:
            if server.poll() is None:
                server.terminate()
            server.wait(timeout=10)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="Directory for the ZIP and SHA-256 file")
    output = parser.parse_args().output.resolve()
    expected_version = tuple(int(part) for part in PYTHON_VERSION.split("."))
    if sysconfig.get_platform() != "win-amd64" or sys.version_info[:3] != expected_version:
        parser.error(f"Build with x64 Python {PYTHON_VERSION} on Windows.")

    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="footprints-", dir=output) as temp:
        stage = Path(temp)
        bundle = stage / "Footprints"
        app = bundle / "app"
        runtime = bundle / "runtime"
        app.mkdir(parents=True)
        install_runtime(runtime, stage)

        for filename in ("serve.py", "index.html", "passport.js", "styles.css"):
            shutil.copyfile(ROOT / filename, app / filename)
        shutil.copyfile(ROOT / "LICENSE", bundle / "LICENSE")
        for filename in ("Start Footprints.cmd", "Start here.txt", "sample-artifact.txt"):
            shutil.copyfile(ROOT / "scripts" / filename, bundle / filename)
        # pip's console scripts reference the builder's Python. The bundle uses its own launcher.
        scripts = (runtime / "site-packages" / "bin", runtime / "site-packages" / "Scripts")
        zip_path = stage / ASSET
        with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as archive:
            for path in sorted(bundle.rglob("*")):
                if path.is_file() and not any(path.is_relative_to(folder) for folder in scripts):
                    archive.write(path, path.relative_to(stage))

        extracted = stage / "extracted package"
        with ZipFile(zip_path) as archive:
            archive.extractall(extracted)
        smoke_test(extracted / "Footprints", stage)

        digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
        checksum = stage / f"{ASSET}.sha256"
        checksum.write_text(f"{digest}  {ASSET}\n", encoding="ascii", newline="\n")
        zip_path.replace(output / ASSET)
        checksum.replace(output / checksum.name)
        print(f"Created and verified a sample passport from the extracted {ASSET}.")


if __name__ == "__main__":
    main()
