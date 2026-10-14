# Gathering 18 — The Open Fork

All four latest tools were tried; all 174 expected command exits matched and
1,202 tests passed. `REPORT.md` covers each line, confirms Line 4's previous
malformed-return defect is repaired, and gives bounded completion targets.
`COINS.md` requests no coin. No line folder changed.

Run all offline tool checks from the workspace root:

```sh
python3 -B gathering/check_tools.py
```

The new shared dependency/call report preserves open structural dependencies
beside a proof-backed historical call. Its real ZTO demonstration works offline:

```sh
python3 -B shared/frontier-report/frontier_report.py --demo
```

`shared/frontier-report/README.md` also gives the real IMD replay, which deliberately
exits 3 and retains 34 unresolved sites despite a valid supply return. Evidence
is committed as ordinary JSON, and every runtime dependency is standard-library
Python or existing committed source. The optional read-only gathering collector
is not needed for verification; read it before using it to make new RPC calls.

The finished image is `artifacts/gathering/wall-v18.png`, 1254 × 1254 RGB PNG.
The companion is `dist/gathering/18.jpg`, a 512 × 512 baseline JPEG; the record is
`dist/gathering/18.json`. `VISUAL.md` records exact additive pixel preservation,
five-digit hand review and limitations. Required artifact files remain untracked.
Rebuild the self-contained gallery with `python3 -B gathering/build_index.py`.
Run `python3 -B gathering/check_delivery_18.py` for local output/scope checks.
