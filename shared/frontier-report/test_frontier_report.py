"""Exercise real replay and refusal paths of the dependency/call evidence join."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import frontier_report as tool


class FrontierReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.zto, cls.zto_call = tool.demo_inputs()
        cls.imd = tool.frontier.read_json('line-3/tools/code-routes/imd-proof.json')
        cls.target = tool.frontier.read_json('line-3/tools/code-target-proofs/imd-target-proof.json')
        cls.imd_call = tool.proof_report.surface_call.calldata.load(HERE / 'imd-call.json')

    def evaluate(self, bundle=None, call=None, targets=None, signature='totalSupply()'):
        return tool.evaluate(bundle or self.zto, call or self.zto_call,
                             signature, ['uint256'], targets)

    def test_real_zto_bounded_review(self):
        r = self.evaluate()
        self.assertEqual(r['status'], 'ready-to-review-bounded-scan')
        self.assertEqual(r['call_report']['decoded_values'][0]['value'],
                         '1000000000000000000000000000')
        self.assertFalse(r['complete_dependencies_verified'])
        self.assertFalse(r['transaction_approved'])

    def test_real_imd_valid_call_keeps_open_frontier(self):
        r = self.evaluate(self.imd, self.imd_call, [self.target])
        self.assertTrue(r['call_context_aligned'])
        self.assertEqual(r['status'], 'review-with-open-frontier')
        self.assertEqual(r['dependency_frontier']['unresolved_call_site_count'], 34)
        self.assertEqual(r['call_report']['decoded_values'][0]['value'],
                         '4174192949067000000000000')
        self.assertEqual(len(r['input_sha256']['target_proofs']), 1)

    def test_missing_constant_proof_remains_visible(self):
        r = self.evaluate(self.imd, self.imd_call, [])
        f = r['dependency_frontier']
        self.assertEqual(r['status'], 'review-with-open-frontier')
        self.assertEqual(f['unresolved_call_site_count'], 11)
        self.assertEqual(f['missing_constant_targets'], [self.target['observation']['target']])

    def test_wrong_call_block_withholds_all_values(self):
        changed = copy.deepcopy(self.zto_call)
        changed['block']['hash'] = self.imd_call['block']['hash']
        r = self.evaluate(call=changed)
        self.assertEqual(r['status'], 'call-context-withheld')
        self.assertIsNone(r['call_report']['decoded_values'])
        self.assertIsNone(r['call_report']['return_bytes'])

    def test_target_or_selector_mismatch_withholds(self):
        r = self.evaluate(self.zto, self.imd_call)
        self.assertFalse(r['call_context_aligned'])
        r = self.evaluate(signature='balanceOf(address)')
        self.assertFalse(r['call_context_aligned'])

    def test_malformed_return_refused(self):
        changed = copy.deepcopy(self.zto_call)
        changed['outcome']['result'] = 'not-hex-return-bytes'
        with self.assertRaises(ValueError):
            self.evaluate(call=changed)

    def test_unrelated_duplicate_and_old_proofs_refused(self):
        old = tool.frontier.read_json('line-3/tools/code-proof/imd-proof.json')
        for source, additions in ((self.imd, [self.zto]),
                                  (self.imd, [self.target, self.target]),
                                  (old, [self.target])):
            with self.subTest(additions=len(additions)), self.assertRaises(ValueError):
                self.evaluate(source, self.imd_call, additions)

    def test_corrupted_proof_refused(self):
        changed = copy.deepcopy(self.target)
        changed['header_rlp'] = '0x80'
        with self.assertRaises(ValueError):
            self.evaluate(self.imd, self.imd_call, [changed])

    def test_anchor_is_equality_only(self):
        anchor = self.imd['observation']['block']['hash']
        r = tool.evaluate(self.imd, self.imd_call, 'totalSupply()', ['uint256'],
                          [self.target], anchor)
        self.assertFalse(r['dependency_frontier']['anchor_authenticity_verified'])
        with self.assertRaises(ValueError):
            tool.evaluate(self.imd, self.imd_call, 'totalSupply()', ['uint256'],
                          [self.target], self.zto['observation']['block']['hash'])

    def test_cli_exits_and_no_network_demo(self):
        prefix = [sys.executable, '-B', str(HERE / 'frontier_report.py')]
        cases = [(['--demo'], 0), (['--demo', '--types', 'uint256'], 1),
                 (['--bundle', 'line-3/tools/code-routes/imd-proof.json',
                   '--observation', str(HERE / 'imd-call.json'),
                   '--signature', 'totalSupply()', '--types', 'uint256'], 3),
                 (['--bundle', 'line-3/tools/code-routes/imd-proof.json',
                   '--observation', str(HERE / 'imd-call.json'),
                   '--signature', 'balanceOf(address)', '--types', 'uint256'], 2),
                 (['--bundle', '../outside.json', '--observation', str(HERE / 'imd-call.json'),
                   '--signature', 'totalSupply()', '--types', 'uint256'], 1)]
        for args, expected in cases:
            done = subprocess.run(prefix + args, capture_output=True, text=True, timeout=20)
            with self.subTest(args=args):
                self.assertEqual(done.returncode, expected, done.stderr)
                result = json.loads(done.stderr if expected == 1 else done.stdout)
                self.assertIn('status', result)


if __name__ == '__main__':
    unittest.main()
