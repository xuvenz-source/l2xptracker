# Colour tracking (v0.30)

Configure Reborn system messages: XP/SP magenta, Adena yellow, item acquisitions green and consumable usage sky blue. The filters were calibrated against observed RGB (255,13,255), (255,255,13), (13,255,13), and (13,194,255). Existing beige/yellow clients retain legacy OCR fallback. Use the Reviews category filters to correct uncertain messages, including unreadable colour-classified rows.

Consumable counts represent observed use messages (one activation per message), not necessarily inventory units. Enable/disable notices and ordinary skill messages are not usage. History and CSV retain separate consumable event types. The tracker cannot recover messages that scroll past between captures or distinguish identical frames with no detectable scroll. No game process memory or network inspection is used.
