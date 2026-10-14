# Dependency-backed Call Report

Review a saved Ethereum call alongside the unresolved code dependencies of its
proof-backed runtime. This joins Line 3's Code Dependency Frontier to the shared
Line 3/4 Proof-backed Rehearsal Report. Python 3.10+, standard library only.
Run from the workspace root:

```sh
python3 -B shared/frontier-report/frontier_report.py --demo
```

When tried, the saved real ZTO `totalSupply()` call aligned with its raw code
proof and decoded `1000000000000000000000000000` raw units. The bounded structural
scan found one runtime and no external-call instructions. The status was
`ready-to-review-bounded-scan`, exit 0. That status is a review aid, not approval.
The reproducible output is `zto-demo.json`; no RPC is needed to replay it.

The real IMD example was captured read-only from PublicNode at decimal Ethereum
block **26,188,209**, hash
`0x1dfd9e5522e0883294299de66aafcf57f28fa4f9a431b1858a728cae919e5b6e`.
The collector compared the returned block number back to decimal, matched the
saved proof hash and runtime bytes, and pinned the call by canonical block hash.
Its raw observation is `imd-call.json`, an ordinary committed file. Replay it:

```sh
python3 -B shared/frontier-report/frontier_report.py --bundle line-3/tools/code-routes/imd-proof.json --observation shared/frontier-report/imd-call.json --signature 'totalSupply()' --types uint256 --target-proof line-3/tools/code-target-proofs/imd-target-proof.json
```

This intentionally exits **3**, with `review-with-open-frontier`: the valid
historical return decoded `4174192949067000000000000` raw IMD units, while two
proved runtimes still contain **34 unresolved structural call sites**. Without
the target proof, the report retains one missing constant target and eleven
unresolved sites. Open sites are not necessarily reached by `totalSupply()`.
The complete replay output is `imd-demo.json`.

Supply a raw source Code Proof bundle, raw Call Rehearsal observation, explicit
signature and flat ABI return types. Repeat `--target-proof` up to sixteen times.
An optional `--anchor-hash` checks equality to your separately selected hash;
it cannot authenticate that choice. Every proof is reverified; the identical
source bundle anchors both the call and dependency scan. Additional proofs must
be reached constant targets at the exact same block. Every input must remain
inside the workspace, and inherited readers reject duplicate JSON keys and
oversize files. Exact caller, calldata and native value remain in `call`.

| Exit | Status | Meaning |
| --- | --- | --- |
| 0 | `ready-to-review-bounded-scan` | Call aligns; supplied structural scan has no open site. |
| 3 | `review-with-open-frontier` | Call aligns; missing target proofs or unresolved operands remain. |
| 2 | `call-context-withheld` | Call/proof/ABI checks disagree; decoded values and return are withheld. |
| 1 | `invalid` | Malformed evidence, corrupt/unrelated/duplicate/wrong-block proofs, or file errors. |

Argument syntax errors conventionally exit 2. Results use stdout; invalid-input
errors use stderr. Canonical input digests bind content, not a trusted identity.
The tool writes nothing and makes no network request.

Ten focused tests passed, including both real examples, missing proof visibility,
wrong call block and selector, malformed return, corrupted target proof, unrelated
and duplicate proofs, wrong proof block, anchor mismatch, and CLI exit behavior:

```sh
python3 -B -m unittest discover -s shared/frontier-report -p 'test_*.py' -v
```

## Dependencies and limits

`dependency_frontier.py` is promoted from Line 3 with only its dependency-root
path adapted. Keep the committed Line 3 `code-targets`, `code-calls`,
`code-surface`, `code-opcodes`, `code-ancestry`, `code-proof` and `code-lens`
folders, plus `shared/rehearsal-report` and `shared/surface-return` with their
existing nested sources. Both demonstrations use those committed evidence files.
There are no external packages or network installation requirements.

Proof inclusion is relative to the supplied header; consensus authenticity is
not established. RPC returns and chosen ABI layouts remain unproved claims.
The structural scan does not model actual execution, call-specific reachability,
dynamic targets or complete dependencies. Even a closed bounded scan cannot
establish safety. No freshness, permission, gas, state effects or future result
is promised. ZTO first and IMD second suffice; no new coin is needed. No wallet,
key, secret or environment is read and nothing is signed, sent, paid or deployed.
