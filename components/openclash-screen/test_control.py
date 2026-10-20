import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('control', Path(__file__).with_name('control.py'))
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)


def api_rules(rules):
    result = []
    for line in rules:
        parts = line.split(',')
        result.append({'type': {'GEOSITE': 'GeoSite', 'GEOIP': 'GeoIP', 'MATCH': 'Match'}.get(parts[0], parts[0]),
                       'payload': parts[1] if parts[0] != 'MATCH' else '',
                       'proxy': parts[2] if parts[0] != 'MATCH' else parts[1]})
    return result


class FakeController:
    def __init__(self, fail_apply=False):
        self.mode = 'rule'
        self.rules = api_rules(c.rules_for('mainland'))
        self.global_selection = 'DIRECT'
        self.fail_apply = fail_apply
        self.applies = 0

    def snapshot(self):
        return {'mode': self.mode}, self.rules, {'now': 'test-node'}

    def api(self, path, method='GET', value=None):
        if path == '/proxies/GLOBAL':
            if method == 'PUT': self.global_selection = value['name']
            return {'now': self.global_selection}
        if path == '/configs?force=true':
            self.applies += 1
            if value['payload'] == 'runtime-original':
                self.mode = 'rule'; self.rules = api_rules(c.rules_for('mainland'))
            else:
                self.mode = 'global'; self.rules = api_rules(c.rules_for('global'))
                self.global_selection = 'PROXY'
            if self.fail_apply and self.applies == 1:
                raise TimeoutError('reply lost after applying')
            return {}
        raise AssertionError(path)

    verify = c.Controller.verify


class ModeTests(unittest.TestCase):
    def test_four_modes_have_distinct_actual_semantics(self):
        for mode in c.MODES:
            self.assertEqual(c.classify({'mode': c.core_mode(mode)}, api_rules(c.rules_for(mode))), mode)
        self.assertNotEqual(c.rules_for('gfw'), c.rules_for('mainland'))

    def test_unknown_rule_mode_is_not_called_mainland(self):
        self.assertEqual(c.classify({'mode': 'rule'}, api_rules(['MATCH,DIRECT'])), 'custom')
        self.assertEqual(c.classify({'mode': 'rule'}, []), 'custom')

    def test_reject_invalid_mode(self):
        for mode in ('gfw; reboot', '../global', '', 'rule', None):
            self.assertRaises(ValueError, c.rules_for, mode)
            self.assertFalse(c.request(mode)['ok'])

    def test_global_requires_proxy_group(self):
        ctl = FakeController(); ctl.mode = 'global'
        self.assertRaises(RuntimeError, ctl.verify, 'global')
        ctl.global_selection = 'PROXY'
        self.assertEqual(ctl.verify('global')['now'], 'test-node')

    def exercise(self, fail_apply=False, fail_commit=False):
        with tempfile.TemporaryDirectory() as temp:
            d = Path(temp); source = d / 'source'; runtime = d / 'runtime'
            initial = json.dumps({'mode': 'rule', 'rules': c.rules_for('mainland'),
                                 'proxies': [{'name': 'test-node', 'password': 'private-test'}],
                                 'proxy-groups': [{'name': 'PROXY', 'proxies': ['test-node']}]}).encode()
            source.write_bytes(initial); runtime.write_bytes(b'runtime-original')
            values = {'config_path': str(source), 'enable': '1', 'proxy_mode': 'rule'}
            commits = 0
            def command(argv, **kw):
                nonlocal commits
                if argv[:2] == ['uci', 'set']:
                    values['proxy_mode'] = argv[2].split('=', 1)[1]
                if argv[:2] == ['uci', 'commit']:
                    commits += 1
                    if fail_commit and commits == 1: raise OSError('simulated persistence failure')
                return b''
            ctl = FakeController(fail_apply)
            with patch.object(c, 'SOURCE', source), patch.object(c, 'RUNTIME', runtime), \
                 patch.object(c, 'uci', lambda n: values[n]), patch.object(c, 'command', command), \
                 patch.object(c, 'validation_env', lambda: {}), \
                 patch.object(c, 'render_runtime', lambda b, t: b'runtime-global'):
                if fail_apply or fail_commit:
                    self.assertRaises(Exception, c.apply_mode, 'global', ctl, d / 'backup')
                    self.assertEqual(source.read_bytes(), initial)
                    self.assertEqual(runtime.read_bytes(), b'runtime-original')
                    self.assertEqual(values['proxy_mode'], 'rule')
                    self.assertEqual(c.classify(*ctl.snapshot()[:2]), 'mainland')
                    self.assertEqual(ctl.global_selection, 'DIRECT')
                    self.assertTrue(json.loads((d / 'backup/result.json').read_bytes())['rolled_back'])
                else:
                    self.assertTrue(c.apply_mode('global', ctl, d / 'backup')['ok'])
                    saved = json.loads(source.read_bytes())
                    self.assertEqual(saved['proxies'], json.loads(initial)['proxies'])
                    self.assertEqual(saved['proxy-groups'][-1]['proxies'], ['PROXY'])
                    self.assertEqual(values['proxy_mode'], 'global')
                    self.assertEqual(runtime.read_bytes(), b'runtime-global')
                self.assertEqual((d / 'backup/source.before').stat().st_mode & 0o777, 0o600)

    def test_success_preserves_nodes_and_persists_mode(self): self.exercise()
    def test_reply_timeout_restores_files_core_rules_and_global_selection(self): self.exercise(fail_apply=True)
    def test_persistence_failure_rolls_back(self): self.exercise(fail_commit=True)

    def test_real_yaml_transform_preserves_auth_and_ports(self):
        runtime = b'''mode: rule
secret: private-test
mixed-port: 7893
authentication: ['test:private']
proxies: [{name: node, type: direct}]
proxy-groups: [{name: PROXY, type: select, proxies: [node]}]
rules: ['MATCH,PROXY']
'''
        new = c.render_runtime(runtime, 'gfw')
        self.assertIn(b'private-test', new)
        self.assertIn(b'7893', new)
        self.assertIn(b'GEOSITE,gfw,PROXY', new)
        self.assertIn(b'GLOBAL', new)


if __name__ == '__main__':
    unittest.main(verbosity=2)
