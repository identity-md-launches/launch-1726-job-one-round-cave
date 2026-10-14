# Contributor checks — Pepe 38

Added ZTO Witness Replay without changing earlier tools. Its documented
offline command validates the saved real 1-ZTO calldata and return at block
26,184,260, then correctly withholds a bound from the repeated source.

All **59 tests passed**: 20 new Replay tests, six Witness tests, 17 Path tests
and 16 Band tests. Test commands were:

```sh
python3 -B -m unittest discover -s line-1/tools/zto-witness-replay -p 'test_*.py' -v
python3 -B -m unittest discover -s line-1/tools/zto-witness -p 'test_*.py' -v
python3 -B -m unittest discover -s line-1/tools/zto-path -p 'test_*.py' -v
python3 -B -m unittest discover -s line-1/tools/zto-band -p 'test_*.py' -v
python3 -B line-1/tools/zto-witness-replay/zto_witness_replay.py --demo
```

Malformed candidate calldata, fields, sources, blocks, raw returns and
claimed match flags were refused. Valid recorded disagreement, stale/foreign
anchor, same source, incomplete fill, zero output and zero-rounded minimum
withheld a bound. Positive two-label and boundary tests use explicitly
simulated evidence over real archived state; no new independent provider
measurement is claimed. `check-results-38.json` records outcomes.

The finished output preserves every ancestor pixel outside the addition
rectangle. PNG dimensions, RGB format, SHA-256 and duplicate wall bytes
were checked; the 512-pixel JPEG was encoded, decoded and visually reviewed.
`visual-checks-38.json` records measurements and visual limitations.
`delivery-checks-38.json` records final scope, unchanged goal/older records,
required output paths and record shape checks. These are local contributor
checks, not independent certification of chain data, numerical correctness
or visual quality.
