# Checks for record 38

Reproduced the gathering's defect before editing: changing the real saved ZTO
return to `not-hex-return-bytes` still yielded `ready-to-review`.
After repair, the same input yields invalid error JSON and CLI exit 2.

Commands run from the repository root on 2026-10-14:

```sh
python3 -B line-4/tools/rehearsal-report/rehearsal_report.py
python3 -B -m unittest discover -s line-4/tools/rehearsal-report -p 'test_*.py' -v
python3 -B -m unittest discover -s line-4/tools/call-rehearsal -p 'test_*.py' -v
```

The real-evidence offline demo succeeds and decodes ZTO supply as 10^27 raw
units at the saved historical block. All 14 report regressions and all 20
collector tests pass. The report suite prevents network use for its evidence
replay and checks invalid, withheld and favorable CLI exits.

The image inspector validates the named PNG and JPEG; standard-library decoded
pixel comparison establishes zero changes outside the new patch. The deliverable
check confirms the numbered schema, PNG hash link, unchanged goal and older
records, bounded new source files, and identical named/continuing PNGs.
These are local contributor checks only. No claim of authenticated provider,
ABI, canonical header, current freshness or future execution is made.
