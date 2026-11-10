# Footprints Discovery

Footprints Discovery is a local UI for exploring AI discovery and working with model passports. Footprints collects file evidence and metadata. [Forkit Core](https://github.com/Forkit-Dev-Core/Forkit_Dev) creates the passport, assigns its ID, and verifies its identity.

## Create and verify a model passport

From a checkout of this repository, use Python 3.10 or later and Git to install the pinned Core dependency in a virtual environment.

```sh
python -m venv .venv
```

Activate it with `.venv\Scripts\Activate.ps1` in PowerShell or `source .venv/bin/activate` on macOS or Linux. Then run:

```sh
python -m pip install -r requirements.txt
python serve.py
```

Open [Footprints on this device](http://127.0.0.1:8765/footprints/). Choose a nonempty model artifact up to 64 MiB, enter its name, version, creator, task, and architecture, then select **Create and verify passport**. To try it with a small public artifact, use the [Tiny Random BERT safetensors file](https://huggingface.co/hf-internal-testing/tiny-random-bert/blob/f171d7baecaf37b5da5a3616d8833b9969753535/model.safetensors).

For that example, enter `tiny-random-bert`, `1.0.0`, and `Hugging Face`. Choose **Other** for the task and **Encoder only** for the architecture. The version is a local passport label for the example.

The browser computes SHA-256 from the selected file. Core receives the hash, filename, and form metadata, and stores a passport in `~/.forkit/footprints`. Use `--registry-root` to choose another local directory. Verification checks that Core can derive the same ID from the stored identity fields. The UI displays the submitted file hash and the returned passport ID.

You can also open `index.html` directly to try the simulated discovery example. That example uses fictional signals and does not scan your device. Each result lists the signals behind it, a short reason for each, and a confidence score. The [evidence format](docs/evidence-format.md) describes the input, the signal catalog, and the results.

## Run the checks

Use Node.js 24 for the discovery tests. The Python integration test uses Core's real local registry in a temporary directory.

```sh
node --test
python -m pip install httpx
python -m unittest discover -s tests
```

## Contribute

Pick a [good first issue](https://github.com/Forkit-Dev-Core/footprints/labels/good%20first%20issue), report a problem in [Issues](https://github.com/Forkit-Dev-Core/footprints/issues), or suggest an idea in [Discussions](https://github.com/Forkit-Dev-Core/footprints/discussions). You can contribute code, tests, documentation, or examples. The [contributor guide](CONTRIBUTING.md) explains how to get a change reviewed.

Use the [community page](docs/community.md) to share demos, writeups, workshop resources, and lessons others can build on.

## License

This project is available under the [MIT License](LICENSE). Forkit Core is a separate dependency under its [Apache 2.0 license](https://github.com/Forkit-Dev-Core/Forkit_Dev/blob/main/LICENSE).
