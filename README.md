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

## Party tracking (v0.18)

Before Start, open **Party setup** and enter the other character names (comma-separated). The roster is fixed for that session; stop and start a new session if it changes. The loot list records visible personal and named party acquisitions as before, including named Adena messages if visible. If only your own Adena share is visible, each configured member receives a separate equal-share estimate, and the session summary estimates total party Adena and Adena/hour. Estimates assume every member receives the same amount as you, are not additional recorded loot, and can be wrong for rounding, range or distribution changes. Your HUD continues to show personal rates. Session history and merged reports calculate estimates per original roster; old sessions without a roster are not estimated. CSV exports contain observed events only.

## Kills/hour (v0.19)

Each recorded personal XP acquisition event counts as one estimated kill, including partial XP/SP events. Manual approvals of new XP events add a kill; correcting existing partial events does not. The HUD, live totals and session history show kills/hour based on active capture time. Existing saved sessions and merged reports derive kill counts from recorded events; history summary CSV includes kills and kills/hour. XP from quests or other non-kill sources also counts if it uses the same message format, and missed OCR messages can undercount kills. Party kills are counted once per personal XP message, not multiplied by party size.

## Current status: v0.19

OCR is imperfect. Rapid or ambiguous scrolling, clipped lines and misread numbers may cause missed or incorrect events. Paused periods are not captured. Actual Windows gameplay and distribution on a clean PC still need testing. The tracker does not establish that server rules permit its use.

## Developers

Use Python 3.12 x64 and Tesseract with English data on Windows. Run `Start Tracker.bat` or install `requirements.txt` and run `python tracker.py`. Run regression tests with `python -m unittest discover -v`. `Build Portable.bat` creates a self-tested portable ZIP locally. See the existing README.txt for calibration and the version-by-version history, and BUILD INSTRUCTIONS.txt for packaging details.

GitHub Actions runs tests on main and pull requests. Successful main pushes also generate a Windows portable build artifact. A maintainer can manually rerun **Windows tests and portable build**. See [RELEASING.md](RELEASING.md) before sharing it publicly.

## Privacy and licensing

Tracking is local; do not upload personal session databases, logs, chat screenshots or settings to this repository. When reporting a bug, remove personal or party names if needed. The project license has not yet been selected by the owner; public visibility alone does not grant an open-source license. See THIRD PARTY.txt for dependency notices and distribution considerations.
