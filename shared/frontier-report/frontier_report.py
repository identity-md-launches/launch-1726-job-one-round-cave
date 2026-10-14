#!/usr/bin/env python3
"""Present a proof-backed call together with its bounded code dependency frontier."""
import argparse
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dependency_frontier as frontier
sys.path.insert(0, str(HERE.parent / 'rehearsal-report'))
import proof_report

SCHEMA = 'dependency-backed-call-report-v1'
EXIT = {'ready-to-review-bounded-scan': 0, 'call-context-withheld': 2,
        'review-with-open-frontier': 3}


def evaluate(bundle, observation, signature, return_types, target_bundles=None,
             anchor_hash=None):
    """Reverify raw proofs and call context; never hide an unresolved call site."""
    if target_bundles is None:
        target_bundles = []
    # Both components receive the SAME raw source proof and anchor choice.
    dependency = frontier.evaluate(bundle, target_bundles, anchor_hash)
    call = proof_report.report(bundle, observation, signature, return_types, anchor_hash)
    frontier.require(dependency['source_target'] == bundle['observation']['target'].lower(),
                     'dependency source differs from proof root')
    frontier.require(dependency['code_block']['number'] == bundle['observation']['block']['number']
                     and dependency['code_block']['hash'] == bundle['observation']['block']['hash'].lower(),
                     'dependency block differs from proof source')
    aligned = call['status'] == 'ready-to-review'
    open_frontier = dependency['decision'] == 'open-frontier'
    status = ('call-context-withheld' if not aligned else
              'review-with-open-frontier' if open_frontier else
              'ready-to-review-bounded-scan')
    return {
        'schema': SCHEMA, 'status': status,
        'call_context_aligned': aligned, 'dependency_frontier_open': open_frontier,
        'call': dict(observation['call']),
        'call_report': call, 'dependency_frontier': dependency,
        'input_sha256': {
            **call['input_sha256'],
            'target_proofs': sorted(proof_report.surface_call.context.digest(item)
                                    for item in target_bundles),
        },
        'complete_dependencies_verified': False,
        'transaction_approved': False,
        'limits': 'The frontier is a structural scan of supplied proved runtimes, not '
                  'call-specific execution or reachability. Open sites might be irrelevant '
                  'to this call; no-open-sites does not establish complete dependencies. '
                  'Proof inclusion is relative to an unauthenticated supplied header. '
                  'Call returns and reviewer ABI choices remain unproved. No freshness, '
                  'permission, economic safety, state effects or future execution is established.',
    }


def demo_inputs():
    surface = proof_report.SURFACE
    return (frontier.read_json(surface / 'zto-proof.json'),
            proof_report.surface_call.calldata.load(surface / 'zto-call.json'))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--demo', action='store_true')
    parser.add_argument('--bundle')
    parser.add_argument('--observation')
    parser.add_argument('--signature')
    parser.add_argument('--types', help='explicit comma-separated flat return ABI types')
    parser.add_argument('--target-proof', action='append', default=[])
    parser.add_argument('--anchor-hash')
    args = parser.parse_args(argv)
    try:
        explicit = [args.bundle, args.observation, args.signature, args.types]
        frontier.require((args.demo and not any(explicit) and not args.target_proof
                          and not args.anchor_hash) or (not args.demo and all(explicit)),
                         'choose --demo alone or all four explicit inputs')
        frontier.require(len(args.target_proof) <= 16, 'at most 16 target proofs')
        if args.demo:
            bundle, observation = demo_inputs()
            signature, types = 'totalSupply()', ['uint256']
        else:
            bundle = frontier.read_json(args.bundle)
            observation = proof_report.surface_call.calldata.load(args.observation)
            signature, types = args.signature, args.types.split(',')
        targets = [frontier.read_json(path) for path in args.target_proof]
        result = evaluate(bundle, observation, signature, types, targets, args.anchor_hash)
        print(json.dumps(result, indent=2, allow_nan=False))
        return EXIT[result['status']]
    except (ValueError, KeyError, TypeError, OSError, OverflowError, AttributeError,
            IndexError, RecursionError) as error:
        print(json.dumps({'schema': SCHEMA, 'status': 'invalid', 'error': str(error)}),
              file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
