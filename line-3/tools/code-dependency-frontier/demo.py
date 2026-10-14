"""Replay the saved real ZTO and IMD proofs, ZTO first, without networking."""
import json
from pathlib import Path
import code_dependency_frontier as tool

HERE = Path(__file__).resolve().parent


def main():
    zto = tool.evaluate(tool.read_json(HERE.parent / 'code-routes/zto-proof.json'), [])
    imd = tool.evaluate(
        tool.read_json(HERE.parent / 'code-routes/imd-proof.json'),
        [tool.read_json(HERE.parent / 'code-target-proofs/imd-target-proof.json')])
    passed = (zto['decision'] == 'no-open-sites-in-bounded-scan'
              and zto['proved_runtime_count'] == 1
              and zto['unresolved_call_site_count'] == 0
              and imd['decision'] == 'open-frontier'
              and imd['proved_runtime_count'] == 2
              and imd['missing_constant_targets'] == []
              and imd['unresolved_call_site_count'] == 34
              and any(row['runtime_bytes'] == 24005 for row in imd['runtimes']))
    return {'demonstration_passed': passed,
            'ZTO': {'decision': zto['decision'],
                    'proved_runtimes': zto['proved_runtime_count'],
                    'unresolved_sites': zto['unresolved_call_site_count']},
            'IMD': {'decision': imd['decision'],
                    'proved_runtimes': imd['proved_runtime_count'],
                    'missing_constant_targets': imd['missing_constant_targets'],
                    'unresolved_sites': imd['unresolved_call_site_count']},
            'note': 'Historical proof replay only. No independent anchor or complete dependency claim.'}


if __name__ == '__main__':
    report = main()
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report['demonstration_passed'] else 1)
