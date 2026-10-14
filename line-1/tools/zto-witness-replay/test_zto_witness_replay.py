import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

import zto_witness_replay as replay


class ReplayTests(unittest.TestCase):
    def setUp(self):
        self.a, self.ca = copy.deepcopy(replay.demo_inputs())
        self.b, self.cb = copy.deepcopy((self.a, self.ca))
        # Explicit simulated second label, never a claimed second real capture.
        self.b['base']['source'] = self.cb['source'] = 'https://second.example/rpc'
        self.controls = ['ZTO', '1', 100, self.a['base']['block']['hash'],
                         int(self.a['base']['block']['number'], 16), 0]

    def run_replay(self):
        return replay.replay(self.a, self.b, self.ca, self.cb, *self.controls)

    def rebuild_check(self, observation, check):
        token, amount = self.controls[:2]
        quote = replay.path.quote(observation, token, amount)
        row = check['results'][0]
        output = quote.get('estimate', quote.get('partial'))['output_raw']
        row.update(input_token=token, amount=amount,
                   request=replay.expected_request(observation, token, amount),
                   raw_result='0x' + (replay.path.z.word(int(output)) + replay.path.z.word(0)).hex(),
                   local_output_raw=output, initialized_ticks_crossed=quote['initialized_ticks_crossed'],
                   matches=True)

    def test_demo_real_single_source_offline(self):
        with patch('socket.socket', side_effect=AssertionError('network forbidden')):
            result = replay.demo()
        self.assertEqual(result['reasons'], ['same_source_label'])
        self.assertEqual(result['raw_quoter_matches'], [True, True])
        self.assertIsNone(result['bound'])

    def test_simulated_two_label_floor_release(self):
        result = self.run_replay()
        self.assertTrue(result['bound_released'])
        self.assertEqual(result['bound']['planning_minimum_raw'], '15139234039518')

    def test_zero_rounded_minimum_withheld(self):
        self.controls[1] = '0.0000000000001'
        for observation, check in ((self.a, self.ca), (self.b, self.cb)):
            self.rebuild_check(observation, check)
        result = self.run_replay()
        self.assertEqual(result['reasons'], ['planning_minimum_rounds_to_zero'])
        self.assertFalse(result['bound_released'])
        self.assertIsNone(result['bound'])

    def test_zero_output_withheld(self):
        self.controls[1] = '0.000000000000000001'
        for observation, check in ((self.a, self.ca), (self.b, self.cb)):
            self.rebuild_check(observation, check)
        self.assertFalse(self.run_replay()['bound_released'])

    def test_wrong_calldata_refused(self):
        original = self.ca['results'][0]['request']['data']
        # Every ABI component: selector, tuple offset, currencies, fee, spacing,
        # hook, direction, amount, bytes offset and bytes length.
        for start in [2] + [10 + i * 64 for i in range(10)]:
            with self.subTest(start=start):
                data = original[:start] + ('f' if original[start] != 'f' else 'e') + original[start+1:]
                self.ca['results'][0]['request']['data'] = data
                with self.assertRaisesRegex(ValueError, 'quoter request'):
                    self.run_replay()
        self.ca['results'][0]['request']['data'] = original

    def test_transaction_fields_refused(self):
        self.ca['results'][0]['request']['value'] = '0x0'
        with self.assertRaisesRegex(ValueError, 'quoter request'):
            self.run_replay()

    def test_wrong_to_quoter_source_and_block_refused(self):
        mutations = [('quoter', replay.path.z.MANAGER), ('source', self.b['base']['source']),
                     ('block', dict(self.ca['block'], timestamp='0x1'))]
        for key, value in mutations:
            with self.subTest(key=key):
                old = self.ca[key]
                self.ca[key] = value
                with self.assertRaises(ValueError):
                    self.run_replay()
                self.ca[key] = old
        self.ca['results'][0]['request']['to'] = replay.path.z.MANAGER
        with self.assertRaises(ValueError):
            self.run_replay()

    def test_wrong_block_anchor_withheld(self):
        self.controls[3] = self.a['base']['initialize']['blockHash']
        self.assertIn('caller_block_anchor_mismatch', self.run_replay()['reasons'])

    def test_age_boundaries(self):
        self.controls[4] += 10
        self.controls[5] = 10
        self.assertTrue(self.run_replay()['bound_released'])
        self.controls[5] = 9
        self.assertIn('outside_caller_age_limit', self.run_replay()['reasons'])
        self.controls[4] -= 11
        self.assertIn('outside_caller_age_limit', self.run_replay()['reasons'])

    def test_changed_pool_state_withheld(self):
        raw = self.b['base']['raw']['liquidity']
        self.b['base']['raw']['liquidity'] = '0x' + replay.path.z.word(int(raw, 16)+1).hex()
        self.rebuild_check(self.b, self.cb)
        self.assertIn('different_block_state_or_coverage', self.run_replay()['reasons'])

    def test_different_block_withheld(self):
        self.b['base']['block']['hash'] = self.a['base']['initialize']['blockHash']
        self.cb['block'] = copy.deepcopy(self.b['base']['block'])
        result = self.run_replay()
        self.assertIn('different_block_state_or_coverage', result['reasons'])
        self.assertFalse(result['bound_released'])

    def test_raw_return_mismatch_withheld_and_false_claim_refused(self):
        row = self.ca['results'][0]
        output, gas = replay.path.z.words(row['raw_result'], 2)
        row['raw_result'] = '0x' + (replay.path.z.word(output+1) + replay.path.z.word(gas)).hex()
        with self.assertRaisesRegex(ValueError, 'match flags'):
            self.run_replay()
        self.ca['all_match'] = row['matches'] = False
        self.assertIn('quoter_does_not_match_complete_local_fill', self.run_replay()['reasons'])

    def test_malformed_raw_return_refused(self):
        for raw in ('not-hex', '0x', self.ca['results'][0]['raw_result'] + '00'):
            self.ca['results'][0]['raw_result'] = raw
            with self.assertRaises(ValueError):
                self.run_replay()

    def test_claimed_local_output_and_tick_count_refused(self):
        row = self.ca['results'][0]
        output = row['local_output_raw']
        row['local_output_raw'] = str(int(output)+1)
        with self.assertRaisesRegex(ValueError, 'local output'):
            self.run_replay()
        row['local_output_raw'] = output
        row['initialized_ticks_crossed'] = True
        with self.assertRaisesRegex(ValueError, 'crossed-tick'):
            self.run_replay()

    def test_extra_or_multiple_results_refused(self):
        self.ca['results'].append(copy.deepcopy(self.ca['results'][0]))
        with self.assertRaises(ValueError):
            self.run_replay()
        self.ca['results'].pop()
        self.ca['bound_released'] = True
        with self.assertRaises(ValueError):
            self.run_replay()

    def test_bool_numeric_controls_refused(self):
        for index in (2, 4, 5):
            old = self.controls[index]
            self.controls[index] = True
            with self.assertRaises(ValueError):
                self.run_replay()
            self.controls[index] = old

    def test_reverse_direction_simulation(self):
        self.controls[0] = 'IMD'
        for observation, check in ((self.a, self.ca), (self.b, self.cb)):
            self.rebuild_check(observation, check)
        result = self.run_replay()
        self.assertTrue(result['bound_released'])
        self.assertEqual(result['output_token'], 'ZTO')

    def test_partial_fill_never_releases(self):
        self.controls[1] = '1000000000'
        for observation, check in ((self.a, self.ca), (self.b, self.cb)):
            self.rebuild_check(observation, check)
        result = self.run_replay()
        self.assertIn('incomplete_local_fill', result['reasons'])
        self.assertIsNone(result['bound'])

    def test_strict_json_and_workspace_boundary(self):
        with self.assertRaises(ValueError):
            replay.pairs([('x', 1), ('x', 2)])
        for text in ('{"x":1.0}', '{"x":NaN}', '{"x":Infinity}'):
            with self.assertRaises(ValueError):
                json.loads(text, parse_float=replay.unsupported_number,
                           parse_constant=replay.unsupported_number)
        with self.assertRaisesRegex(ValueError, 'workspace'):
            replay.read_json('/tmp/not-workspace.json')

    def test_cli_demo_and_conflicting_controls(self):
        script = str(Path(replay.__file__).resolve())
        result = subprocess.run([sys.executable, '-B', script, '--demo'],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(json.loads(result.stdout)['bound_released'])
        result = subprocess.run([sys.executable, '-B', script, '--demo', '--amount', '1'],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)


if __name__ == '__main__':
    unittest.main()
