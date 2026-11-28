# L2 Legacy Farming Tracker

Independent Windows farming analytics for Lineage II C1. Reads visible system-chat pixels using local OCR. No game injection, memory reading, network interception, client modification or automated game input.

[Download the latest published release](https://github.com/xuvenz-source/l2xptracker/releases/latest) · [User guide](docs/USER-GUIDE.md) · [Build instructions](docs/BUILDING.md)

## Getting started

1. Download the Windows x64 **Portable.zip** from Releases (not Source code or a Delta.zip).
2. Extract the entire archive to a dedicated writable folder. Keep the executable, `_internal` and `ocr` directories together.
3. Run `L2 Legacy Tracker.exe`, open the game in windowed/borderless mode, and bind the visible system-message area.
4. Start a session. Configure the floating HUD and, if desired, select a default farming monster.

Python and Tesseract are bundled in the portable release. The application is unsigned. Obtain server staff approval before using it in game.

## Features

- Live XP, SP, Adena, kills/hour and player-level forecasts; net Adena after known consumable costs.
- Three independently positionable floating HUDs: main controls, XP/SP and Adena/Loot.
- Monster library, default kill assignment, drop estimates and bulk identification reviews.
- Observed loot, item valuations, consumable expenses, party rosters and saved presets.
- Local session history, folders, drag-and-drop merging, CSV exports and OCR corrections.
- Dark/light appearance, automatic verified updates and incremental downloads for compatible installations.
- Prestige workspace in v0.55.2 source: Overview, Progression, Loot & Adena, Monster Library, Party, History, Reviews, Activity Log and Settings.

The latest downloadable version is shown on Releases; source changes are not necessarily published yet.

## Documentation

| Document | Contents |
| --- | --- |
| [User guide](docs/USER-GUIDE.md) | Current setup, farming, HUD and review instructions |
| [Chat calibration](docs/CALIBRATION.md) | Text sizes, colours and capture troubleshooting |
| [Build instructions](docs/BUILDING.md) | Run from source, tests and Windows portable packaging |
| [Release process](docs/RELEASING.md) | Automated validation, release and updater compatibility |
| [Historical changelog](docs/archive/CHANGELOG-through-v0.53.md) | Archived version-by-version development notes |
| [Third-party notices](THIRD%20PARTY.txt) | Bundled dependencies and redistribution considerations |

## Development

Use Python 3.12 x64 and English Tesseract on Windows. Install `requirements.txt` and run `python tracker.py`, or use `Start Tracker.bat`.

Run the regression suite from the repository root:

```sh
python -m unittest discover -s tests -v
```

The application modules remain at the repository root. Regression tests are in `tests/`, documentation in `docs/`, and CI in `.github/workflows/`. Generated archives, build output and personal data are not tracked.

## Privacy and limitations

Session data and preferences are stored locally under `%LOCALAPPDATA%\L2LegacyTracker`. Do not upload personal databases, screenshots or logs without removing sensitive information. OCR can miss or misread messages; estimated kills use personal XP/SP events as a proxy and default monster assignments are assumptions. Party estimates and drop forecasts are not guaranteed rewards.

The tracker is experimental. Automated tests and packaging checks do not establish live gameplay reliability, clean-PC compatibility or server permission. Not affiliated with NCSoft or L2 Reborn. A project license has not been selected; public visibility alone does not grant an open-source license.
