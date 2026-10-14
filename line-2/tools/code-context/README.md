# Allowance Code Context

Bind an ERC-20 permission inventory to runtime-code observations for **every active spender at the exact same token and block hash**. This prevents a detached, incomplete or wrong-block code report from appearing to cover measured permissions. Python 3.10+, standard library only; uses adjacent Line 2 sources already included in the repository. No installation or network is needed for the demonstration.

From the repository root, one command shows it working:

```sh
python3 -B line-2/tools/code-context/code_context.py
```

## What happened when tried

The offline demonstration recomputed the saved real ZTO inventory and PublicNode code observations at Ethereum block **26,187,572**, hash `0xfbdf6fb511bd7ee2e74dd1b2bd8982e05e2d4cf8d10e495e6b9789bc50e7997f`. It returned `context_matched`: 19 measured pairs, three active permissions and two distinct active spenders with runtime lengths of 2,133 and 8,285 bytes. Two active permissions have empty balances and remain explicitly active. This is historical replay, not a new chain read or a current-tip claim. No invented observation is used in the demonstration.

Twelve focused tests passed, covering real evidence, token/chain/block mismatch, missing and extraneous code coverage, empty runtime with active permission, false empty-code hashes, forged counters and boolean chain IDs, duplicate spenders, wrong row anchors, input digest binding, bounded workspace-only duplicate-rejecting input loading, and CLI exits. Test mutations are synthetic and never delivered as chain observations.

## Your own evidence

```sh
python3 -B line-2/tools/code-context/code_context.py --observation path/to/inventory.json --runtime path/to/code.json
```

Both paths must resolve inside the current workspace. Each JSON input is limited to 96 KiB; duplicate keys are rejected. The observation is raw Allowance Lens evidence or an Allowance Changes inventory, not a summarized decision. The code input is an `active-allowance-spender-code-v1` report from `tools/spender-code/spender_code.py`. That read-only collector accepts a real ZTO or IMD inventory and requests code at its canonical block hash with its own User-Agent. Read its source and README before using it. This checker makes no network calls.

The checker validates the raw permission inventory, every runtime row, exact chain/token/block identity, reported pair and active-spender counts, and empty-runtime hash consistency. All distinct active spenders must have a code row, with no extra inactive or unrelated spender rows. A missing code row leaves permission active and returns `incomplete_code_context`; an extra row also prevents matching. Zero-allowance pairs remain in the output but require no code observation. An all-zero, nonempty inventory can match an explicitly empty code report; the ancestor collector currently requires at least one active spender, so it does not produce this case itself.

Exit **0** means the evidence context matches. Exit **3** means runtime coverage is incomplete or extraneous. Exit **1** means malformed or inconsistent evidence. Each raw input has a SHA-256 digest over parsed, sorted compact JSON. These digests bind the inputs, not a provider's identity.

```sh
python3 -B -m unittest discover -s line-2/tools/code-context -p 'test_*.py' -v
```

Matching is evidence association, never permission-policy approval, transaction authority or a safety claim. RPC observations and reported runtime hashes are trusted inputs, not proofs; this tool has no raw code bytes to recompute the code hashes. Code presence does not identify control, a proxy target or behavior. An empty runtime or empty balance never revokes a nonzero allowance. Unknown spenders, Permit2, signatures, custom authorization and later state remain outside coverage. Pair exposure bounds overlap per owner and cannot simply be summed. Nothing reads secrets, keys, wallets or environment variables, signs, sends, pays, posts or deploys.
