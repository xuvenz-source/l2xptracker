# Chat calibration

In Settings → Tracking, select View / edit bound areas. Draw around the visible system-message panel and use Auto-fit chat, or manually select the text area with complete rows and no scrollbar interference. Check the fitted outline before saving. Keep the game windowed/borderless and chat unobstructed. Rebind after changing game font, scaling or layout.

## Text size and colours

| Size | Line spacing |
| --- | --- |
| Small | 16 px |
| Medium | 17 px |
| Large | 19 px |
| Manual | 10–40 px |

Choose the actual in-game text size or manually set the observed spacing. Use the built-in L2 defaults, distinct colours, or custom hex colours matching your client. Distinct colours aid recognition.

| Message | L2 defaults | Distinct colours |
| --- | --- | --- |
| XP / SP | #B09B79 | #FF00FF |
| Adena | #FFFF00 | #FFFF00 |
| Items | #FFFF00 | #00FF00 |
| Consumables | #B09B79 | #00AAFF |
| Other | #B09B79 | #B09B79 |

Apply chat settings before tracking. Shared colours are distinguished by text; uncertain rows may require review. Experimental native chat recognition (Large / Medium / Small) is off by default. It falls back to OCR when templates are uncertain.

## Troubleshooting

If the game is covered, minimised or resized, visible-pixel capture cannot read it safely. Check bound areas, text spacing and colours, then compare short-session totals against the game. Reviews correct uncertainty; no method can reconstruct messages that scrolled past unseen. Settings → Advanced provides optional OCR evidence and local diagnostics. Remove sensitive player names before sharing.

Large-text slash recovery: for exact magenta personal XP/SP and yellow personal Adena, a failed OCR amount containing a slash can be checked against verified full-line glyphs at two thresholds and isolated digits-only OCR. The XP/SP fallback never overrides a conflicting valid number. A standalone slash in the Adena amount is also eligible for verification. This is not global slash replacement and does not expand support to Medium glyphs. Unverified fields remain in review.

## Character level and experience percentage

The fixed-size character status font is independent of chat text size. Prefer Auto-fit player for the entire compact frame. For manual binding, select only the level badge and XP percentage (including decimal and percent sign), excluding the name, HP and MP. Saving bound areas now checks the selected fields against the captured image and reports their readings in Settings → Player status. Live automatic readings still require confirmation and reject conflicting valid numbers. Low-confidence fields are not guessed. The status reader uses alternate thresholds, contrast and scaling if the normal two passes cannot agree.

### Native status digit recogniser (initial coverage)

Character level and XP percentage now attempt exact native pixel matches at two brightness thresholds before OCR. The separate level badge library initially contains 0 and 2. The white status font contains 0, 1, 4, 5, 7, 8, decimal point and percent sign; 5, 7 and 8 are sourced from HP/MP glyphs and still need independent XP-bar examples. Missing digits, changed geometry, additional UI content and ambiguous matches fall back to the existing status OCR. The existing live-reading confirmation rules remain in place. Chat OCR is unchanged. Additional verified native-size screenshots are needed to extend coverage; no automatic template learning from uncertain OCR.

The supplied Character Status window adds verified XP-bar 2 and 6 and a second 5 mask; MP supplies 9. The white bar library now contains nine digits (3 missing), decimal and percent. The gold text in the detailed stats and the level badge remain separate fonts. No raw full-window screenshot is retained.

### Medium consumable text

The observed OCR aliases `Use Soulshot: No Grads,` and `Use Soulshot: Ne Grace,` can now be recovered as the canonical No Grade Soulshot activation when at least two complete readings agree and the message has the dedicated #00AAFF consumable colour. Other grades, Spiritshots, conflicting valid messages, shared colours and single uncertain readings are not automatically corrected. This is a targeted text recovery rule, not a complete Medium glyph library. Existing reviews are not rewritten.

## Native chat recognition (v0.55 experimental)

Settings → Tracking → Native chat recognition enables the existing Large numeric path and new native-size profiles for Large, Medium and Small. It remains opt-in, using the existing preference. Restart the session after changing it. The new profiles recognise personal XP/SP, obtained Adena and No Grade Soulshot using the distinct magenta, yellow and blue palette. Digits must match exact shapes at both thresholds; fixed reward words allow at most two changed bits and Soulshot words require exact shapes. Unknown digits, conflicting shapes, unsupported messages, shared colours and clipped rows fall back to OCR. Spiritshots and arbitrary item names are not yet supported. Only labelled system-message masks are retained, never world chat or screenshots. In a development check, 15 of 22 rows from four separate screenshots matched and seven abstained; no wrong values were observed. Thresholds were selected on this small sample, so this is not an independent accuracy benchmark or live capture test.

## Auto-fit chat binding

Draw a rough rectangle enclosing the entire **system-message panel**, including its frame and scrollbar, but not the separate world/general chat panel. With at least three contiguous visible messages and the correct configured chat size and colours, click Auto-fit chat in the binding editor. It measures the actual row spacing and removes excess bottom margin while preserving the selected width and top. Check the preview includes the entire final message, then save. If detection is uncertain, the rectangle is unchanged; select a smaller region or adjust manually. The fitted geometry stays fixed during capture; changing chat size, panel position or size may require rebinding. No full-window capture beyond the existing binding workflow, dynamic cropping, new preferences or saved-data migration is introduced.

### Additional OCR recovery (v0.55.2)

The dedicated blue No Grade Soulshot fallback also recognizes observed `Ni Grade`, `Ho Grade`, `Wo Grade`, and `Heo Grade` aliases. `Ao Grade` may contribute a vote only when another reading supports No Grade; Ao alone is ambiguous with A Grade. Conflicting valid grades and shot types remain rejected. The item-colour fallback resolves exactly two complete `Recipe: Blue Diamond Necklace` readings with one `Recipe: Blue Ciamond Necklace` reading, personal acquisition only, no conflicting quantity or other name. This is not general fuzzy item matching. Saved reviews are not automatically rewritten; the native chat templates remain unchanged.

### Small Soulshot full-line recovery (v0.55.3)

A dedicated exact 9 × 135 pixel No Grade Soulshot signature at blue thresholds 230 and 250 is used after ordinary OCR cannot agree, only for the distinct #00AAFF consumable colour. Both complete masks must match; any parsed conflicting event blocks this recovery. It works even if experimental native recognition is disabled. Large/Medium OCR paths are unchanged. Four rows in one screenshot supplied the masks; 10 of 13 rows from the other four supplied Small screenshots matched both thresholds, with three abstentions. This is a development check, not a live accuracy estimate. No actual other-grade samples were available for negative validation.

Small Soulshot OCR fallback (v0.55.4): `Wis Grade` is an additional weak alias, accepted only with a stronger complete No Grade-like reading such as `Wo Grade`. Damaged prefixes such as `Lise` do not contribute a vote. Weak aliases alone and conflicting valid grades or shot types remain uncounted. The exact pixel templates are unchanged.

## Auto-fit compact player frame (v0.55.5)

In Settings → Player status, choose Select player frame, draw around the whole compact player frame (level/name, HP, MP and XP), then click Auto-fit player. The detector uses the red HP and blue MP bars to locate the native level badge and percentage. Both candidate crops must be readable by the existing status recogniser before either replaces its draft binding. Check the displayed values and outlines, then save. The two standard digit regions and (since v0.56) verified compact-frame/bar geometry are persisted. Manual field binding remains available. This version is calibrated to the supplied native compact frame; other layouts/scaling, nearly empty bars or clipped/obscured frames may need manual selection. The detailed Character Status window is not supported by this auto-fit.

## HP / MP tracking foundation (v0.56)

Rebind using Select player frame → Auto-fit player after updating. The compact frame and bar geometry are now saved in addition to the original level/XP rectangles. The frame remains protected from overlay placement. During an unpaused live session, HP/MP bar fill is sampled about every 250 ms (subject to UI polling and capture latency), with separate slower numeric OCR. Two matching numeric readings must agree with the measured fill. Exact values expire when stale or the fill changes; a `~` percentage is approximate and an em dash means unavailable. Empty or heavily obscured bars may be unavailable. Enable Show HP/MP in the main HUD gear, then choose Health (HP) and Mana (MP) under its own Visible widgets. The panel is off by default on new installations. Older digit-only bindings still work but have no HP/MP data. No health/mana event history or automated gameplay is added. Animated orbs are deferred until this foundation is validated.

### Independent HP/MP HUD (v0.56.3)
HP and MP now belong to their own native overlay. Use Main HUD gear → Show HP/MP or the HUD settings page. Previously enabled HP/MP widgets migrate automatically; new installations keep it hidden until enabled. Its own gear controls the two values, row arrangement and frame binding. Unlock and drag to reposition; its position persists separately. Hide/show does not change tracking or other panels. Vital readings update up to four times per second. The optional first globe style is available from v0.57.

### HP/MP display modes and globes (v0.57)

HP/MP HUD gear → Display style offers Numbers (default) or Globes. HP text and MP text independently offer Value, Percent or Both (default). Exact values are never replaced by percentages in Value mode. Both reserves the value slot with a dash while numeric OCR is unavailable (e.g. `— - ~31%`). Percent uses verified numeric percentage when available, otherwise the estimated bar fill with a ~ marker. The globe uses fresh measured fill, not the formatted text, and unavailable fill is grey rather than interpreted as zero. Both globes share the existing movable panel, row arrangement, font size and opacity. This is a first static circular fill design with live updates, not animated liquid or independent per-globe placement. Capture and verification rules are unchanged.

### Independent transparent globes and numeric OCR (v0.58)

Globes mode hides the rectangular HP/MP panel and shows individual click-through health and mana globes. Main HUD gear → HP/MP and globe settings provides separate Move and Resize commands. Sizes (80–240 px) and positions persist separately. From v0.59.1, Move shows a temporary drag bar above the selected globe; drag it and click its padlock to save and hide the bar. Shift placement is no longer used for globes. Numbers remain a separate conventional panel. Numeric OCR now uses independent bounded workers and alternate luminance masks; a verified pair can survive a static bar calibration offset but is rejected when the measured fill moves or the reading expires. No values are derived from guessed maxima. Live Windows validation is required, especially for layered colour-key transparency and OCR under varying backgrounds.

### Ornate glass globes (v0.59)

Globes now use an original supersampled bronze frame, dark glass cavity, curved red/blue liquid surface, specular highlight and per-pixel alpha via UpdateLayeredWindow. Both text mode places the percentage above the exact value; Value and Percent use a single centered line. Settings preview renders the same art. No image assets or font files are bundled; the renderer uses the installed Windows Segoe UI font with a Pillow fallback. Existing independent positions, sizes (80–240 px), opacity, click-through behaviour and OCR rules are retained. Liquid curvature is static, not animated. Windows visual validation is required.
