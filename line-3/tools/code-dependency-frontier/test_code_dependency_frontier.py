"""Focused checks of real proof replay and bounded frontier assembly."""
import copy
import sys
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import code_dependency_frontier as tool


def bundle(name):
    return tool.read_json(HERE.parent / name)


class FrontierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.zto = bundle('code-routes/zto-proof.json')
        cls.imd = bundle('code-routes/imd-proof.json')
        cls.target = bundle('code-target-proofs/imd-target-proof.json')

    def test_real_zto_then_imd_expansion(self):
        zto = tool.evaluate(self.zto, [])
        imd = tool.evaluate(self.imd, [self.target])
        self.assertEqual(zto['decision'], 'no-open-sites-in-bounded-scan')
        self.assertEqual(imd['proved_runtime_count'], 2)
        self.assertEqual(imd['constant_edge_count'], 1)
        self.assertEqual(imd['constant_edges'][0]['status'], 'proved-runtime')
        self.assertEqual(imd['unresolved_call_site_count'], 34)
        self.assertEqual([node['unresolved_call_site_count']
                          for node in imd['runtimes']], [23, 11])
        self.assertFalse(imd['dependency_completeness_verified'])

    def test_missing_proof_stays_visible(self):
        report = tool.evaluate(self.imd, [])
        self.assertEqual(report['decision'], 'open-frontier')
        self.assertEqual(report['missing_constant_targets'],
                         [self.target['observation']['target']])
        self.assertEqual(report['unresolved_call_site_count'], 11)

    def test_unrelated_and_duplicate_proofs_refused(self):
        with self.assertRaisesRegex(ValueError, 'unrelated'):
            tool.evaluate(self.imd, [self.zto])
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            tool.evaluate(self.imd, [self.target, self.target])

    def test_different_block_refused(self):
        older = bundle('code-proof/imd-proof.json')
        with self.assertRaisesRegex(ValueError, 'same block'):
            tool.evaluate(older, [self.target])

    def test_corrupted_target_runtime_refused(self):
        tampered = copy.deepcopy(self.target)
        code = tampered['observation']['nodes'][0]['code']
        tampered['observation']['nodes'][0]['code'] = code[:-1] + ('0' if code[-1] != '0' else '1')
        with self.assertRaises(ValueError):
            tool.evaluate(self.imd, [tampered])

    def test_separate_anchor_equality_does_not_authenticate(self):
        block_hash = self.imd['observation']['block']['hash']
        report = tool.evaluate(self.imd, [self.target], block_hash)
        self.assertFalse(report['anchor_authenticity_verified'])
        with self.assertRaises(ValueError):
            tool.evaluate(self.imd, [self.target], '0x' + '00' * 32)

    def test_two_hop_cycle_and_input_order(self):
        def runtime(address, targets):
            groups = [{'address': target, 'call_site_count': 1,
                       'opcodes': ['CALL'], 'sites': [{'pc': pc, 'opcode': 'CALL'}]}
                      for pc, target in enumerate(targets)]
            return {'address': address, 'code_hash': '0x' + address[-2:] * 32,
                    'runtime_bytes': 3, 'call_instruction_count': len(targets),
                    'locally_constant_target_count': len(targets),
                    'unresolved_target_count': 0,
                    'constant_targets': groups, 'unresolved_sites': [],
                    'recognized_solidity_metadata': None}
        def inventory(address, destinations):
            return {'target': address, 'chain_id': 1,
                    'code_block': {'number': '0x1', 'hash': '0x' + 'ab' * 32},
                    'proof': {'state_inclusion_verified': True},
                    'runtimes': [runtime(address, destinations)]}
        a, b, c = ('0x' + digit * 40 for digit in 'abc')
        source = inventory(a, [b])
        second = inventory(b, [c])
        third = inventory(c, [a])
        result = tool.assemble(source, [third, second])
        self.assertEqual(result['proved_runtime_count'], 3)
        self.assertEqual(result['decision'], 'no-open-sites-in-bounded-scan')
        self.assertEqual(len(result['constant_edges']), 3)
        with self.assertRaisesRegex(ValueError, 'unrelated'):
            tool.assemble(source, [third])


if __name__ == '__main__':
    unittest.main()
