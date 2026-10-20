import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import urllib.parse

spec = importlib.util.spec_from_file_location('nodes_control', Path(__file__).with_name('control.py'))
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)


class FakeNodes:
    def __init__(self, fail_select=False, failed_delay=False, global_mode=False):
        self.names = ['node-one', "节点 two / ' $(never-executed)"]
        self.selected = self.names[0]
        self.global_selected = 'DIRECT'
        self.mode = 'global' if global_mode else 'rule'
        self.fail_select = fail_select
        self.failed_delay = failed_delay
        self.failed_once = False
        self.calls = []
        self.rules = [{'type': 'Match', 'payload': '', 'proxy': 'PROXY'}]

    def snapshot(self):
        return {'mode': self.mode}, self.rules, self.api('/proxies/PROXY')

    def api(self, path, method='GET', value=None, seconds=6):
        self.calls.append((path, method, value))
        if path == '/proxies/PROXY':
            if method == 'PUT':
                self.selected = value['name']
                if self.fail_select and not self.failed_once:
                    self.failed_once = True
                    raise TimeoutError('lost response after selection')
            return {'now': self.selected, 'type': 'Selector', 'all': self.names + ['DIRECT', 'other-group']}
        if path == '/proxies/GLOBAL':
            if method == 'PUT': self.global_selected = value['name']
            return {'now': self.global_selected}
        if path == '/proxies':
            return {'proxies': {self.names[0]: {'type': 'VLESS'}, self.names[1]: {'type': 'Tuic'},
                                'DIRECT': {'type': 'Direct'}, 'other-group': {'type': 'Selector'}}}
        if '/delay?' in path:
            if self.failed_delay and urllib.parse.quote(self.names[1], safe='') in path:
                raise TimeoutError('test timeout')
            return {'delay': 123}
        raise AssertionError(path)


class NodeTests(unittest.TestCase):
    def source(self, ctl):
        return {'mode': 'rule', 'rules': ['MATCH,PROXY'],
                'profile': {'store-selected': True},
                'proxies': [{'name': n, 'type': 'vless', 'password': 'private-test'} for n in ctl.names],
                'proxy-groups': [{'name': 'PROXY', 'type': 'select', 'proxies': ctl.names}]}

    def test_only_leaf_nodes_exposed_without_credentials(self):
        ctl = FakeNodes(); rows = c.node_choices(ctl)
        self.assertEqual(len(rows), 2)
        self.assertTrue(rows[0]['selected'])
        self.assertFalse(rows[1]['selected'])
        self.assertTrue(all(c.valid_node_id(n['id']) for n in rows))
        self.assertNotIn('password', json.dumps(rows))
        self.assertEqual(set(rows[0]), {'id', 'name', 'type', 'selected'})

    def test_node_identifier_injection_rejected(self):
        for value in ('x; reboot', '../foo', "node'1", 'a'*23, 'A'*24, None):
            self.assertFalse(c.valid_node_id(value))
            self.assertFalse(c.request_action('node', value)['ok'])

    def exercise_select(self, fail_api=False, fail_file=False, global_mode=False):
        ctl = FakeNodes(fail_select=fail_api, global_mode=global_mode)
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp); source = d/'source'; runtime = d/'runtime'
            original = self.source(ctl); original['mode'] = ctl.mode
            source.write_text(json.dumps(original)); original_bytes = source.read_bytes()
            runtime.write_bytes(b'original-runtime')
            writes = c.atomic_write; failed = False
            def write(path, data):
                nonlocal failed
                if fail_file and path == source and not failed:
                    failed = True; raise OSError('simulated source write failure')
                return writes(path, data)
            with patch.object(c,'SOURCE',source), patch.object(c,'RUNTIME',runtime), \
                 patch.object(c,'uci',lambda k: {'config_path':str(source),'enable':'1'}[k]), \
                 patch.object(c,'render_node_runtime',lambda a,b:b'new-runtime'), \
                 patch.object(c,'validation_env',lambda:{}), patch.object(c,'command',lambda *a,**k:b''), \
                 patch.object(c,'atomic_write',write):
                args=(c.node_id(ctl.names[1]),ctl,d/'backup')
                if fail_api or fail_file:
                    self.assertRaises(Exception,c.apply_node,*args)
                    self.assertEqual(ctl.selected,ctl.names[0])
                    self.assertEqual(ctl.global_selected,'DIRECT')
                    self.assertEqual(source.read_bytes(),original_bytes)
                    self.assertEqual(runtime.read_bytes(),b'original-runtime')
                    self.assertTrue(json.loads((d/'backup/result.json').read_bytes())['rolled_back'])
                else:
                    self.assertTrue(c.apply_node(*args)['ok'])
                    saved=json.loads(source.read_bytes())
                    self.assertEqual(saved['proxies'],original['proxies'])
                    self.assertEqual(saved['rules'],original['rules'])
                    self.assertEqual(saved['mode'],original['mode'])
                    self.assertEqual(saved['proxy-groups'][0]['default-selected'],ctl.names[1])
                    self.assertEqual(ctl.selected,ctl.names[1])
                    self.assertEqual(ctl.global_selected,'PROXY' if global_mode else 'DIRECT')

    def test_selection_persists_and_preserves_policy(self): self.exercise_select()
    def test_global_routes_selected_node_through_proxy_group(self): self.exercise_select(global_mode=True)
    def test_api_reply_lost_rolls_back(self): self.exercise_select(fail_api=True)
    def test_source_write_failure_rolls_back(self): self.exercise_select(fail_file=True)

    def test_latency_is_manual_and_never_selects_nodes(self):
        ctl=FakeNodes(failed_delay=True)
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);source=d/'source';source.write_text(json.dumps(self.source(ctl)))
            with patch.object(c,'STATE_DIR',d),patch.object(c,'SOURCE',source):
                self.assertEqual(c.latency_read(),{})
                result=c.run_latency(ctl)
                self.assertEqual(result['tested'],2);self.assertEqual(result['passed'],1)
                rows=c.latency_read()['results']
                self.assertEqual(rows[c.node_id(ctl.names[0])]['delay_ms'],123)
                self.assertEqual(rows[c.node_id(ctl.names[1])]['status'],'failed')
                self.assertIsNone(rows[c.node_id(ctl.names[1])]['delay_ms'])
                self.assertTrue(all(method=='GET' for _,method,_ in ctl.calls))
                self.assertEqual(ctl.selected,ctl.names[0])
                # Changing mode or a saved selector must not pretend the underlying node changed.
                s=json.loads(source.read_bytes());s['mode']='global';s['proxy-groups'][0]['default-selected']=ctl.names[1];source.write_text(json.dumps(s))
                self.assertEqual(len(c.latency_read()['results']),2)
                s['proxies'][0]['password']='new-secret';source.write_text(json.dumps(s))
                self.assertEqual(c.latency_read(),{})

    def test_native_yaml_transform_preserves_secret_and_rules(self):
        before=b'''mode: rule
secret: private-test
mixed-port: 7893
proxy-groups: [{name: PROXY, type: select, proxies: [node-one, node-two]}]
rules: ['MATCH,PROXY']
'''
        result=c.render_node_runtime(before,'node-two')
        self.assertIn(b'private-test',result);self.assertIn(b'MATCH,PROXY',result)
        self.assertIn(b'default-selected: node-two',result);self.assertIn(b'7893',result)


if __name__=='__main__':unittest.main(verbosity=2)
