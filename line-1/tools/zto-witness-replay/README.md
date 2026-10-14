# ZTO Witness Replay

Recompute a ZTO/IMD planning bound from two transferred pool snapshots and
their saved V4Quoter calls, without contacting any RPC. Each saved request
must encode the assigned real pool, input direction, exact amount and empty
hook data. Each return must agree with the locally recomputed complete fill.
The receiver explicitly chooses the expected block hash, reference height,
age ceiling and tolerance. Same source labels and zero-rounded minima
withhold the bound.

Python 3.10+ and standard library only. From the repository root:

```sh
python3 -B line-1/tools/zto-witness-replay/zto_witness_replay.py --demo
```

When tried, this validated the real archived **1-ZTO** calldata and raw
V4Quoter return at Ethereum block **26,184,260**. Both local calculations
and saved replies were **15,292,155,595,473 raw IMD**. It correctly returned
`withheld`, `same_source_label`, `bound_released: false`, and `bound: null`:
replaying one PublicNode capture twice does not make two witnesses. Demo exit
0 means the demonstration ran, not that a bound was released. The actual
output is `demo-report.json`. No new RPC capture or current-price claim is made.

Keep the committed sibling `zto-witness/`, `zto-path/` and `zto-band/` folders.
The demo additionally uses Path's `observation.json` and `quoter-check.json`.
There are no packages to install and no network requirement.

For your own evidence, supply every option below. Paths denote your own
workspace files; controls come from your review decision, separately from
the sender's claims:

```sh
python3 -B line-1/tools/zto-witness-replay/zto_witness_replay.py \
  --snapshot-a SNAPSHOT_A.json --snapshot-b SNAPSHOT_B.json \
  --quoter-a QUOTER_A.json --quoter-b QUOTER_B.json \
  --input ZTO --amount AMOUNT --slippage-bps TOLERANCE \
  --expected-block-hash HASH --reference-block HEIGHT --max-age-blocks AGE
```

The evidence formats are ZTO Path's `zto-path-observation-v1` and
`zto-path-quoter-check-v1`. Each check must contain **exactly one result**;
Path's `--check-quoter --save-check` produces that format when invoked for
one amount. A multi-case saved check must first be explicitly narrowed to
the intended row; the demo does this for the historical fixture. No witness
report, sender's released-bound flag or estimated-output label is accepted
as a substitute for the raw evidence.

The replay checks these before releasing a minimum:

- Canonical header fields, real pool identity, currency order, fees, hook
  restrictions, bitmap coverage and every initialized tick.
- Check source equal to its snapshot source; exact block header and Quoter
  contract; exact canonical `to` and ABI calldata, with no transaction fields.
- Exact direction and amount, raw two-word return, recomputed output and
  crossed-tick count, and boolean match flags consistent with the return.
- Distinct literal source labels and equal complete pool state/coverage.
- Both hashes equal the caller's anchor and both ages within the inclusive
  ceiling: `0 <= reference_block - observed_block <= max_age_blocks`.
- The inherited Witness comparison passes, and the rounded planning minimum
  `floor(output_raw * (10000 - slippage_bps) / 10000)` is strictly positive.

Slippage is an explicitly selected integer 0–9999. Heights and age ceiling
are nonnegative uint64 integers. Input amounts are positive plain decimal
strings with token precision, fitting the inherited positive int128 limit.
For complete fills, internally inconsistent claimed match flags are malformed
evidence; a consistently recorded raw mismatch produces a withheld result.
Incomplete fills never release a bound. The second Quoter return word is
structurally decoded but supplies no gas limit or execution guarantee.

Exit **0** means a bound was replayed (except the explicitly labeled demo).
Exit **2** means a well-formed replay withheld the bound; inspect `reasons`.
Exit **1** means malformed evidence, missing controls or file errors.
Argparse syntax errors conventionally exit 2. Reports use stdout; errors use
stderr. This tool writes no files. Files must be inside the current workspace
and at most 100 KB; duplicate JSON keys, floats and nonfinite numbers are
refused. Canonical parsed-input SHA-256 values identify the evidence, not a
provider or Ethereum consensus.

All **20 focused tests** passed, including altered ABI words, contract/source/
block mismatch, misleading return flags, age boundaries, partial fills,
zero outputs/minima, extra transaction fields and a no-network real-fixture
demo. The 39 Witness/Path/Band dependency tests also passed. Positive two-label
and tiny-output cases are **explicit simulations using copied real state**,
not claims of a second real capture or a measured tiny-output Quoter call.

```sh
python3 -B -m unittest discover -s line-1/tools/zto-witness-replay -p 'test_*.py' -v
```

This checks internal evidence consistency. Relabeling copied data can pass
the distinct-label check; distinct URLs can also share an upstream. No raw
RPC result or block anchor is authenticated, and no chain ancestry is proved.
The caller's reference height is not measured current freshness. Pool math
is reused, not independently verified. Bounds remain historical, limited to
recorded tick coverage and unenforced by a router. Settlement, token transfer
behavior, gas, MEV and future state remain outside scope. No wallet, key,
secret, environment variable, signing, send, payment, post or deployment is
used. The real ZTO/IMD pool is sufficient; no new coin is needed.
