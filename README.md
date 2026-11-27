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

## Updates (v0.20)

Portable builds check GitHub's latest published stable release on launch. **Check for updates** also checks manually. In v0.20–v0.23 downloads require approval; v0.24 adds automatic installation as described below. Updates are disabled while tracking or draining OCR. The updater downloads the exact versioned ZIP and SHA-256 sidecar, verifies its digest, extracts it beside the installation and runs its self-test. It then closes the tracker, replaces the dedicated application directory and restarts. The old folder is retained; immediate installation/startup failure attempts rollback. LocalAppData settings and session history are untouched. If the folder contains extra files, extract a new release to a dedicated folder instead. HTTPS and release checksums are not a publisher signature; trust the repository and do not disable security software.

## Numeric reviews (v0.21)

Select XP / SP or Adena and enter the numbers only. Unambiguous OCR suggestions prefill the fields; conflicting values remain blank. Previously counted partial XP/SP is locked and will not be added twice. The Adena recipient is shown for personal and party drops. Item / other retains full-message correction. Approvals continue to update session totals, kills and merged reports.

## Appearance (v0.22)

The desktop dashboard now defaults to a charcoal dark theme with gold Adena, green EXP and blue kills/hour cards, styled tables, numeric reviews and a colour-coded activity log. Enable **Light mode** in Settings. Appearance is saved separately from calibration and sessions. Windows-native dialogs may still follow the system theme. No OCR, HUD or session calculation changes.

## Tracking preferences and HUD pause (v0.23)

Use the floating HUD Pause/Resume button or the desktop controls to toggle the same manual pause. Settings now contains Light mode and Pause when Lineage 2 loses focus (off by default). Background tracking continues only while the calibrated chat pixels remain visible and unobstructed; covered, minimised or resized clients suspend capture and exclude that time from rates. This is not hidden-window capture. The HUD still hides outside the game. Focus and appearance preferences persist independently of calibration. Native game click routing and background capture require live Windows testing.

## Automatic installation (v0.24)

Launch only `L2 Legacy Tracker.exe`. The integrated updater checks for newer published stable releases on startup and every 30 minutes while open. Automatic installation is enabled by default, can be disabled in Settings, and waits for tracking, pending OCR and open tracker dialogs to finish. With automatic installation off, the update button offers manual approval. Each install verifies the ZIP checksum and self-test, saves the session, starts the bundled internal helper, then restarts. A failed attempt is not repeated continuously; the update button permits manual retry. A previous installation is retained. The helper remains bundled beside the main executable for compatibility with earlier updater versions; users never need to open it. The complete extracted folder is required. Draft releases remain invisible until the maintainer publishes them.

## Grouped session history (v0.25)

Merged reports now appear as collapsed parent sessions. Expand them to see originals and any previously selected merged reports. Grouped sessions no longer occupy separate top-level rows. Existing merged reports automatically display their original sources without database migration. A source included in multiple reports is visible under each; its actual record is shared, not copied. Totals, exports and review corrections continue to use unique original sessions. Renaming an original updates its name in all groups.

## Party presets (v0.26)

In **Party setup**, enter your usual teammates and choose **Save as new** to name a preset. Select a saved preset to populate the roster, then choose **Use party** for your next session. Presets can be updated, renamed or deleted; Solo / clear empties the roster. Presets are stored locally in tracker_preferences.json and survive upgrades. Saved sessions retain their original rosters; no preset is automatically applied after restarting the tracker.

## Tabbed interface and incremental updates (v0.27)

The desktop now has Dashboard, Activity, Reviews, History, Party and Settings tabs. Capture controls and the status bar remain available across tabs; game binding and HUD positioning are under Settings. Existing history and presets are retained. The updater prefers a smaller, checksum-verified file-level patch for an exact installed version when available. Unchanged files are copied locally and verified against the target manifest; changed files are downloaded, removed files are omitted, and the complete staged installation is self-tested before the existing backup/restart process. A missing, incompatible or failed patch falls back to the full ZIP. v0.26 and older need one full update to acquire this capability. Release packaging compares against the latest published version, so skipping versions may still require a full download.

## Capture and pause reliability hotfix (v0.28)

Restores the original focused-game screen capture path, avoiding false-positive background occlusion checks while the game is focused. When unfocused, overlapping windows still suspend OCR. Keep chat unobstructed even in the focused game. HUD pause and position commands are dispatched through the main UI queue, not directly from native window callbacks. Settings includes an Open diagnostic folder action; bounded local diagnostics and native fault dumps help identify remaining errors. No screenshots or chat messages are deliberately written to diagnostic logs. Live game verification remains necessary.

## Drag-and-drop session grouping (v0.29)

In History, drag an original session onto another session to create a named parent, or drop a session or group onto an existing parent to add it immediately. Drag multiple selected rows together, using Ctrl/Shift first. Valid targets are highlighted. Existing memberships are preserved; dragging a shared session adds a reference, not a copy or destructive move. Duplicate sources and circular groups are rejected, and nested parent totals are refreshed atomically. Merge selected remains available.

## Lockable HUD (v0.32)
The in-game HUD starts locked. Double-click its top-right padlock to unlock, then left-click and drag its body. Single-click the open padlock to lock it again. Pause/Resume remains interactive in both states. The locked body is click-through; the lock and Pause/Resume remain interactive. Positions are saved on release, constrained to the game client and kept away from captured chat. The explicit Settings positioning tools remain available as a fallback.

## HUD opacity (v0.33)
Settings → Tracking → HUD opacity adjusts the entire floating HUD from 20% to 100%, including text and buttons. The default is 92%, matching the previous appearance; Reset restores it. Changes apply immediately to the HUD and save locally, independently of chat calibration. The HUD is visible when the game is foreground, so return to the game to inspect changes. Lock, drag, pause and focus rules are unchanged.

## Consumable costs (v0.34)
Double-click a consumable in the Dashboard or select Edit selected cost to assign Adena per observed activation. Enter the combined cost if a weapon uses several units per activation; no automatic inventory quantity is assumed. Blank means unpriced, zero means free. Prices apply retroactively to the selected session. During active tracking, edits also save as a future default; historical edits change only that session. Set default cost lets you preconfigure prices by exact item name for future sessions. History keeps each original session's prices, even when merged. Reports show known cost, cost/hour, Adena after known costs (not total profit), and unpriced uses. Exports include a separate consumables CSV. Old sessions remain unpriced until edited.

## Optional net Adena HUD (v0.35)
Settings → Tracking → Subtract consumable costs from HUD Adena/hr (net) replaces the existing HUD Adena rate with (personal Adena earned minus known consumable expenses) divided by active hours. Default is off (gross earnings). The preference saves locally and applies immediately; negative net rates remain visible. NET ADENA/H* indicates unpriced uses, so the figure is only net of known expenses. The dashboard and history retain gross earnings and expense reports; no additional HUD column is added.

## HUD drag hotfix (v0.35.1)
Unlocked HUD movement now handles native mouse-down, mouse-move and mouse-up directly, with mouse capture on the HUD itself when Windows permits. Polling remains a fallback. A missing asynchronous mouse-button state no longer immediately cancels a native drag. Positions still avoid the selected chat region. Local diagnostics record drag start/end and rejected positions; live game interaction requires verification.

## Reset session (v0.36)
Reset in the main control bar or HUD stops the active capture, drains buffered OCR, saves the original session with its pending reviews and costs, then creates a fresh session. It preserves active party, prices, capture configuration and manual pause state. Existing on-screen chat is used as a baseline, not replayed. Reset is disabled while draining; if saving fails, no new session is started. Messages appearing between capture stop and the new baseline may not be recorded. Reset is non-destructive and does not require confirmation.

## Organised session history (v0.37)
Create top-level character sections and nested folders. Drag sessions or reports into folders or use Move to; moving does not merge or modify statistics. New logs here chooses the destination for future sessions (including Reset). Drag onto another session or report still merges as before. Delete requires confirmation: originals are removed from every report, empty reports are removed, deleting a report retains its sources, and deleting a folder promotes its remaining contents. Active/draining sessions cannot be deleted. Existing archives migrate in place; original session data and merged-report links are preserved.

## Visual updater (v0.38)
The portable tracker opens a dedicated update manager before the main dashboard. It checks the latest published release and respects automatic installation preferences. Downloads show measured bytes and percentage when the package size is known; preparation, verification and testing use an indeterminate progress bar. A failed incremental patch switches to the full package. Offline or failed checks can open the current tracker without an update. The separate installation helper shows an installing window during file replacement and restart. An update-triggered restart skips the redundant startup check. Periodic and manual updates also show the visual download window when idle. Upgrading from older versions uses their existing updater once; the new visual manager is available on subsequent launches.

## Manual loot sell values (v0.39)
Double-click an actual item row in Dashboard → Session loot or select Edit item value. Enter expected Adena per individual item (e.g. NPC vendor sell price). Quantity times unit value is shown separately from actual Adena. Personal estimated loot value and its hourly rate exclude other players' drops; unpriced quantities are identified. Live edits become future defaults; stopped/historical edits only change that session. Set default value configures future sessions. Reset preserves active prices and merged reports use each original's own values. Export includes a loot-values CSV. Gross and net cash metrics and HUD remain unchanged; estimated sale value is not confirmed sale proceeds.

## Modular HUD and player progress (v0.40)
Settings now contains Tracking, HUD and Player status tabs. HUD widgets, order (drag handles or arrows), font size, one/two rows, visibility and controls are saved; the lock remains available. Select level digits and XP percentage separately while stopped, or enter manual progress. C1 XP requirements are bundled, with configurable cap. Automatic reading uses passive screenshots and repeated OCR agreement; stale readings are marked. ETA uses active XP/hour after 30 seconds. Manual mode estimates progress from recorded XP and must be recalibrated after death or character changes. Status-region and chat protection adapt to HUD dimensions. Live Windows/game OCR and dragging still require verification.

## Responsive interface (v0.41)
History has a compact top toolbar, resizable session/detail panes, separate scrollable Summary and Loot & expenses tabs, and horizontal table scrolling. Dashboard, settings, review and party pages scroll independently; the main status/update bar stays pinned. Smaller window sizes no longer require enlarging the app just to reach lower controls. Existing session data is unchanged.

## Automatic backup retention (v0.42)
Settings → Tracking → Updates → Keep installation backups defaults to two previous installations; choose one or keep all. Cleanup runs on normal startup (including accumulated older backups) and after successful installation/restart verification. It only removes older recognised sibling backup folders matching the updater naming convention, installation marker and expected structure; symlinks/junctions and changed or unrecognised backups are skipped. The just-created rollback copy is protected. Cleanup errors never invalidate an update. Session database/preferences live separately and are not pruned. On the first upgrade from an older helper, cleanup occurs at the next ordinary launch.

## Automatic chat row alignment (v0.43)
The selected font size is a nominal pitch. At capture startup, several high-contrast colour-matched chat lines can establish a more accurate physical pitch and vertical alignment (including Large rendered at 18 px rather than 19). Mask overlap and OCR crops share the same aligned rows. Weak evidence retains the configured pitch; changed geometry causes a conservative rebaseline, not replay of prior chat. HUD status distinguishes waiting, ready, synchronising and active capture. Existing chat at session start is intentionally not counted.

## XP recognition hotfix (v0.43.4)
The reported screenshot produced 867, 66/ and S67 as OCR interpretations of the XP amount, while SP was consistently 43. Magenta XP messages now retry with two independent colour-contrast masks when numeric agreement is missing. Invalid digit tokens are not treated as valid numeric suffixes. XP and SP are verified independently, preserving an agreed XP amount even when SP is uncertain; conflicting valid values still require review.

## Sparse chat alignment (v0.43.5)
The latest user screenshot shows 21-pixel chat spacing with only three bright reward messages. The detector now falls back to tightly palette-matched ordinary chat lines and tests nearby pitches through ±4 pixels. It reprojects the previous committed screenshot when alignment changes, rather than throwing away intervening messages. Identical frames are still not counted twice.

## Quest item rewards (v0.43.6)
Earned item messages such as `You have earned Turek Dog Tag.` are counted as item loot, even when they share the yellow Adena colour. Existing item quantities, manual sale values, history and export support apply. Damaged currency messages remain reviewable. Old Adena-colour reviews containing recognisable earned item evidence can be approved as items; no saved review is silently counted.

## Current status: v0.43.6

The pause/resume regression fixture uses correctly shaped pixel arrays; mixed-pitch OCR batches are processed separately so a calibration change cannot invalidate queued rows.

OCR is imperfect. Rapid or ambiguous scrolling, clipped lines and misread numbers may cause missed or incorrect events. Paused periods are not captured. Actual Windows gameplay and distribution on a clean PC still need testing. The tracker does not establish that server rules permit its use.

## Developers

Use Python 3.12 x64 and Tesseract with English data on Windows. Run `Start Tracker.bat` or install `requirements.txt` and run `python tracker.py`. Run regression tests with `python -m unittest discover -v`. `Build Portable.bat` creates a self-tested portable ZIP locally. See the existing README.txt for calibration and the version-by-version history, and BUILD INSTRUCTIONS.txt for packaging details.

GitHub Actions runs tests on main and pull requests. Successful main pushes also generate a Windows portable build artifact and a draft release if the version does not already exist. Only published releases are visible to the updater. A maintainer can manually rerun **Windows tests and portable build**. See [RELEASING.md](RELEASING.md) before sharing it publicly.

## Privacy and licensing

Tracking is local; do not upload personal session databases, logs, chat screenshots or settings to this repository. When reporting a bug, remove personal or party names if needed. The project license has not yet been selected by the owner; public visibility alone does not grant an open-source license. See THIRD PARTY.txt for dependency notices and distribution considerations.
