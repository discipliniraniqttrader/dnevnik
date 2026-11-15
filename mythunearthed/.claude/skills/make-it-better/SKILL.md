---
name: make-it-better
description: Raise a MythUnearthed Short to viral quality. Use when the owner says /make-it-better or asks to improve a script, animation or video. Applies the viral script and animation rules in MAKE_IT_BETTER.md and scores the result.
---
# make-it-better
1. Read `MAKE_IT_BETTER.md` (viral script rules, viral animation rules, scorecard) and `QUALITY.md`.
2. Script work (QUILL): rewrite `topics/<topic>/script.json` to 40–50 s with a ≤8-word hook, an open loop closed in the last third, pattern breaks every 4–6 s, a loop ending with an A/B question. Keep every fact sourced; claims stay claims.
3. Animation work (PRISM): render with `python3 make_short.py topics/<topic>` (viral style: big centered captions with keyword pop, progress bar, numbered reveals, Ezra reactions ≥35%, 1.2–2 s shots, no flashes).
4. Review (HELM): read `topics/<topic>/out/<topic>_sheet.png` and `report.json`; score against the table; send back anything below minimum; write the 2+ improvements vs. the previous video into report.json `improvements`.
