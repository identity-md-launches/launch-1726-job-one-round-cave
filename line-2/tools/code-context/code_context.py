#!/usr/bin/env python3
"""Bind active-spender runtime observations to an exact ERC-20 inventory."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'permission-gate'))
import permission_gate as gate
sys.path.insert(0, str(HERE.parent / 'code-delta'))
import code_delta as code


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def check(observation, runtime):
    measured = gate.changes.flatten(observation)
    gate.lens.require(measured['chain_id'] == 1 and
                      measured['token_address'] in gate.lens.TOKENS.values(),
                      'inventory must select real ZTO or IMD on Ethereum')
    gate.lens.require(bool(measured['pairs']), 'empty inventory cannot establish context')
    # Ancestor validation checks every code row's address, length, hash and anchor.
    gate.lens.require(type(runtime.get('chain_id')) is int, 'chain id must be an integer')
    report = code.validate(runtime)
    for key in ('chain_id', 'token', 'token_address', 'block_number', 'block_hash'):
        gate.lens.require(measured[key] == report[key], 'code and inventory differ on ' + key)
    gate.lens.require(runtime.get('source') in gate.lens.PUBLIC_ENDPOINTS,
                      'code source must be a documented public Ethereum endpoint')
    active = {spender for (_, spender), row in measured['pairs'].items()
              if int(row['allowance_raw']) > 0}
    for field, count in (('measured_pair_count', len(measured['pairs'])),
                         ('active_spender_count', len(active))):
        gate.lens.require(type(runtime.get(field)) is int and runtime[field] == count,
                          'code report disagrees on ' + field)
    empty_hash = hashlib.sha256(b'').hexdigest()
    for row in report['spenders'].values():
        gate.lens.require((row['bytes'] == 0) == (row['sha256'] == empty_hash),
                          'empty runtime length and hash disagree')
    observed = set(report['spenders'])
    missing, extra = sorted(active - observed), sorted(observed - active)
    matched = not missing and not extra
    pairs = []
    for (owner, spender), row in sorted(measured['pairs'].items()):
        allowance = int(row['allowance_raw'])
        runtime_row = report['spenders'].get(spender) if allowance else None
        status = ('inactive_permission_code_not_required' if not allowance else
                  'active_permission_code_not_observed' if runtime_row is None else
                  'active_permission_with_runtime' if runtime_row['bytes'] else
                  'active_permission_without_runtime')
        pairs.append({'owner': owner, 'spender': spender, 'status': status,
                      'allowance_raw': row['allowance_raw'], 'balance_raw': row['balance_raw'],
                      'spendable_upper_bound_raw': row['spendable_upper_bound_raw'],
                      'empty_balance_active_permission': bool(allowance) and int(row['balance_raw']) == 0,
                      'runtime': runtime_row})
    return {
        'schema': 'allowance-code-context-v1',
        'status': 'context_matched' if matched else 'incomplete_code_context',
        'context_matched': matched, 'chain_id': 1, 'token': measured['token'],
        'token_address': measured['token_address'],
        'block_number': measured['block_number'], 'block_hash': measured['block_hash'],
        'measured_pair_count': len(pairs), 'active_spender_count': len(active),
        'missing_active_spenders': missing, 'extra_code_spenders': extra,
        'active_pair_count': sum(int(row['allowance_raw']) > 0 for row in pairs),
        'empty_balance_active_pair_count': sum(row['empty_balance_active_permission'] for row in pairs),
        'pairs': pairs, 'complete_wallet_audit': False,
        'input_sha256': {'observation': digest(observation), 'runtime': digest(runtime)},
        'limitations': [
            'Context matching is evidence association, not permission-policy approval or transaction authority.',
            'Only supplied standard ERC-20 owner/spender pairs are covered; undiscovered approvals, Permit2 and signatures remain unknown.',
            'An empty balance or empty runtime never clears a nonzero spending permission.',
            'Runtime hashes describe reported bytes, not controller, proxy implementation or behavior.',
            'Both inputs are trusted RPC observations, not state proofs or authenticated chain history.',
            'Historical matching says nothing about current state, later code changes or future execution.',
            'Pair exposure bounds overlap per owner and must not be added together without a balance cap.',
        ],
    }


def demo_inputs():
    return (gate.load(HERE.parent / 'bundle-refresh' / 'live-after.json'),
            gate.load(HERE.parent / 'code-delta' / 'example-report.json'))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--observation', help='workspace raw Allowance Lens/Changes inventory')
    parser.add_argument('--runtime', help='workspace Spender Code report at the same block')
    args = parser.parse_args(argv)
    try:
        gate.lens.require((args.observation is None) == (args.runtime is None),
                          'provide both inputs, or neither for the historical ZTO demo')
        demo = args.observation is None
        inputs = demo_inputs() if demo else (gate.load(args.observation), gate.load(args.runtime))
        result = check(*inputs)
        result['demonstration'] = demo
        print(json.dumps(result, indent=2))
        return 0 if result['context_matched'] else 3
    except (ValueError, KeyError, TypeError, AttributeError, OSError, OverflowError, RecursionError) as exc:
        print(json.dumps({'error': str(exc)}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
