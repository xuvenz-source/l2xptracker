# Windows development and portable builds

## Run from source

Use 64-bit Python 3.12, Tcl/Tk and a trusted Windows Tesseract installation containing English language data (`tessdata/eng.traineddata`).

From the repository root, run `Start Tracker.bat`, or install `requirements.txt` in a virtual environment and run `python tracker.py`.

## Regression tests

```sh
python -m unittest discover -s tests -v
```

Run from the repository root so application modules and sibling test fixtures resolve. Windows is required for full native HUD/capture and desktop tests; environments without a display may skip GUI tests. Version-named regression files intentionally preserve historical edge cases.

## Build a distributable

1. On Windows x64, double-click `Build Portable.bat`. Internet access is required for build dependencies.
2. For a custom OCR installation, pass the Tesseract directory as its first argument. Alternatively run `python build_portable.py --tesseract "C:\\Program Files\\Tesseract-OCR"` after installing `requirements-build.txt`.
3. The script builds and smoke-tests the frozen app and updater, copies dependency notices, and validates the resulting versioned ZIP in `Share with friends/`.
4. Test the full ZIP on another Windows x64 computer before sharing. Do not share only the executable.

Version and archive names come from `version.py`. Never commit build outputs, ZIPs, private session data or local virtual environments. See [release process](RELEASING.md) and [third-party notices](../THIRD%20PARTY.txt). Builds are unsigned; automated tests do not replace live testing.
