"""Build and smoke-test the portable Windows x64 Footprints archive."""

import argparse
import hashlib
import shutil
import socket
import subprocess
import sys
import sysconfig
import tempfile
import time
import urllib.request
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

    subprocess.run(
        [
            sys.executable, "-m", "pip", "--isolated", "install", "--disable-pip-version-check",
            "--no-compile", "--index-url", "https://pypi.org/simple",
            "--target", str(runtime / "site-packages"), "-r", str(ROOT / "requirements.txt"),
        ],
        cwd=ROOT,
        check=True,
    )
    (runtime / "python314._pth").write_text(
        "python314.zip\n.\nsite-packages\n../app\n", encoding="ascii"
    )


def smoke_test(bundle: Path, stage: Path) -> None:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]

    command = [
        str(bundle / "runtime" / "python.exe"), "-B", str(bundle / "app" / "serve.py"),
        "--port", str(port), "--registry-root", str(stage / "test registry"),
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
                    time.sleep(0.25)
            else:
                raise RuntimeError("The bundled Footprints page did not become ready.")

            for script in ("discovery.js", "passport.js"):
                with urllib.request.urlopen(f"{origin}/footprints/{script}", timeout=2) as response:
                    if not response.read():
                        raise RuntimeError(f"The bundled {script} is empty.")
        finally:
            if server.poll() is None:
                server.terminate()
            server.wait(timeout=10)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="Directory for the ZIP and SHA-256 file")
    output = parser.parse_args().output.resolve()
    if sysconfig.get_platform() != "win-amd64" or sys.version_info[:2] != (3, 14):
        parser.error("Build with x64 Python 3.14 on Windows.")

    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="footprints-", dir=output) as temp:
        stage = Path(temp)
        bundle = stage / "Footprints"
        app = bundle / "app"
        runtime = bundle / "runtime"
        app.mkdir(parents=True)
        install_runtime(runtime, stage)

        for filename in ("serve.py", "index.html", "discovery.js", "passport.js"):
            shutil.copyfile(ROOT / filename, app / filename)
        shutil.copyfile(ROOT / "LICENSE", bundle / "LICENSE")
        for filename in ("Start Footprints.cmd", "Start here.txt", "sample-artifact.txt"):
            shutil.copyfile(ROOT / "scripts" / filename, bundle / filename)
        smoke_test(bundle, stage)

        # pip's console scripts reference the builder's Python. The bundle uses its own launcher.
        scripts = (runtime / "site-packages" / "bin", runtime / "site-packages" / "Scripts")
        with ZipFile(stage / ASSET, "w", compression=ZIP_DEFLATED) as archive:
            for path in sorted(bundle.rglob("*")):
                if path.is_file() and not any(path.is_relative_to(folder) for folder in scripts):
                    archive.write(path, path.relative_to(stage))

        digest = hashlib.sha256((stage / ASSET).read_bytes()).hexdigest()
        checksum = stage / f"{ASSET}.sha256"
        checksum.write_text(f"{digest}  {ASSET}\n", encoding="ascii")
        (stage / ASSET).replace(output / ASSET)
        checksum.replace(output / checksum.name)
        print(f"Windows bundle smoke test passed. Wrote {ASSET} and its SHA-256 file.")


if __name__ == "__main__":
    main()
