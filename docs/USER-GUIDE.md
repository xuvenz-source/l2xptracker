# User guide

This describes the v0.55.3 Prestige source interface; earlier installed releases may use tabs or slightly different labels. Check the version on the main window and the published release before troubleshooting.

## First session

- Extract the full portable archive and launch the tracker. Keep its installation folder dedicated to the application.
- Use windowed/borderless Lineage II and keep system chat visible, scrolled to the bottom and unobstructed.
- Open Bound areas (or Settings → Tracking → View / edit bound areas). Focus the game when prompted. Select the message text, not scrollbars or controls. See [calibration](CALIBRATION.md).
- Start the session. Existing chat is a baseline, not newly earned loot. Pause/Resume and Stop share the same session controls as the HUD. Stop lets queued OCR finish before saving. Reset saves the prior session and starts a new one; avoid combat during the transition.

The timer normally continues while the game loses focus. Capture only reads safely visible pixels; minimised or covered chat cannot be recovered. Enable pause on focus loss in Settings → Tracking if preferred. Resizing or changing chat layout can require recalibration.

## Workspace

- **Overview:** live rates, level progress, current default monster and a circular progression indicator and selectable rolling charts of session-average XP, gross Adena and kills/hour, sampled during live tracking.
- **Progression:** XP/level forecasts, SP balance and estimates; enter level and XP manually or configure automatic status OCR in Settings → Player status. Stale automatic progress is marked.
- **Loot & Adena:** recorded item quantities, estimated sell values, consumable activations, known costs and desired drops. Double-click a row to edit the current session; defaults apply to future sessions. Unpriced costs are not assumed free. Estimated item sale values are separate from observed Adena.
- **Monster Library:** import and verify monster level, base XP/SP and drop table; select active monsters and optionally a default, then Apply selection. Exact unique reward signatures take priority when enabled under normal solo/full-stamina conditions. Otherwise positive personal rewards may use the default even in a party. Defaults are assumptions, not verified identities. Choose No default to disable. Changes apply to future captured rewards; Reviews can bulk-assign existing unidentified kills with confirmation. Manual corrections are preserved. Drop waits are statistical averages, not countdowns or guarantees.
- **Party:** enter teammates, save/load presets and apply the roster. Roster changes during a live session create new tracking periods; previous rewards remain attributed to their original context. Equal-share Adena estimates are not observed rewards.
- **Session History:** create sections/folders, drag sessions to organise or merge, rename and export. Merged reports count original sessions once. Folder deletion preserves contents; report deletion preserves originals. Open an original for corrections or price edits.
- **Reviews:** approve or dismiss uncertain OCR; previously counted partial XP/SP is locked. Monster identification reviews support bulk assignments and explicit signature learning only for verified normal rewards.
- **Activity Log:** accepted and ignored lines and recognition warnings.

Press Ctrl+K for quick navigation to pages and common settings.

## Floating HUDs

The compact main HUD contains Pause/Resume, Reset, lock and gear. Its cog includes tracker visibility. XP/SP and Adena/Loot panels each have a toolbar and scoped settings. Hiding a panel does not pause tracking.

Double-click a padlock to unlock, drag the body and click the padlock to lock. Move panels away from chat and calibrated status regions. Settings → HUD controls global visibility, opacity, font size, widget order, presets and layout. Each tracker gear offers its own rows and visible widgets. Net Adena/hr subtracts known consumable costs; an asterisk indicates unpriced uses.

## Updates and support

The portable updater checks on startup and every 30 minutes, installs published stable releases while idle by default and restarts the app. Disable automatic installation or adjust backup retention in Settings → Updates. Compatible versions use verified direct deltas; a full ZIP is the fallback. Do not launch the bundled helper manually.

Preferences and history are stored separately from the installation. Settings → Advanced includes diagnostic-folder access and optional OCR evidence collection. Nothing is uploaded automatically. Review exported evidence for private names before sharing.

This tool estimates performance from visible messages; OCR, non-kill XP, shared damage, reward changes and missed messages affect accuracy. Test against in-game totals with staff permission before relying on results.
