#!/usr/bin/python3
"""Local screen integration. No arbitrary paths, shell commands or credentials in replies."""
import fcntl
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import urllib.request
import urllib.parse
import uuid

SOURCE = Path('/etc/openclash/config/e5-reference.yaml')
RUNTIME = Path('/etc/openclash/e5-reference.yaml')
STATE_DIR = Path('/tmp/run/e5-openclash-screen')
BACKUP_DIR = Path('/root/e5-openclash-screen-backup-20261020')
MODES = ('direct', 'gfw', 'mainland', 'global')
PRIVATE_RULES = [
    'DOMAIN-SUFFIX,local,DIRECT',
    'IP-CIDR,10.0.0.0/8,DIRECT,no-resolve',
    'IP-CIDR,172.16.0.0/12,DIRECT,no-resolve',
    'IP-CIDR,192.168.0.0/16,DIRECT,no-resolve',
]


def rules_for(mode):
    if mode not in MODES:
        raise ValueError('invalid mode')
    return PRIVATE_RULES + (['GEOSITE,gfw,PROXY', 'MATCH,DIRECT'] if mode == 'gfw' else
                            ['GEOSITE,CN,DIRECT', 'GEOIP,CN,DIRECT', 'MATCH,PROXY'])


def core_mode(mode):
    return mode if mode in ('direct', 'global') else 'rule'


def classify(config, rules):
    mode = config.get('mode')
    if mode in ('direct', 'global'):
        return mode
    if mode != 'rule':
        return 'unknown'
    normalized = [(str(r.get('type', '')).lower(), str(r.get('payload', '')).lower(),
                   r.get('proxy')) for r in rules]
    if ('geosite', 'gfw', 'PROXY') in normalized and normalized[-1:] == [('match', '', 'DIRECT')]:
        return 'gfw'
    if (('geosite', 'cn', 'DIRECT') in normalized and
            ('geoip', 'cn', 'DIRECT') in normalized and
            normalized[-1:] == [('match', '', 'PROXY')]):
        return 'mainland'
    return 'custom'


def command(argv, *, data=None, seconds=8, check=True, env=None):
    p = subprocess.run(argv, input=data, capture_output=True, timeout=seconds, env=env)
    if check and p.returncode:
        raise RuntimeError('local command failed')
    return p.stdout


def uci(name):
    return command(['uci', '-q', 'get', 'openclash.config.' + name], check=False).decode().strip()


def atomic_write(path, data):
    fd, temp = tempfile.mkstemp(prefix='.' + path.name + '.', dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def state_write(value):
    STATE_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    atomic_write(STATE_DIR / 'operation.json', (json.dumps(value) + '\n').encode())


def state_read():
    try:
        return json.loads((STATE_DIR / 'operation.json').read_bytes())
    except (OSError, ValueError):
        return {}


def node_id(name):
    return hashlib.sha256(name.encode()).hexdigest()[:24]


def valid_node_id(value):
    return isinstance(value, str) and len(value) == 24 and all(x in '0123456789abcdef' for x in value)


def node_scope():
    source = json.loads(SOURCE.read_bytes())
    return hashlib.sha256(json.dumps([source.get('proxies'), source.get('proxy-providers')],
                                     sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def node_choices(controller, group=None):
    group = group if group is not None else controller.api('/proxies/PROXY')
    all_proxies = controller.api('/proxies').get('proxies', {})
    groups = {'Selector', 'URLTest', 'Fallback', 'LoadBalance', 'Relay'}
    special = {'DIRECT', 'REJECT', 'REJECT-DROP', 'PASS', 'COMPATIBLE', 'GLOBAL', 'PROXY'}
    result = []
    for name in group.get('all', []):
        detail = all_proxies.get(name, {})
        if name in special or not detail or detail.get('type') in groups:
            continue
        result.append({'id': node_id(name), 'name': name, 'type': detail.get('type', ''),
                       'selected': name == group.get('now')})
    return result


def latency_read():
    try:
        value = json.loads((STATE_DIR / 'latency.json').read_bytes())
        return value if isinstance(value, dict) and value.get('scope') == node_scope() else {}
    except (OSError, ValueError):
        return {}


def rule_signature(rules):
    return [(r.get('type'), r.get('payload'), r.get('proxy')) for r in rules]


class Controller:
    def __init__(self):
        port = uci('cn_port') or '9090'
        if not port.isdigit() or not 1 <= int(port) <= 65535:
            raise ValueError('invalid controller port')
        self.base = 'http://127.0.0.1:' + port
        self.secret = uci('dashboard_password')
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def api(self, path, method='GET', value=None, seconds=6):
        data = None if value is None else json.dumps(value).encode()
        req = urllib.request.Request(self.base + path, data=data, method=method,
                                      headers={'Authorization': 'Bearer ' + self.secret,
                                               'Content-Type': 'application/json'})
        with self.opener.open(req, timeout=seconds) as response:
            body = response.read(2 << 20)
            return json.loads(body) if body else {}

    def snapshot(self):
        config = self.api('/configs')
        rules = self.api('/rules').get('rules', [])
        group = self.api('/proxies/PROXY')
        return config, rules, group

    def verify(self, target):
        config, rules, group = self.snapshot()
        if classify(config, rules) != target:
            raise RuntimeError('mode verification failed')
        if target == 'global' and self.api('/proxies/GLOBAL').get('now') != 'PROXY':
            raise RuntimeError('global group verification failed')
        return group


def status():
    operation = state_read()
    if operation.get('state') == 'running':
        fd = os.open(STATE_DIR / 'lock', os.O_RDWR | os.O_CREAT, 0o600)
        try:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                operation = dict(operation, state='interrupted', error='上次切换中断，请检查后再操作')
            except BlockingIOError:
                pass
        finally:
            os.close(fd)
    result = {'ok': True, 'enabled': uci('enable') == '1', 'running': False,
              'managed': uci('config_path') == str(SOURCE), 'mode': 'unknown',
              'node': '', 'nodes': [], 'operation': operation}
    try:
        c = Controller()
        config, rules, group = c.snapshot()
        result.update(running=True, mode=classify(config, rules), node=group.get('now', ''))
        tests = latency_read() if result['managed'] else {}
        for node in node_choices(c, group):
            test = tests.get('results', {}).get(node['id'], {})
            node.update(test_status=test.get('status', 'untested'), delay_ms=test.get('delay_ms'),
                        tested_at=test.get('tested_at'))
            result['nodes'].append(node)
        result['last_tested_at'] = tests.get('tested_at')
    except Exception:
        result['error'] = 'OpenClash 未运行或控制接口暂不可用'
    return result


def render_runtime(before, target):
    # Ruby YAML is already an OpenClash dependency. No unsafe YAML object loading.
    ruby = '''c=YAML.safe_load(STDIN.read, permitted_classes: [], permitted_symbols: [], aliases: true)
c["mode"]=ARGV[0]
c["rules"]=ARGV[1].split("\\n")
c["proxy-groups"]=(c["proxy-groups"] || []).reject{|g|g["name"]=="GLOBAL"}
c["proxy-groups"] << {"name"=>"GLOBAL", "type"=>"select", "proxies"=>["PROXY"]}
print YAML.dump(c)
'''
    return command(['ruby', '-ryaml', '-e', ruby, core_mode(target), '\n'.join(rules_for(target))],
                   data=before)


def validation_env():
    # Match the existing core's resource allowlist; do not disable safe-path checks.
    pids = command(['pidof', 'clash']).split()
    if len(pids) != 1:
        raise RuntimeError('expected one active core')
    values = (Path('/proc') / pids[0].decode() / 'environ').read_bytes().split(b'\0')
    paths = next((v.split(b'=', 1)[1].decode() for v in values if v.startswith(b'SAFE_PATHS=')), '')
    return dict(os.environ, SAFE_PATHS=paths)


def apply_mode(target, controller, backup):
    if target not in MODES or uci('config_path') != str(SOURCE):
        raise RuntimeError('unmanaged config')
    if uci('enable') != '1':
        raise RuntimeError('service disabled')
    previous_config, previous_rules, _ = controller.snapshot()
    previous_global = controller.api('/proxies/GLOBAL').get('now')
    source_before, runtime_before = SOURCE.read_bytes(), RUNTIME.read_bytes()
    if len(source_before) > (1 << 20) or len(runtime_before) > (4 << 20):
        raise RuntimeError('oversized config')
    uci_before = uci('proxy_mode')
    source = json.loads(source_before)
    source['mode'] = core_mode(target)
    source['rules'] = rules_for(target)
    source['proxy-groups'] = [g for g in source.get('proxy-groups', []) if g['name'] != 'GLOBAL']
    source['proxy-groups'].append({'name': 'GLOBAL', 'type': 'select', 'proxies': ['PROXY']})
    source_after = (json.dumps(source, ensure_ascii=False, indent=2) + '\n').encode()
    runtime_after = render_runtime(runtime_before, target)
    backup.mkdir(mode=0o700, parents=True, exist_ok=False)
    atomic_write(backup / 'source.before', source_before)
    atomic_write(backup / 'runtime.before', runtime_before)
    atomic_write(backup / 'uci-proxy-mode.before', uci_before.encode())
    stage = backup / 'runtime.candidate.yaml'
    atomic_write(stage, runtime_after)
    try:
        command(['/etc/openclash/core/clash_meta', '-t', '-d', '/etc/openclash', '-f', str(stage)],
                seconds=15, env=validation_env())
    except Exception:
        atomic_write(backup / 'result.json', b'{"ok":false,"no_runtime_change":true}\n')
        raise
    applied = False
    try:
        # Native reload keeps listeners and firewall configuration; no service/system restart.
        applied = True  # A timed-out reply may still mean that the API applied the payload.
        controller.api('/configs?force=true', 'PUT', {'payload': runtime_after.decode()})
        controller.verify(target)
        atomic_write(SOURCE, source_after)
        atomic_write(RUNTIME, runtime_after)
        command(['uci', 'set', 'openclash.config.proxy_mode=' + core_mode(target)])
        command(['uci', 'commit', 'openclash'])
        if uci('proxy_mode') != core_mode(target):
            raise RuntimeError('persistent mode verification failed')
        controller.verify(target)
        atomic_write(backup / 'result.json', json.dumps({'ok': True, 'mode': target,
                     'source_sha256': hashlib.sha256(source_after).hexdigest(),
                     'runtime_sha256': hashlib.sha256(runtime_after).hexdigest()}).encode())
        return {'ok': True, 'mode': target}
    except Exception:
        if applied:
            atomic_write(SOURCE, source_before)
            atomic_write(RUNTIME, runtime_before)
            command(['uci', 'set', 'openclash.config.proxy_mode=' + uci_before])
            command(['uci', 'commit', 'openclash'])
            controller.api('/configs?force=true', 'PUT', {'payload': runtime_before.decode()})
            if previous_global:
                controller.api('/proxies/GLOBAL', 'PUT', {'name': previous_global})
            config, rules, _ = controller.snapshot()
            if config.get('mode') != previous_config.get('mode') or rules != previous_rules:
                raise RuntimeError('rollback verification failed')
            atomic_write(backup / 'result.json', b'{"ok":false,"rolled_back":true}\n')
        raise


def render_node_runtime(before, name):
    ruby = '''c=YAML.safe_load(STDIN.read, permitted_classes: [], permitted_symbols: [], aliases: true)
g=(c["proxy-groups"] || []).find{|v|v["name"]=="PROXY"}
abort "missing selector" unless g && g["type"]=="select"
g["default-selected"]=ARGV[0]
print YAML.dump(c)
'''
    return command(['ruby', '-ryaml', '-e', ruby, name], data=before)


def apply_node(target_id, controller, backup):
    if not valid_node_id(target_id) or uci('config_path') != str(SOURCE) or uci('enable') != '1':
        raise RuntimeError('invalid node or unmanaged config')
    before_config, before_rules, before_group = controller.snapshot()
    choices = node_choices(controller, before_group)
    matches = [n for n in choices if n['id'] == target_id]
    if len(matches) != 1:
        raise ValueError('node is no longer in PROXY')
    name = matches[0]['name']
    previous = before_group.get('now')
    previous_global = controller.api('/proxies/GLOBAL').get('now')
    source_before, runtime_before = SOURCE.read_bytes(), RUNTIME.read_bytes()
    source = json.loads(source_before)
    groups = [g for g in source.get('proxy-groups', []) if g.get('name') == 'PROXY']
    if len(groups) != 1 or groups[0].get('type') != 'select':
        raise RuntimeError('PROXY is not a manual selector')
    groups[0]['default-selected'] = name
    source_after = (json.dumps(source, ensure_ascii=False, indent=2) + '\n').encode()
    runtime_after = render_node_runtime(runtime_before, name)
    backup.mkdir(mode=0o700, parents=True, exist_ok=False)
    for filename, data in [('source.before', source_before), ('runtime.before', runtime_before)]:
        atomic_write(backup / filename, data)
    atomic_write(backup / 'selection.before.json', json.dumps({'PROXY': previous, 'GLOBAL': previous_global}).encode())
    stage = backup / 'runtime.candidate.yaml'
    atomic_write(stage, runtime_after)
    try:
        command(['/etc/openclash/core/clash_meta', '-t', '-d', '/etc/openclash', '-f', str(stage)],
                seconds=15, env=validation_env())
    except Exception:
        atomic_write(backup / 'result.json', b'{"ok":false,"no_runtime_change":true}\n')
        raise
    try:
        controller.api('/proxies/PROXY', 'PUT', {'name': name})
        if before_config.get('mode') == 'global' and previous_global != 'PROXY':
            controller.api('/proxies/GLOBAL', 'PUT', {'name': 'PROXY'})
        if controller.api('/proxies/PROXY').get('now') != name:
            raise RuntimeError('node selection verification failed')
        atomic_write(SOURCE, source_after)
        atomic_write(RUNTIME, runtime_after)
        config, rules, group = controller.snapshot()
        saved = json.loads(SOURCE.read_bytes())
        saved_group = next(g for g in saved['proxy-groups'] if g['name'] == 'PROXY')
        if (group.get('now') != name or saved_group.get('default-selected') != name or
                config.get('mode') != before_config.get('mode') or
                rule_signature(rules) != rule_signature(before_rules)):
            raise RuntimeError('node persistence or mode verification failed')
        result = {'ok': True, 'action': 'node', 'node': name, 'node_id': target_id}
        atomic_write(backup / 'result.json', json.dumps(result).encode())
        return result
    except Exception:
        atomic_write(SOURCE, source_before)
        atomic_write(RUNTIME, runtime_before)
        controller.api('/proxies/PROXY', 'PUT', {'name': previous})
        if previous_global:
            controller.api('/proxies/GLOBAL', 'PUT', {'name': previous_global})
        if controller.api('/proxies/PROXY').get('now') != previous:
            raise RuntimeError('node rollback verification failed')
        atomic_write(backup / 'result.json', b'{"ok":false,"rolled_back":true}\n')
        raise


def run_latency(controller):
    choices = node_choices(controller)
    if not choices or len(choices) > 32:
        raise ValueError('node count must be 1..32')
    scope = node_scope()

    def probe(node):
        at = int(time.time())
        try:
            query = urllib.parse.urlencode({'url': 'https://www.gstatic.com/generate_204',
                                            'timeout': 8000, 'expected': '204'})
            value = controller.api('/proxies/' + urllib.parse.quote(node['name'], safe='') +
                                   '/delay?' + query, seconds=10).get('delay')
            if not isinstance(value, int) or isinstance(value, bool) or not 0 < value < 65536:
                raise ValueError('invalid delay')
            return node['id'], {'status': 'ok', 'delay_ms': value, 'tested_at': at}
        except Exception:
            return node['id'], {'status': 'failed', 'delay_ms': None, 'tested_at': at}

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = dict(pool.map(probe, choices))
    tested_at = int(time.time())
    if scope != node_scope():
        raise RuntimeError('node definitions changed during test')
    atomic_write(STATE_DIR / 'latency.json', json.dumps({'scope': scope, 'tested_at': tested_at,
                 'results': results}).encode())
    return {'ok': True, 'action': 'test', 'tested': len(results),
            'passed': sum(r['status'] == 'ok' for r in results.values()), 'tested_at': tested_at}


def request_action(action, target):
    if action == 'mode' and target not in MODES:
        return {'ok': False, 'error': '无效模式'}
    if action == 'node' and not valid_node_id(target):
        return {'ok': False, 'error': '无效节点'}
    if action not in ('mode', 'node', 'test'):
        return {'ok': False, 'error': '无效操作'}
    STATE_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(STATE_DIR / 'lock', os.O_RDWR | os.O_CREAT, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {'ok': False, 'error': '正在切换，请稍候'}
        if state_read().get('state') == 'running':
            return {'ok': False, 'error': '上次切换中断，请先检查恢复记录'}
        current = status()
        if not current.get('running') or not current.get('enabled'):
            return {'ok': False, 'error': '请先在 OpenClash 管理页启动服务'}
        if not current.get('managed'):
            return {'ok': False, 'error': '当前配置未接入屏幕控制，请使用管理页操作'}
        source = json.loads(SOURCE.read_bytes())
        if (action == 'mode' and current.get('mode') == target and uci('proxy_mode') == core_mode(target)
                and source.get('mode') == core_mode(target) and source.get('rules') == rules_for(target)):
            return {'ok': True, 'mode': target, 'unchanged': True}
        label = target
        if action == 'node':
            matches = [n for n in current['nodes'] if n['id'] == target]
            if len(matches) != 1:
                return {'ok': False, 'error': '节点已变化，请刷新列表'}
            label = matches[0]['name']
        if action == 'test' and not 1 <= len(current['nodes']) <= 32:
            return {'ok': False, 'error': '可测试节点数量需为 1–32 个'}
        job = uuid.uuid4().hex
        state_write({'id': job, 'state': 'running', 'action': action, 'target': target,
                     'label': label, 'started': int(time.time())})
        # The child inherits the flock open-file description. Closing it here does not unlock the child.
        try:
            subprocess.Popen([sys.executable, str(Path(__file__).resolve()), 'worker', action, target, job, str(fd)],
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             pass_fds=(fd,), start_new_session=True)
        except Exception:
            state_write({'id': job, 'state': 'failed', 'error': '无法启动切换任务'})
            raise
        return {'ok': True, 'accepted': True, 'id': job}
    finally:
        os.close(fd)


def request(target):
    return request_action('mode', target)


def worker(action, target, job, fd):
    try:
        controller = Controller()
        if action == 'mode':
            result = apply_mode(target, controller, BACKUP_DIR / job)
        elif action == 'node':
            result = apply_node(target, controller, BACKUP_DIR / job)
        elif action == 'test':
            result = run_latency(controller)
        else:
            raise ValueError('invalid action')
        state_write(dict(result, action=action, id=job, state='done', ended=int(time.time())))
    except Exception:
        receipt = BACKUP_DIR / job / 'result.json'
        details = json.loads(receipt.read_bytes()) if receipt.exists() else {}
        restored = details.get('rolled_back', False)
        state_write({'id': job, 'state': 'failed', 'action': action, 'rolled_back': restored,
                     'error': '延迟测试未完成，未切换节点' if action == 'test' else
                     '切换失败，已恢复原设置' if restored else
                     '切换未完成，原设置未更改' if details.get('no_runtime_change') else '切换未完成，请检查恢复记录',
                     'ended': int(time.time())})
    finally:
        os.close(fd)


if __name__ == '__main__':
    try:
        if sys.argv[1:] == ['status']:
            print(json.dumps(status(), ensure_ascii=False))
        elif len(sys.argv) == 3 and sys.argv[1] == 'request':
            print(json.dumps(request(sys.argv[2]), ensure_ascii=False))
        elif len(sys.argv) == 3 and sys.argv[1] == 'select-node':
            print(json.dumps(request_action('node', sys.argv[2]), ensure_ascii=False))
        elif sys.argv[1:] == ['test-nodes']:
            print(json.dumps(request_action('test', '-'), ensure_ascii=False))
        elif len(sys.argv) == 6 and sys.argv[1] == 'worker' and sys.argv[2] in ('mode', 'node', 'test'):
            worker(sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5]))
        else:
            raise ValueError('invalid command')
    except Exception:
        print(json.dumps({'ok': False, 'error': '操作失败，请检查 OpenClash 状态'}, ensure_ascii=False))
        sys.exit(1)
