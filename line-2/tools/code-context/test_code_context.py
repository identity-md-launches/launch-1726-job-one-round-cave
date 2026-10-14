import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import code_context as context


class ContextTests(unittest.TestCase):
    def setUp(self):
        self.observation, self.runtime = context.demo_inputs()

    def check(self):
        return context.check(self.observation, self.runtime)

    def test_real_zto_context(self):
        result = self.check()
        self.assertTrue(result['context_matched'])
        self.assertEqual((result['measured_pair_count'], result['active_spender_count'],
                          result['active_pair_count'], result['empty_balance_active_pair_count']),
                         (19, 2, 3, 2))
        self.assertFalse(result['complete_wallet_audit'])

    def test_all_identity_fields_bound(self):
        mutations = {'chain_id': 2, 'token': 'IMD',
                     'token_address': context.gate.lens.TOKENS['IMD'],
                     'block_number': self.runtime['block_number'] + 1,
                     'block_hash': '0x' + 'ab' * 32}
        for field, value in mutations.items():
            with self.subTest(field=field):
                altered = copy.deepcopy(self.runtime)
                altered[field] = value
                if field == 'block_hash':
                    for row in altered['spenders']:
                        row['block_hash'] = value
                with self.assertRaises(ValueError):
                    context.check(self.observation, altered)

    def test_missing_code_keeps_permission(self):
        removed = self.runtime['spenders'].pop()
        result = self.check()
        self.assertFalse(result['context_matched'])
        self.assertEqual(result['missing_active_spenders'], [removed['spender']])
        rows = [row for row in result['pairs'] if row['spender'] == removed['spender']]
        self.assertTrue(any(row['status'] == 'active_permission_code_not_observed' and
                            int(row['allowance_raw']) > 0 for row in rows))

    def test_extra_inactive_code_withholds_context(self):
        measured = context.gate.changes.flatten(self.observation)
        active = {row['spender'] for row in self.runtime['spenders']}
        spender = next(spender for _, spender in measured['pairs'] if spender not in active)
        extra = copy.deepcopy(self.runtime['spenders'][0])
        extra['spender'] = spender
        self.runtime['spenders'].append(extra)
        result = self.check()
        self.assertFalse(result['context_matched'])
        self.assertEqual(result['extra_code_spenders'], [spender])

    def test_empty_code_never_clears_allowance(self):
        row = self.runtime['spenders'][0]
        row.update(runtime_code_bytes=0, runtime_code_sha256=hashlib.sha256(b'').hexdigest(),
                   classification='no_runtime_code_at_block')
        result = self.check()
        self.assertTrue(result['context_matched'])
        active = [pair for pair in result['pairs']
                  if pair['status'] == 'active_permission_without_runtime']
        self.assertTrue(active)
        self.assertTrue(all(int(pair['allowance_raw']) > 0 for pair in active))

    def test_false_empty_hash_refused(self):
        self.runtime['spenders'][0].update(runtime_code_bytes=0,
                                          classification='no_runtime_code_at_block')
        with self.assertRaisesRegex(ValueError, 'empty runtime'):
            self.check()

    def test_forged_counters_and_boolean_chain_refused(self):
        for field in ('measured_pair_count', 'active_spender_count', 'chain_id'):
            with self.subTest(field=field):
                for value in (True, 99):
                    altered = copy.deepcopy(self.runtime)
                    altered[field] = value
                    with self.assertRaises(ValueError):
                        context.check(self.observation, altered)

    def test_duplicate_spender_refused(self):
        self.runtime['spenders'].append(copy.deepcopy(self.runtime['spenders'][0]))
        with self.assertRaisesRegex(ValueError, 'duplicate spender'):
            self.check()

    def test_wrong_row_anchor_refused(self):
        self.runtime['spenders'][0]['block_hash'] = '0x' + 'ab' * 32
        with self.assertRaisesRegex(ValueError, 'pinned'):
            self.check()

    def test_input_digests_bind_raw_evidence(self):
        result = self.check()
        self.runtime['source'] = 'https://eth.drpc.org'
        later = self.check()
        self.assertNotEqual(result['input_sha256']['runtime'], later['input_sha256']['runtime'])
        self.assertEqual(result['input_sha256']['observation'], later['input_sha256']['observation'])

    def test_loader_limits_duplicates_and_workspace(self):
        scratch = Path.cwd() / 'test/scratch'
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as directory:
            path = Path(directory) / 'input.json'
            path.write_text('{"key":1,"key":2}')
            with self.assertRaisesRegex(ValueError, 'duplicate JSON'):
                context.gate.load(path)
            path.write_bytes(b' ' * (context.gate.LIMIT + 1))
            with self.assertRaisesRegex(ValueError, '96 KiB'):
                context.gate.load(path)
        with self.assertRaises(ValueError):
            context.gate.load(Path.cwd().parent / 'outside.json')

    def test_cli_success_missing_input_and_coverage_exit(self):
        command = [sys.executable, '-B', str(context.HERE / 'code_context.py')]
        demo = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(demo.returncode, 0, demo.stderr)
        self.assertEqual(json.loads(demo.stdout)['status'], 'context_matched')
        partial = subprocess.run(command + ['--runtime', 'missing.json'],
                                 capture_output=True, text=True)
        self.assertEqual(partial.returncode, 1)
        scratch = Path.cwd() / 'test/scratch'
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as directory:
            observation, runtime = Path(directory) / 'observation.json', Path(directory) / 'runtime.json'
            observation.write_text(json.dumps(self.observation))
            self.runtime['spenders'].pop()
            runtime.write_text(json.dumps(self.runtime))
            missing = subprocess.run(command + ['--observation', str(observation), '--runtime', str(runtime)],
                                     capture_output=True, text=True)
            self.assertEqual(missing.returncode, 3, missing.stderr)
            self.assertFalse(json.loads(missing.stdout)['context_matched'])


if __name__ == '__main__':
    unittest.main()
