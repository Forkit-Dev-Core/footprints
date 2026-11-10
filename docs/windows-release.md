# Windows preview releases

The Windows x64 download is a portable ZIP. It contains the public Footprints app, the pinned public Forkit Core dependency, and the Python runtime. People can extract it and run the launcher without installing Python or Git.

## Prepare a release

1. After the change passes checks and is reviewed and merged, open **Actions → Windows package → Run workflow** and select the reviewed ref to release.
2. Download the `footprints-windows-release-files` artifact from the successful run. It contains `Footprints-Windows-x64.zip` and `Footprints-Windows-x64.zip.sha256`.
3. Compare the checksum with `Get-FileHash .\Footprints-Windows-x64.zip -Algorithm SHA256`. Extract the ZIP into a fresh folder. Start it with **Start Footprints.cmd**, open the local page, and create and verify a passport using a synthetic model file.
4. Create a draft GitHub Release tagged at the reviewed commit. Attach the ZIP and its checksum as separate release assets. Publish after a maintainer has tried the extracted package.

To build locally, use Windows and x64 Python 3.14.10.

```powershell
python scripts/build_windows.py .\release-files
```

The builder and embedded runtime both use Python 3.14.10. The build verifies the embedded runtime against the [Python release checksum](https://www.python.org/downloads/release/python-31410/), checks the hashes in the Windows build and runtime requirement files, and extracts the finished ZIP into a fresh directory. It then checks the browser assets and creates and verifies a passport for the bundled sample on loopback.

When updating a dependency, update its version and artifact hash in the relevant requirement file and run the Windows package workflow. The Forkit Core source archive and its hash are shared with source installs through the root requirement file.

## Website download count

Link the community page directly to the Windows ZIP in a published GitHub Release. Read the asset's `download_count` from the [GitHub Releases API](https://docs.github.com/en/rest/releases/assets) on the server or at build time. Show it as **Windows ZIP downloads** for that release. Keep the ZIP's filename stable and count that asset only.
