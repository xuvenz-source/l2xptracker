L2 LEGACY FARMING TRACKER — VERSION 0.15

This is an external Python desktop application for Windows, not a compiled EXE.
It reads visible desktop pixels only, using MSS and local Tesseract OCR. It does not
open game process memory, inject code, intercept packets, modify the client or send
inputs. Server permission is not established; ask Reborn staff before live use.

SETUP
1. Install Python 3.11 or 3.12 for Windows from https://www.python.org/downloads/windows/
   (include the Python launcher and Tcl/Tk, which are standard installer options).
2. Install Tesseract OCR for Windows, English language data. The project lists
   Windows builds at https://tesseract-ocr.github.io/tessdoc/Installation.html
   Use the standard C:\Program Files\Tesseract-OCR installation or put tesseract.exe
   on PATH. Do not run the tracker as administrator.
3. Extract the ZIP. Double-click Start Tracker.bat. First run installs the Python
   dependencies into a local virtual environment (requires internet access).
   Subsequent tracking runs locally without an internet connection.

CALIBRATION
- Use windowed/borderless Lineage II. Keep chat scrolled to bottom and visible.
- Click Bind game / chat area, then OK. Within five seconds, focus Lineage II.
- The selector shows a snapshot of the focused window's client area. Drag around
  the message text only, excluding scrollbar/arrows, and confirm the window title.
- Include complete rows and align the top to the first complete text row.
  Default pitch is 18 pixels; adjust if UI scaling differs.
- Press Start and return to Lineage II. Existing text is a baseline, not new loot.
- Alt-tabbing or minimising pauses capture and the active farming timer. Returning
  to the game automatically resumes, using a fresh baseline to avoid duplicates.
  Messages received while paused are not recovered. Previously queued OCR can
  still finish while paused, so totals may change briefly after switching away.
- Moving the window is supported at the same client size. Resizing the window,
  changing UI scale/chat layout, or reopening the client may require stopping and
  binding again. Keep the chat unobstructed by overlays; this uses desktop pixels.
- Press Stop and let buffered OCR finish, then Export CSV. The raw CSV includes
  ignored lines and warnings; the event CSV has parsed data for analysis.

TRACKS
Personal XP, SP, Adena and item drops, party loot by character name, session duration,
XP/hour and Adena/hour. Combat messages are ignored. No kill-count estimate from XP.

LIMITATIONS
This is a first prototype, not a validated live tracker. Parser and synthetic scroll
checks were performed, and one screenshot OCR test was done. Actual Windows capture,
full GUI operation, combat-speed accuracy and quantity formats are not verified.
Screen capture targets 20 frames/s; OCR runs independently with a bounded queue.
The scroll detector uses matching physical rows to count new lines, including
identical consecutive messages when movement is visible. If the entire window
changes or a shift cannot be distinguished, lines can be lost or miscounted.
When no reliable overlap is detected, it logs a warning and resynchronises rather
than counting ambiguous text. Some errors can occur without warnings. Changing
background, clipping, wrapped text, unusual fonts, names or new message formats can
also reduce accuracy. Multiple-item patterns are provisional (e.g. Stem (3), 3 Stem,
Stem x3). An unrecognised quantity can be counted as one item or parsed incorrectly;
review the raw export. No persistent session history until CSV export.

FIRST TEST
With staff permission, track for 5–10 minutes and compare totals to the character's
actual XP, SP, Adena and inventory differences. Avoid spending Adena or transferring
items during this test. Party members' own Adena and XP cannot be determined from
personal messages. Review gap warnings and raw text. Do not rely on it for a long
farming session until calibrated.

VERSION 0.2 OCR CHANGES
Yellow loot rows use a separate colour mask. Adena amounts are cropped and read
using digits-only OCR with two thresholds when word boundaries are clear. Conflicting
readings are flagged REVIEW and excluded from totals; the raw CSV records them.
Some errors can still agree across both OCR passes; live validation remains required.
Extra OCR passes may increase processing backlog. The reported 75 and 57 examples
were provided as text only, so their actual pixels have not been tested.

VERSION 0.3 XP OCR CHANGES
Corrects the observed word-level error haye -> have in XP messages. When a
non-yellow XP line fails parsing, retry from its original pixels at two softer
brightness thresholds (90 and 110), requiring both parsed XP/SP values to agree.
Never convert © to 9 or guess another numeric value. Disagreement remains REVIEW.
Tested on the supplied three-line crop, including two identical 221 XP lines:
703 XP and 30 SP in total. Initial valid OCR is still accepted without retries;
valid-looking wrong numbers remain possible. Live Windows capture not tested.

VERSION 0.4 WINDOW FOCUS
Uses Windows foreground-window, window identity and client geometry APIs only.
Checks identity, focus and geometry both before and after each screen capture.
Capture pauses when the selected window is not foreground, unavailable, resized,
or outside the visible desktop. Chat coordinates are client-relative. Rates use
active capture time rather than total wall time. No game process memory is read.
Eight simulated window-state checks and Python syntax checks passed. Actual Windows
API behavior, live capture, and OCR integration have not been tested in this build.

VERSION 0.5 ADENA OCR
If one numeric OCR reading is blank, retry using up to two additional colour
thresholds. Two numeric readings must agree and no valid numeric reading may
conflict with them or with a valid full-line Adena result. A single surviving
reading is still flagged REVIEW. Blank readings are explicitly labelled in the
log. Extra passes occur only when needed, and may increase OCR processing time.
The 85 Adena error was supplied as text, not pixels; retry logic was tested
with simulated readings. Live Windows gameplay remains untested.

VERSION 0.6 — GAME HUD AND SAVED CALIBRATION
- Select the game/chat once in v0.6. The chat rectangle, line height, game title,
  window class and original client dimensions are saved in
  %LOCALAPPDATA%\L2LegacyTracker\settings.json, outside the version directory.
  Keep this file when upgrading. v0.5 did not save settings, so one initial
  selection is required. Start with the matching game open at the same size.
  A restarted client can be matched automatically by its title/class/dimensions;
  if multiple matching clients exist or the title/size changes, rebind manually.
  Changing chat layout/UI scale may require manual recalibration even at same size.
- Game HUD checkbox (enabled by default) controls a 310x62 native Windows
  click-through, non-activating desktop popup showing personal Adena/hr and EXP/hr.
  It displays only during tracking when the bound game is foreground, checked
  approximately every 100 ms; a very brief delay on alt-tab is possible. It uses
  active capture time, follows game movement, and selects a corner that avoids
  the saved chat rectangle, or hides if there is no safe corner. Use windowed or
  borderless mode; exclusive fullscreen may not display external overlays.
- No added dependencies. All v0.5 recognition and capture code retained.
- Seven automated tests cover calibration storage/validation, matching, HUD
  positioning/rates, simulated visibility and capture geometry. Windows native
  overlay drawing, focus/click-through and live gameplay remain untested.

VERSION 0.7 — XP RETRY VERIFICATION
- Compare the XP/SP numeric pair from the initial read and up to three softer
  per-row reads. Allow SF for SP and damaged leading words only in the retry
  verifier. The ordinary parser is unchanged. Two agreeing pairs are required;
  a readable conflicting pair rejects the event. Blank or incomplete readings
  do not vote. This is not independent proof of OCR accuracy.
- The reported 261 XP / 12 SP case passes using the supplied OCR strings; its
  original pixels were not supplied. Nine new mocked OCR/verification tests and
  seven existing HUD/settings tests passed. Windows live testing remains open.
- Existing v0.6 saved settings and HUD retained; no dependencies added.

VERSION 0.8 — SHIFT-DRAG HUD
- While the tracker is running and the bound game is active, hold either Shift
  key, then left-click and drag the HUD. Release the mouse button or Shift to
  finish. Without Shift, the HUD remains click-through and never intentionally
  activates itself. The HUD checks focus and Shift state about every 25 ms.
- Position is saved in the existing settings.json as client-relative coordinates
  (hud_position). v0.6/v0.7 chat calibration remains compatible; no re-selection
  is required unless the original calibration is otherwise invalid.
- HUD movement is clamped to the visible client and rejects positions overlapping
  the selected OCR rectangle. If a saved position is unusable, an automatic
  safe corner is selected. Alt-tab hides the HUD and ends any drag.
- No new dependencies, hooks, injected code, or synthetic game input. Eight new
  simulated tests plus sixteen existing tests passed in the Linux development
  environment; MSS was stubbed for the pure logic suite because it was not
  installed there. Python syntax checks passed. Native Windows drag interaction,
  rendering, focus preservation and live capture still require user testing.

VERSION 0.9 XP RETRY PARSER
Recognises merged XP/and/SP labels and limited trailing OCR noise after
sentence punctuation (one isolated digit or x). Requires two agreeing
XP/SP pairs as before; conflicting observed pairs remain REVIEW. Does not
guess unreadable digits. Tested with the reported 221 XP and 9 SP strings
and regression cases; original pixels and native Windows gameplay untested.
Settings schema, HUD, and capture logic are unchanged.

VERSION 0.10 — REPEATED MESSAGE OCR
- Increases spacing between rows in the shared OCR sheet. Adjacent visually
  similar rows bypass the sheet and are recognised individually; repeated XP
  rows receive independent numeric verification. A blank or malformed XP batch
  read also triggers isolated recognition. Each captured row remains a separate
  event; numeric values are never copied from adjacent rows. Yellow messages
  retain their existing isolated OCR and numeric validation.
- Scroll detection and saved settings are unchanged. Completely indistinguishable
  screen frames cannot reveal whether a new identical message arrived.
- Repeated-row isolation adds OCR work when messages look alike. Live Windows
  performance remains untested. No new dependencies.

VERSION 0.11 — HUD DRAG FALLBACK
- Hold Shift, then click and hold over the HUD and drag. Native mouse-message
  handling is retained; the HUD also polls the physical mouse-button transition
  and cursor position while the bound game is foreground. This allows dragging
  when a layered popup does not receive the click. No hooks or simulated inputs.
- On return from alt-tab, an already-held mouse button cannot start a polled drag;
  release and press again. Normal clicks and clicks starting outside the HUD do
  not start a drag. Releasing either control saves the accepted position.
- If Windows passes a Shift-click through the HUD to Lineage II, the game may
  receive that click as well. Use a safe area of the game when moving the HUD.
- Existing OCR logic, calibration and HUD position storage are unchanged. Native
  Windows mouse routing is not testable in the development environment.

VERSION 0.12 — SP-ONLY OCR CONFLICTS
If valid readings agree on XP but disagree on SP, perform two additional
isolated OCR passes using different thresholds/resampling. If all valid reads
agree on XP and SP has at least three agreeing votes against one dissent,
count both and explicitly label the SP majority in the log and raw CSV.
Otherwise count the agreed XP alone, leave SP blank in the event CSV, and
flag the unknown SP for review. If XP itself conflicts, neither is counted.
This is a heuristic: correlated OCR errors can still produce a wrong majority.
No changes to Adena recognition, capture, HUD or saved settings. Tests use
mocked OCR strings and capture; the reported error's original pixels and live
Windows operation have not been verified. Six new tests plus 47 previous
regression tests passed with MSS stubbed in the development environment.

VERSION 0.13 — MANUAL REVIEW QUEUE
Click Review (N) in the main tracker while paused or after stopping. Select a
pending message to see all OCR evidence and the suggested complete messages in
an editable drop-down. A sole candidate is prefilled; conflicting candidates
require you to choose or type a corrected message. Click Approve & count to
update current session totals and rates, or Dismiss (ignore) to leave the
uncertain message uncounted. For partial XP messages, the XP is already recorded;
enter the original XP and corrected SP to add only SP. Each row has a separate
review ID; approving it removes it from the queue so it cannot be counted twice.
The existing warning count is historical; Pending review shows unresolved rows.
Review decisions appear in the raw CSV; approved events appear in the normal CSV.
Reviews can be resolved after Stop, but starting a new session or closing the
application discards unresolved reviews (with a warning). There is no image
history or persistent session/review storage. Existing calibration and HUD
settings remain unchanged. OCR and Windows capture code are unchanged.

VERSION 0.14 — MANUAL PAUSE AND HUD POSITIONING
- Pause / Resume preserves the current session, reviews, totals and active timer.
  Pausing stops new screen captures; queued OCR from before pause may finish.
  Resume still requires Lineage II focus. A fresh chat baseline prevents paused
  or previously counted messages from being counted again. Messages received
  while paused are not recovered. Stop still ends the session.
- Position HUD opens a schematic of the saved game dimensions and protected chat
  area. Drag the HUD in that preview and Save position. It works without a live
  session or Shift-click; the saved position is applied when the game HUD appears.
- Move HUD in game arms a click-free placement mode while a session is running.
  Return to the game, move the mouse to position the HUD, then tap Shift to save.
  Alt-tab after placement begins cancels it. No mouse click is needed; the HUD
  remains click-through in this mode. Existing Shift-drag remains available.
  If the in-game mode does not work, use the tracker preview instead.
- Both positioning methods use the existing settings file. No recalibration,
  OCR changes, game injection, or new dependencies. Native Windows game behaviour
  remains untested; automated tests use mocked capture and Windows APIs.

VERSION 0.15 — SP-ONLY MAJORITY WITH UNREADABLE PASS
If all valid XP/SP pairs agree on XP, accept an SP majority of two
matching readings against one dissent after at least four attempts,
including an unreadable pass. Existing 3:1 or stronger one-dissent
majorities remain supported. Ties, multiple dissenting readings, and
conflicting XP values retain the previous review behaviour. The log
marks SP majority decisions and retains all OCR evidence. This is a
heuristic and can accept incorrect SP when OCR errors are correlated.
No change to XP or Adena verification, capture, HUD, manual pause,
review queue or saved settings. Tests use mocked OCR outputs; original
pixels and native Windows gameplay remain unverified.

v0.16 — Persistent session history
---------------------------------
- New Session history button. Each new farming session is saved immediately,
  checkpointed every 15 seconds while tracking, and finalised after Stop and
  the queued OCR has finished. Normal closing waits for buffered OCR.
- Names default to the session start date/time. Select one and choose Rename.
- Ctrl/Shift-select at least two entries and click Merge selected; enter a name.
  A merged entry references distinct original sessions, so sources remain
  intact and overlapping merges do not double-count the same saved session.
  Combined rates use total recorded loot/XP divided by summed active seconds.
  Merges update when a source session is corrected; Refresh reloads the report.
- Select one entry to see totals, per-hour rates, active time, party loot,
  warnings and pending reviews. Export selected CSV writes the event list and
  a separate summary CSV. Select an original and Open original for review to
  resolve old OCR reviews; stop any active capture before opening it.
- Archive path: %LOCALAPPDATA%\L2LegacyTracker\sessions.sqlite3. Chat/HUD
  settings stay in settings.json. Close the app before backing up the database.
- A checkpoint may be incomplete after a crash or forced termination; buffered
  OCR and changes after the most recent successful checkpoint may be lost.
  Sessions from v0.15 or earlier were not automatically saved; CSV import is
  not included. No new dependencies. Windows live capture remains untested.


v0.17 — Independent SP verification
- If XP is unreadable or contradictory, two or more agreeing SP readings with no valid SP dissent can be counted independently. No XP is guessed.
- Review the pending XP with the known SP; approving adds only XP. Session history, merges and exports retain the partial event. Blank XP in an export means unknown, not zero.
- Older saved sessions load without migration. Use v0.17 or newer to open sessions containing the new SP-only events.
- Windows portable build kit included. Rebuild the executable using Build Portable.bat.

VERSION 0.32 — LOCKABLE HUD
The in-game HUD starts locked. Double-click the top-right padlock to unlock; left-click and drag the body, then release to save. Single-click the unlocked padlock to lock. Locked body clicks pass through; Pause/Resume works in both states. This supersedes the Shift-drag instructions above. Explicit Settings positioning is still available.

VERSION 0.33 — HUD OPACITY
Settings → Tracking → HUD opacity adjusts the entire floating HUD (20–100%). The setting applies immediately, saves locally and defaults to 92%. Reset restores the default. Return to the game to view changes. Lock, drag, and pause behaviour is unchanged.

VERSION 0.34 — CONSUMABLE COSTS
Dashboard: double-click a consumable and enter Adena per observed activation; blank removes a price, zero means free. Cost and cost/hour, Adena after known costs and unpriced activations are shown. Set default cost saves future prices; historical sessions retain their own prices and can be edited individually. Exports include a consumable costs CSV.
