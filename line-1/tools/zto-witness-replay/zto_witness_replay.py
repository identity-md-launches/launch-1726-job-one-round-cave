#!/usr/bin/env python3
"""Offline, request-bound replay of two saved ZTO/IMD liquidity witnesses."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'zto-witness'))
import zto_witness as witness

path = witness.path
require = path.z.require
CHECK_KEYS = {'schema', 'block', 'source', 'quoter', 'all_match', 'results'}
ROW_KEYS = {'input_token', 'amount', 'request', 'raw_result', 'local_output_raw',
            'initialized_ticks_crossed', 'matches'}
LIMITATIONS = [
    'Saved RPC data and endpoint labels are not authenticated state or proof of independent providers.',
    'The caller supplies the block anchor and reference height; no current freshness is measured.',
    'Arithmetic is inherited, not independently proved; coverage is limited to the saved bitmap.',
    'The positive planning minimum is not enforced by a router or receipt.',
    'No token settlement, gas, MEV, future state, signing or sending is modeled.',
]


def pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, 'duplicate JSON key: ' + key)
        result[key] = value
    return result


def unsupported_number(value):
    raise ValueError('JSON floats and nonfinite numbers are unsupported')


def read_json(filename):
    with path.z.workspace_file(filename).open('rb') as handle:
        data = handle.read(100001)
    require(len(data) <= 100000, 'JSON exceeds 100 KB')
    return json.loads(data, object_pairs_hook=pairs, parse_float=unsupported_number,
                      parse_constant=unsupported_number)


def digest(value):
    data = json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode('ascii')
    return hashlib.sha256(data).hexdigest()


def header(observation):
    block = observation['base']['block']
    require(type(block) is dict and set(block) == {'number', 'hash', 'timestamp'},
            'block must have exactly number, hash and timestamp')
    for field in ('number', 'timestamp'):
        require(type(block[field]) is str and
                re.fullmatch(r'0x(?:0|[1-9a-f][0-9a-f]*)', block[field]) is not None,
                'noncanonical block ' + field)
    require(type(block['hash']) is str and
            re.fullmatch(r'0x[0-9a-f]{64}', block['hash']) is not None,
            'invalid block hash')
    require(path.z.INIT_BLOCK <= int(block['number'], 16) < 1 << 64,
            'block number out of range')
    require(0 < int(block['timestamp'], 16) < 1 << 64, 'block timestamp out of range')
    path.z.validate_endpoint(observation['base']['source'])
    return block


def expected_request(observation, token, amount):
    """Canonical empty-hook-data exact-input ABI, matching Path's measured call."""
    state, _, _ = path.decode(observation)
    decimals = state['decimals'][1 if token == 'ZTO' else 0]
    raw = path.z.parse_amount(amount, decimals)
    require(raw < 1 << 127, 'input must fit positive int128 pool delta')
    values = [32, int(path.z.IMD, 16), int(path.z.ZTO, 16), 12500, 60,
              int(state['hook'], 16), int(token == 'IMD'), raw, 256, 0]
    data = path.selector('quoteExactInputSingle(((address,address,uint24,int24,address),bool,uint128,bytes))')
    data += b''.join(path.z.word(v) for v in values).hex()
    return {'to': path.QUOTER, 'data': data}


def check_source(observation, check, token, amount, quote):
    require(type(check) is dict and set(check) == CHECK_KEYS, 'unexpected quoter check fields')
    require(check['schema'] == 'zto-path-quoter-check-v1', 'unexpected quoter check schema')
    require(check['source'] == observation['base']['source'], 'quoter source mismatch')
    require(check['block'] == observation['base']['block'], 'quoter block mismatch')
    require(check['quoter'] == path.QUOTER, 'quoter contract mismatch')
    require(type(check['all_match']) is bool, 'all_match must be boolean')
    require(type(check['results']) is list and len(check['results']) == 1,
            'expected exactly one quoter result per source')
    row = check['results'][0]
    require(type(row) is dict and set(row) == ROW_KEYS, 'unexpected quoter result fields')
    require(row['input_token'] == token and row['amount'] == amount, 'quoter candidate mismatch')
    request = row['request']
    require(type(request) is dict and set(request) == {'to', 'data'} and
            request == expected_request(observation, token, amount),
            'quoter request does not match pool, direction, amount and empty hook data')
    actual = path.z.words(row['raw_result'], 2)[0]
    require(type(row['local_output_raw']) is str and
            re.fullmatch(r'(?:0|[1-9][0-9]*)', row['local_output_raw']) is not None,
            'local output must be a canonical raw-unit string')
    require(type(row['matches']) is bool, 'matches must be boolean')
    require(type(row['initialized_ticks_crossed']) is int and
            row['initialized_ticks_crossed'] == quote['initialized_ticks_crossed'],
            'local crossed-tick count mismatch')
    if quote['status'] != 'estimated':
        return False
    expected = quote['estimate']['output_raw']
    computed = actual == int(expected)
    require(row['local_output_raw'] == expected, 'claimed local output differs from recomputation')
    require(row['matches'] is computed and check['all_match'] is computed,
            'claimed quoter match flags differ from raw return comparison')
    return computed


def replay(first, second, check_a, check_b, token, amount, slippage_bps,
           expected_block_hash, reference_block, max_age_blocks):
    require(token in ('ZTO', 'IMD'), 'input must be ZTO or IMD')
    require(type(amount) is str, 'amount must be a decimal string')
    require(type(slippage_bps) is int and 0 <= slippage_bps <= 9999,
            'slippage bps must be 0..9999')
    require(type(expected_block_hash) is str and
            re.fullmatch(r'0x[0-9a-f]{64}', expected_block_hash) is not None,
            'expected block hash must be lowercase bytes32')
    for value in (reference_block, max_age_blocks):
        require(type(value) is int and 0 <= value < 1 << 64,
                'reference block and maximum age must be uint64 integers')
    blocks = [header(first), header(second)]
    quotes = [path.quote(first, token, amount), path.quote(second, token, amount)]
    matches = [check_source(first, check_a, token, amount, quotes[0]),
               check_source(second, check_b, token, amount, quotes[1])]
    comparison = witness.compare_snapshots(first, second)
    reasons = []
    if first['base']['source'] == second['base']['source']:
        reasons.append('same_source_label')
    if not comparison['same_pool_state_and_coverage']:
        reasons.append('different_block_state_or_coverage')
    if any(b['hash'] != expected_block_hash for b in blocks):
        reasons.append('caller_block_anchor_mismatch')
    ages = [reference_block - int(b['number'], 16) for b in blocks]
    if any(age < 0 or age > max_age_blocks for age in ages):
        reasons.append('outside_caller_age_limit')
    if any(q['status'] != 'estimated' for q in quotes):
        reasons.append('incomplete_local_fill')
    if not all(matches):
        reasons.append('quoter_does_not_match_complete_local_fill')
    decision = None
    if not reasons:
        decision = witness.corroborate(first, second, check_a, check_b,
                                       token, amount, slippage_bps)
        if not decision['bound_released']:
            reasons.append('ancestor_witness_withheld')
        elif int(decision['bound']['planning_minimum_raw']) <= 0:
            reasons.append('planning_minimum_rounds_to_zero')
    released = not reasons
    return {
        'schema': 'zto-witness-replay-report-v1', 'status': 'replayed' if released else 'withheld',
        'chain_id': 1, 'pool_id': path.z.POOL, 'block': blocks[0],
        'source_labels': [first['base']['source'], second['base']['source']],
        'input_token': token, 'output_token': 'IMD' if token == 'ZTO' else 'ZTO',
        'requested_input': amount, 'slippage_bps': slippage_bps,
        'caller_policy': {'expected_block_hash': expected_block_hash,
                          'reference_block': reference_block, 'max_age_blocks': max_age_blocks},
        'age_blocks': ages, 'reasons': reasons,
        'local_statuses': [q['status'] for q in quotes], 'raw_quoter_matches': matches,
        'evidence_sha256': [digest(v) for v in (first, second, check_a, check_b)],
        'bound_released': released, 'bound': decision['bound'] if released else None,
        'limitations': LIMITATIONS,
    }


def demo_inputs():
    observation = read_json(str(witness.FIXTURE))
    check = read_json(str(witness.FIXTURE.parent / 'quoter-check.json'))
    row = next(r for r in check['results'] if r['input_token'] == 'ZTO' and r['amount'] == '1')
    check = dict(check, results=[row], all_match=row['matches'])
    return observation, check


def demo():
    observation, check = demo_inputs()
    report = replay(observation, observation, check, check, 'ZTO', '1', 100,
                    observation['base']['block']['hash'],
                    int(observation['base']['block']['number'], 16), 0)
    report['mode'] = 'offline_real_historical_single_source'
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--demo', action='store_true')
    parser.add_argument('--snapshot-a')
    parser.add_argument('--snapshot-b')
    parser.add_argument('--quoter-a')
    parser.add_argument('--quoter-b')
    parser.add_argument('--input', choices=('ZTO', 'IMD'))
    parser.add_argument('--amount')
    parser.add_argument('--slippage-bps', type=int)
    parser.add_argument('--expected-block-hash')
    parser.add_argument('--reference-block', type=int)
    parser.add_argument('--max-age-blocks', type=int)
    args = parser.parse_args(argv)
    values = [getattr(args, key) for key in ('snapshot_a', 'snapshot_b', 'quoter_a', 'quoter_b',
              'input', 'amount', 'slippage_bps', 'expected_block_hash', 'reference_block', 'max_age_blocks')]
    try:
        if args.demo:
            require(all(v is None for v in values), '--demo cannot be combined with replay inputs')
            result = demo()
        else:
            require(all(v is not None for v in values), 'supply all four evidence paths and all six controls')
            evidence = [read_json(v) for v in values[:4]]
            result = replay(*evidence, *values[4:])
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0 if args.demo or result['bound_released'] else 2
    except (ValueError, KeyError, TypeError, AttributeError, OSError, OverflowError, RecursionError) as exc:
        print(json.dumps({'error': str(exc)}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
