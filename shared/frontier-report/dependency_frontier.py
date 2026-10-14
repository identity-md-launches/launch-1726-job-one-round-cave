#!/usr/bin/env python3
"""Expand same-block, proof-backed constant call targets and expose the open frontier."""
import argparse
import json
from pathlib import Path
import sys

# Promoted from Line 3; reuse its committed proof/scanner dependencies unchanged.
TOOLS = Path(__file__).resolve().parents[2] / "line-3" / "tools"
sys.path.insert(0, str(TOOLS / 'code-targets'))
import code_targets as targets

require = targets.calls.lens.require
read_json = targets.calls.ancestry.read_json


def assemble(source, additional):
    """Assemble only already-verified Code Targets inventories; never infer execution."""
    require(isinstance(additional, list) and len(additional) <= 16,
            'at most 16 additional proof bundles')
    require(source['chain_id'] == 1 and source['proof']['state_inclusion_verified'],
            'source state proof is not verified')
    block = source['code_block']
    root = source['target']
    inventories = {root: source}
    for item in additional:
        require(item['chain_id'] == 1 and item['proof']['state_inclusion_verified'],
                'target state proof is not verified')
        require(item['code_block'] == block,
                'every proof must have the same block number and hash')
        target = item['target']
        require(target not in inventories, 'duplicate proof root')
        inventories[target] = item

    # A proof may expand the scan only if a prior reached runtime contains its
    # address as a locally constant call operand. Input order is immaterial.
    reached = {root}
    while True:
        discovered = {group['address']
                      for address in reached
                      for runtime in inventories[address]['runtimes']
                      for group in runtime['constant_targets']}
        expanded = reached | (discovered & inventories.keys())
        if expanded == reached:
            break
        reached = expanded
    require(reached == inventories.keys(), 'unrelated target proof root')

    nodes = {}
    for bundle_root in sorted(reached):
        for runtime in inventories[bundle_root]['runtimes']:
            address = runtime['address']
            if address in nodes:
                old = nodes[address]
                require(old['code_hash'] == runtime['code_hash']
                        and old['runtime_bytes'] == runtime['runtime_bytes']
                        and old['call_instruction_count'] == runtime['call_instruction_count']
                        and old['constant_targets'] == runtime['constant_targets']
                        and old['unresolved_sites'] == runtime['unresolved_sites'],
                        'conflicting same-block runtime evidence')
            else:
                nodes[address] = runtime

    edges = []
    unresolved = []
    for caller, runtime in sorted(nodes.items()):
        for group in runtime['constant_targets']:
            address = group['address']
            target = nodes.get(address)
            status = ('missing-proof' if target is None else
                      'proved-empty-account' if target['runtime_bytes'] == 0 else
                      'proved-runtime')
            edges.append({'caller': caller, 'target': address, 'status': status,
                          'call_site_count': group['call_site_count'],
                          'opcodes': group['opcodes'], 'sites': group['sites']})
        if runtime['unresolved_sites']:
            unresolved.append({'caller': caller, 'sites': runtime['unresolved_sites']})
    edges.sort(key=lambda edge: (edge['caller'], edge['target']))
    missing = sorted({edge['target'] for edge in edges
                      if edge['status'] == 'missing-proof'})
    unresolved_count = sum(len(item['sites']) for item in unresolved)
    node_rows = [{'address': address, 'code_hash': runtime['code_hash'],
                  'runtime_bytes': runtime['runtime_bytes'],
                  'call_instruction_count': runtime['call_instruction_count'],
                  'constant_call_site_count': runtime['locally_constant_target_count'],
                  'unresolved_call_site_count': runtime['unresolved_target_count'],
                  'recognized_solidity_metadata': runtime['recognized_solidity_metadata']}
                 for address, runtime in sorted(nodes.items())]
    require(sum(node['call_instruction_count'] for node in node_rows)
            == sum(edge['call_site_count'] for edge in edges) + unresolved_count,
            'incomplete call-site accounting')
    return {
        'schema': 'code-dependency-frontier-v1', 'chain_id': 1,
        'source_target': root, 'code_block': block,
        'decision': ('open-frontier' if missing or unresolved_count else
                     'no-open-sites-in-bounded-scan'),
        'proof_bundle_roots': sorted(reached),
        'proved_runtime_count': len(nodes),
        'constant_edge_count': len(edges),
        'missing_constant_targets': missing,
        'unresolved_call_site_count': unresolved_count,
        'runtimes': node_rows, 'constant_edges': edges,
        'unresolved_calls': unresolved,
        'raw_proofs_reverified': True,
        'anchor_authenticity_verified': False,
        'reachability_verified': False,
        'dependency_completeness_verified': False,
        'semantic_safety_verified': False,
        'scope': 'Same-block raw state/header/runtime proof replay, followed by bounded '
                 'structural scanning of every proved source or discovered-target runtime. '
                 'Only locally constant decoded external-call operands can request more '
                 'proofs; unresolved operands remain open. Structural sites can be '
                 'unreachable or metadata. This is not EVM execution, complete '
                 'dependency discovery, authenticated consensus, source equivalence, '
                 'current-state proof, safety review or transaction approval.'
    }


def evaluate(source_bundle, target_bundles, anchor_hash=None):
    require(isinstance(target_bundles, list) and len(target_bundles) <= 16,
            'at most 16 additional proof bundles')
    source = targets.inspect(source_bundle, anchor_hash)
    additional = [targets.inspect(bundle, anchor_hash) for bundle in target_bundles]
    return assemble(source, additional)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, help='workspace-local raw Code Proof JSON')
    parser.add_argument('--target-proof', action='append', default=[])
    parser.add_argument('--anchor-hash')
    args = parser.parse_args()
    try:
        require(len(args.target_proof) <= 16, 'too many target proofs')
        result = evaluate(read_json(args.source),
                          [read_json(path) for path in args.target_proof],
                          args.anchor_hash)
        print(json.dumps(result, indent=2))
        return 3 if result['decision'] == 'open-frontier' else 0
    except (ValueError, KeyError, TypeError, OSError, OverflowError, AttributeError,
            IndexError, RecursionError) as error:
        print('Code Dependency Frontier: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
