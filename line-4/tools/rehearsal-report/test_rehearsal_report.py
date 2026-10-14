"""Offline adversarial regressions for the repaired summary."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('report_under_test', HERE / 'rehearsal_report.py')
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)
SAVED = HERE.parent / 'return-lens/zto-live-observation.json'


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.value = json.loads(SAVED.read_text())

    def test_real_zto_offline(self):
        with patch.object(report.core.RPC, 'call', side_effect=AssertionError('network forbidden')):
            result = report.report(SAVED)
        self.assertEqual(result['status'], 'ready-to-review')
        self.assertEqual(result['interpretation']['uint256'], str(10**27))
        self.assertNotIn('sender', result)

    def test_malformed_returns(self):
        for raw in ('not-hex-return-bytes', '0x1', '0xgg', None, True, 3, '0x'+'aa'*32769):
            with self.subTest(raw=str(raw)[:30]):
                self.value['outcome'] = {'result': raw}
                with self.assertRaises(ValueError):
                    report.summarize(self.value)

    def test_typed_return_lengths(self):
        for raw in ('0x', '0x01', '0x'+'00'*33):
            self.value['outcome'] = {'result': raw}
            self.assertEqual(report.summarize(self.value)['status'], 'withheld')

    def test_bool_false_true_and_noncanonical(self):
        self.value['returns'] = 'bool'
        for number, expected in ((0, 'withheld'), (1, 'ready-to-review'), (2, 'withheld')):
            self.value['outcome'] = {'result': '0x'+format(number, '064x')}
            self.assertEqual(report.summarize(self.value)['status'], expected)

    def test_raw_empty_has_no_inferred_meaning(self):
        self.value['returns'] = 'raw'; self.value['outcome'] = {'result': '0x'}
        result = report.summarize(self.value)
        self.assertEqual(result['status'], 'ready-to-review')
        self.assertNotIn('uint256', result['interpretation'])

    def test_errors_and_reverts(self):
        for code, message, category in ((3, 'execution reverted', 'revert'),
                                       (-32000, 'archive unavailable', 'rpc-error')):
            self.value['outcome'] = {'error': {'code': code, 'message': message}}
            result = report.summarize(self.value)
            self.assertEqual(result['status'], 'withheld')
            self.assertEqual(result['outcome'], category)
            self.assertIsNone(result['return_bytes'])

    def test_error_payload_must_be_hex(self):
        self.value['outcome'] = {'error': {'code': 3, 'message': 'execution reverted', 'data': 'nonsense'}}
        with self.assertRaises(ValueError): report.summarize(self.value)

    def test_code_flag(self):
        self.value['code_present'] = False
        self.assertEqual(report.summarize(self.value)['status'], 'withheld')
        for bad in (0, 1, None, 'true'):
            self.value['code_present'] = bad
            with self.assertRaises(ValueError): report.summarize(self.value)

    def test_context_mutations(self):
        mutations = [(['chain_id'], True), (['chain_id'], 2), (['source'], 'https://untrusted.invalid'),
                     (['block', 'hash'], '0x11'), (['block', 'number'], '0x01'),
                     (['block', 'timestamp'], 'bad'), (['call', 'to'], 'bad'),
                     (['call', 'data'], '0x1'), (['call', 'value'], '0x00'),
                     (['returns'], 'invented'), (['schema'], 'invented')]
        for keys, bad in mutations:
            value = copy.deepcopy(self.value); obj = value
            for key in keys[:-1]: obj = obj[key]
            obj[keys[-1]] = bad
            with self.subTest(keys=keys), self.assertRaises(ValueError): report.summarize(value)

    def test_unknown_fields_and_ambiguous_outcomes(self):
        for keys in ([], ['block'], ['call'], ['outcome']):
            value = copy.deepcopy(self.value); obj = value
            for key in keys: obj = obj[key]
            obj['surprise'] = 'no'
            with self.assertRaises(ValueError): report.summarize(value)
        for outcome in ({}, {'result':'0x', 'error':{'code':3,'message':'reverted'}}, {'revert':'0x'}):
            self.value['outcome'] = outcome
            with self.assertRaises(ValueError): report.summarize(self.value)

    def test_explicit_sender_preserved(self):
        self.value['call']['from'] = report.core.TOKENS['IMD']
        self.assertEqual(report.summarize(self.value)['sender'], report.core.TOKENS['IMD'])

    def test_relay_provenance_preserved_and_strict(self):
        self.value['transport'] = {'kind':'contributor-relay', 'source_is_attribution_only':True,
                                   'independent_provider_verified':False}
        self.assertEqual(report.summarize(self.value)['transport'], self.value['transport'])
        self.value['transport']['source_is_attribution_only'] = 1
        with self.assertRaises(ValueError): report.summarize(self.value)

    def test_bounded_strict_files(self):
        root = Path('test/scratch'); root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as directory:
            path = Path(directory)/'input.json'
            for text in ('{"schema":1,"schema":2}', '{"n":NaN}', ' '*90001, '[]', '{'):
                path.write_text(text)
                with self.assertRaises(ValueError): report.report(path)
        with self.assertRaises(ValueError): report.report(Path.cwd().parent/'outside.json')

    def test_cli_exit_codes(self):
        root = Path('test/scratch'); root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as directory:
            path = Path(directory)/'input.json'
            for raw, expected in ((self.value['outcome']['result'],0), ('0x',1), ('not-hex-return-bytes',2)):
                self.value['outcome'] = {'result':raw}; path.write_text(json.dumps(self.value))
                result = subprocess.run([sys.executable,'-B',str(HERE/'rehearsal_report.py'),str(path)],
                                        capture_output=True,text=True,timeout=10)
                self.assertEqual(result.returncode,expected,result.stderr)
                parsed = json.loads(result.stdout if expected != 2 else result.stderr)
                self.assertEqual(parsed['status'], {0:'ready-to-review',1:'withheld',2:'invalid'}[expected])


if __name__ == '__main__': unittest.main()
