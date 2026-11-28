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
