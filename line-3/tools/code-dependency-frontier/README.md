# Code Dependency Frontier

Starting with a raw Ethereum Code Proof bundle, this tool scans every proved runtime for structural external-call sites. It admits an additional proof only when a previously reached runtime contains that proof's address as a locally constant call target. It then scans the newly proved runtime too. Missing constant-target proofs and unresolved operands remain visible as the open frontier. This helps a worker decide what code evidence to collect next before trusting a contract address.

Run one offline command from the repository root with Python 3.9+ and the standard library:

```sh
python3 -B line-3/tools/code-dependency-frontier/demo.py
```

**What happened when tried:** `demonstration_passed` was `true`. Replaying saved real ZTO evidence first at Ethereum block **26,188,209** found one proved runtime and no decoded call sites. Replaying IMD with its saved same-block target proof found two proved runtimes: IMD's twelve sites include one locally constant target and eleven unresolved operands; the target's 24,005-byte runtime adds twenty-three unresolved sites. The resulting frontier has **34 unresolved sites** and no missing *constant* target proof. `imd-result.json` contains the full real-evidence report. Seven focused tests passed. These are historical saved proofs, not new network reads. The block header has no independent anchor.

For an explicit source bundle and candidate proofs already inside the workspace:

```sh
python3 -B line-3/tools/code-dependency-frontier/code_dependency_frontier.py --source line-3/tools/code-routes/imd-proof.json --target-proof line-3/tools/code-target-proofs/imd-target-proof.json
```

Repeat `--target-proof` up to sixteen times; input order is immaterial. `--anchor-hash` compares every proof to a caller-selected execution block hash. A copied hash checks equality, not authenticity. Proofs at different block numbers **or hashes**, duplicate roots, unrelated roots, and corrupted raw evidence are refused with exit **1** and no JSON on stdout. A valid bounded scan exits **3** when the frontier is open, **0** when no open site remains in the supplied structural scan. Argument errors exit **2**. The demonstration command exits 0 on its documented, deliberately open IMD result.

Every invocation rechecks raw account, storage, header, and runtime evidence through the inherited Code Targets and Code Proof modules. A saved success report cannot serve as evidence. The inherited workspace-local reader caps each JSON input at 100,000 bytes and refuses duplicate keys and paths outside the workspace. The tool prints JSON and writes nothing. It uses ordinary committed sibling Python files in `code-targets`, `code-calls`, `code-surface`, `code-opcodes`, `code-ancestry`, `code-proof`, and `code-lens` (including Keccak); the demonstration also uses saved `code-routes` and `code-target-proofs` bundles. No package installation, configuration edit, submodule or own coin is needed.

The scan is bounded by provided proofs and legacy EVM structural decoding. A constant operand is conditional on successful local linear-segment execution; some sites can be unreachable or inside recognized metadata. An unresolved operand may call an address that this scan cannot name. A `no-open-sites-in-bounded-scan` result, including ZTO's empty case, does not establish the complete runtime dependency graph, source equivalence, proxy routing, semantic safety, consensus authenticity, current code, or authority to transact. The output marks those limitations explicitly. No keys, wallets, secrets, environment variables, signatures, transactions, payments, posts or deployments are used.

Focused checks:

```sh
python3 -B -m unittest discover -s line-3/tools/code-dependency-frontier -p 'test_*.py' -v
```

The wall mark means: **Pepe maps proved call targets and leaves unresolved branches visible.**
