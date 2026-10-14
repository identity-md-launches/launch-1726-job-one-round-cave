#!/usr/bin/env python3
"""Read totalSupply at a saved proof's exact block, using public mainnet RPC only."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path('line-3/tools/code-targets').resolve()))
import code_targets
sys.path.insert(0, str(Path('line-4/tools/call-rehearsal').resolve()))
import rehearse


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    destination = rehearse.workspace_path(args.output)
    rehearse.require(destination.is_relative_to(Path('gathering').resolve())
                     and not destination.exists(), 'new gathering output required')
    bundle = code_targets.calls.ancestry.read_json(args.bundle)
    proved = code_targets.inspect(bundle)
    target = proved['target']
    rehearse.require(target in rehearse.TOKENS.values(), 'real ZTO or IMD required')
    expected = proved['code_block']
    number = int(expected['number'], 16)
    rpc = rehearse.RPC(rehearse.ENDPOINTS[0])
    rehearse.require(rpc.call('eth_chainId', []) == '0x1', 'wrong chain')
    block = rehearse.header(rpc.call('eth_getBlockByNumber', [hex(number), False]))
    rehearse.require(int(block['number'], 16) == number, 'wrong decimal block')
    rehearse.require(block['hash'] == expected['hash'], 'proof block hash mismatch')
    pin = {'blockHash': block['hash'], 'requireCanonical': True}
    code = rehearse.data(rpc.call('eth_getCode', [target, pin]))
    expected_code = next(node['code'] for node in bundle['observation']['nodes']
                         if node['address'].lower() == target)
    rehearse.require(code == expected_code.lower() and code != '0x', 'runtime mismatch')
    call = {'to': target, 'data': '0x18160ddd', 'value': '0x0'}
    raw = rehearse.data(rpc.call('eth_call', [call, pin]), 32)
    after = rehearse.header(rpc.call('eth_getBlockByNumber', [hex(number), False]))
    rehearse.require(after == block, 'header changed during capture')
    observation = {'schema': rehearse.SCHEMA, 'source': rpc.endpoint,
                   'chain_id': 1, 'block': block, 'call': call, 'returns': 'uint256',
                   'code_present': True, 'outcome': {'result': raw}}
    report = rehearse.report(observation)
    report['limits'] = ('Read-only historical RPC capture at the supplied proof block; '
                        'runtime bytes and decimal block number matched. The header '
                        'is not independently authenticated and finality was not measured. '
                        'The RPC return is unproved; nothing was signed or sent.')
    destination.write_text(json.dumps(observation, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError, rehearse.RPCError) as error:
        print(json.dumps({'status': 'capture-failed', 'error': str(error)}))
        sys.exit(1)
