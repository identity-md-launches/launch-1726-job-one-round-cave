# Rehearsal Report

Validate a saved Ethereum call rehearsal and present its exact context and raw
result before a worker reviews it. Python standard library only, offline.

Run from the repository root:

```sh
python3 -B line-4/tools/rehearsal-report/rehearsal_report.py
```

Tried on 2026-10-14: this replay of the ancestor's real ZTO `totalSupply()`
observation returned `ready-to-review`, exit 0, and decoded
`1000000000000000000000000000` raw units at block `0x18f9676`.
No new chain request was made. The saved PublicNode attribution and historical
block are retained; the result makes no claim about today's state.

Pass your own workspace-contained observation as the single positional argument.
Keep the adjacent `call-rehearsal/rehearse.py` dependency and, for the default
demo, `return-lens/zto-live-observation.json`. All are ordinary committed files.

The gathering report's malformed-return defect was reproduced before repair:
`not-hex-return-bytes` produced `ready-to-review`. The repaired report refuses it
with exit 2. It validates exact observation, block, call and outcome fields,
mainnet identity, public source, addresses, RPC quantities and bounded even-length
hexadecimal bytes. It recomputes the selected `raw`, `uint256` or `bool`
interpretation using the existing collector's decoder. It preserves an explicit
sender and relay provenance, and never invents an omitted sender or native value.
Malformed or unknown fields, duplicate keys, non-finite numbers, files over
90,000 bytes and paths resolving outside the workspace are refused.

| Status | Exit | Meaning |
| --- | ---: | --- |
| `ready-to-review` | 0 | Recorded code presence and a valid raw/uint256 return or canonical true boolean. |
| `withheld` | 1 | False boolean, unexpected typed length/encoding, revert, RPC failure or unconfirmed code. |
| `invalid` | 2 | Invalid input; error JSON goes to stderr and no favorable report is emitted. |

An empty raw return is valid encoding with **no inferred meaning**. A reverted
call may be precisely what the reviewer intended; use Revert Expectation for
that policy. This summary deliberately withholds it rather than implying success.
Error payloads, when present, must be raw hexadecimal bytes; provider-specific
nested payloads are unsupported and refused.

`ready-to-review` validates encoding, not truth or transaction safety. The ABI
choice, recorded code flag, RPC return and header are untrusted assertions. This
does not authenticate a chain or ABI, prove code, freshness, authorization, gas,
state effects or future execution. A raw response is not decoded economic meaning.
No wallet, key, secret, environment variable, signature, payment, transaction,
post or deployment is read or made.

The fourteen adversarial regressions passed, including the actual reported
malformed input, incorrect bools, short/empty typed returns, context substitutions,
ambiguous outcomes, code flags, relay flags, strict JSON, file bounds and CLI exits:

```sh
python3 -B -m unittest discover -s line-4/tools/rehearsal-report -p 'test_*.py' -v
```
