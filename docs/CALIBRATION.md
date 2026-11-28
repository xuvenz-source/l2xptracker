# Chat calibration

In Settings → Tracking, select View / edit bound areas and bind visible system-message text. Include complete rows; exclude scrollbars. Keep the game windowed/borderless and chat unobstructed. Rebind after changing game font, scaling or layout.

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

Apply chat settings before tracking. Shared colours are distinguished by text; uncertain rows may require review. Experimental large-text numeric recognition is off by default. It falls back to OCR when digit templates are uncertain.

## Troubleshooting

If the game is covered, minimised or resized, visible-pixel capture cannot read it safely. Check bound areas, text spacing and colours, then compare short-session totals against the game. Reviews correct uncertainty; no method can reconstruct messages that scrolled past unseen. Settings → Advanced provides optional OCR evidence and local diagnostics. Remove sensitive player names before sharing.

Large-text slash recovery: for exact magenta personal XP/SP and yellow personal Adena, a failed OCR amount containing a slash can be checked against verified full-line glyphs at two thresholds and isolated digits-only OCR. The XP/SP fallback never overrides a conflicting valid number. A standalone slash in the Adena amount is also eligible for verification. This is not global slash replacement and does not expand support to Medium glyphs. Unverified fields remain in review.

## Character level and experience percentage

The fixed-size character status font is independent of chat text size. Bind the level badge and the XP percentage including the decimal and percent sign, but exclude the name, HP and MP. Saving bound areas now checks the selected fields against the captured image and reports their readings in Settings → Player status. Live automatic readings still require confirmation and reject conflicting valid numbers. Low-confidence fields are not guessed. The status reader uses alternate thresholds, contrast and scaling if the normal two passes cannot agree.

### Native status digit recogniser (initial coverage)

Character level and XP percentage now attempt exact native pixel matches at two brightness thresholds before OCR. The separate level badge library initially contains 0 and 2. The white status font contains 0, 1, 4, 5, 7, 8, decimal point and percent sign; 5, 7 and 8 are sourced from HP/MP glyphs and still need independent XP-bar examples. Missing digits, changed geometry, additional UI content and ambiguous matches fall back to the existing status OCR. The existing live-reading confirmation rules remain in place. Chat OCR is unchanged. Additional verified native-size screenshots are needed to extend coverage; no automatic template learning from uncertain OCR.

The supplied Character Status window adds verified XP-bar 2 and 6 and a second 5 mask; MP supplies 9. The white bar library now contains nine digits (3 missing), decimal and percent. The gold text in the detailed stats and the level badge remain separate fonts. No raw full-window screenshot is retained.

### Medium consumable text

The observed OCR aliases `Use Soulshot: No Grads,` and `Use Soulshot: Ne Grace,` can now be recovered as the canonical No Grade Soulshot activation when at least two complete readings agree and the message has the dedicated #00AAFF consumable colour. Other grades, Spiritshots, conflicting valid messages, shared colours and single uncertain readings are not automatically corrected. This is a targeted text recovery rule, not a complete Medium glyph library. Existing reviews are not rewritten.

## Native chat recognition (v0.55 experimental)

Settings → Tracking → Native chat recognition enables the existing Large numeric path and new native-size profiles for Large, Medium and Small. It remains opt-in, using the existing preference. Restart the session after changing it. The new profiles recognise personal XP/SP, obtained Adena and No Grade Soulshot using the distinct magenta, yellow and blue palette. Digits must match exact shapes at both thresholds; fixed reward words allow at most two changed bits and Soulshot words require exact shapes. Unknown digits, conflicting shapes, unsupported messages, shared colours and clipped rows fall back to OCR. Spiritshots and arbitrary item names are not yet supported. Only labelled system-message masks are retained, never world chat or screenshots. In a development check, 15 of 22 rows from four separate screenshots matched and seven abstained; no wrong values were observed. Thresholds were selected on this small sample, so this is not an independent accuracy benchmark or live capture test.

## Auto-fit chat binding

Draw a rough rectangle enclosing the entire **system-message panel**, including its frame and scrollbar, but not the separate world/general chat panel. With at least three contiguous visible messages and the correct configured chat size and colours, click Auto-fit chat in the binding editor. It measures the actual row spacing and removes excess bottom margin while preserving the selected width and top. Check the preview includes the entire final message, then save. If detection is uncertain, the rectangle is unchanged; select a smaller region or adjust manually. The fitted geometry stays fixed during capture; changing chat size, panel position or size may require rebinding. No full-window capture beyond the existing binding workflow, dynamic cropping, new preferences or saved-data migration is introduced.
