# Sources retained

- `line-3/tools/code-dependency-frontier/code_dependency_frontier.py`: copied as
  `dependency_frontier.py`; only the import-root path changed to reuse the
  committed Line 3 proof and structural scanner dependencies.
- `shared/rehearsal-report/proof_report.py`: reused without modification to bind
  exact call, source proof, block, selector, canonical arguments and return ABI.
- `shared/surface-return/zto-proof.json` and `zto-call.json`: real saved ZTO demo.
- `line-3/tools/code-routes/imd-proof.json` and
  `line-3/tools/code-target-proofs/imd-target-proof.json`: real same-block source
  and discovered target evidence. IMD call bytes were collected read-only at
  their block, not inferred from a report or synthesized.
- `line-4/tools/call-rehearsal/rehearse.py`: reused in the gathering's bounded
  collector for public RPC, calldata and observation validation.

Every line original is unchanged. Runtime needs no third-party dependency.
