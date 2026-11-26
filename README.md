# L2 Legacy Farming Tracker

Independent, experimental Windows farming tracker for Lineage II C1. Reads visible system-chat pixels with local OCR. No injection, game memory reading, network interception, client modification or automated game inputs. Not affiliated with NCSoft or L2 Reborn; obtain server staff approval before use.

## Download and run

Once a verified release is published, download its Windows x64 portable ZIP from [Releases](https://github.com/xuvenz-source/l2xptracker/releases) (not the source-code ZIP). Extract the whole archive and run `L2 Legacy Tracker.exe`. Keep `ocr` and `_internal` beside the executable. Python and Tesseract do not need to be installed separately. The application is unsigned.

## Features

- Personal XP, SP and Adena; personal and visible party item drops.
- Adena/hour and XP/hour HUD; game-focus protection and manual pause/resume.
- Manual OCR review with partial-value recovery and duplicate prevention.
- Saved chat calibration and HUD position, session history, renaming and merging.
- CSV export and local storage under `%LOCALAPPDATA%\L2LegacyTracker`.

## Current status: v0.17

OCR is imperfect. Rapid or ambiguous scrolling, clipped lines and misread numbers may cause missed or incorrect events. Paused periods are not captured. Actual Windows gameplay and distribution on a clean PC still need testing. The tracker does not establish that server rules permit its use.

## Developers

Use Python 3.12 x64 and Tesseract with English data on Windows. Run `Start Tracker.bat` or install `requirements.txt` and run `python tracker.py`. Run regression tests with `python -m unittest discover -v`. `Build Portable.bat` creates a self-tested portable ZIP locally. See the existing README.txt for calibration and the version-by-version history, and BUILD INSTRUCTIONS.txt for packaging details.

GitHub Actions runs tests on main and pull requests. A maintainer can manually run **Windows tests and portable build** to generate a downloadable build artifact. See [RELEASING.md](RELEASING.md) before sharing it publicly.

## Privacy and licensing

Tracking is local; do not upload personal session databases, logs, chat screenshots or settings to this repository. When reporting a bug, remove personal or party names if needed. The project license has not yet been selected by the owner; public visibility alone does not grant an open-source license. See THIRD PARTY.txt for dependency notices and distribution considerations.
