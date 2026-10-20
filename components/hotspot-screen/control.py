#!/usr/bin/python3
"""Local hotspot controller. No partition access; no secrets in argv or status.

Accounting counts unicast Ethernet bytes crossing wlan0 bridge hooks, including
locally terminated proxy flows. RAM only, since observed association; not billing.
"""
import copy
import fcntl
import json
import os
from pathlib import Path
import re
import signal
import socket
import socketserver
import subprocess
import sys
import threading
import time
import uuid

RUN = Path('/tmp/run/e5-hotspot')
SOCKET = RUN / 'control.sock'
TABLE = 'e5hotspot'
IFACE = 'wlan0'
OBJ = 'hostapd.' + IFACE
WIRELESS = Path('/etc/config/wireless')
BACKUP = Path('/root/e5-hotspot-backup-20261020')
MAC = re.compile(r'(?:[0-9a-f]{2}:){5}[0-9a-f]{2}\Z')
PROTECTED = {'02:50:00:00:e5:02'}
CONFIG_CODE = """import {cursor} from 'uci'; let c=cursor(),a=null;
c.foreach('wireless','wifi-iface',s=>{if(!a&&s.mode=='ap')a=s;});
if(!a)exit(1); print(sprintf('%J',{section:a['.name'],radio:a.device,ssid:a.ssid,key:a.key,
encryption:a.encryption,macfilter:a.macfilter,maclist:a.maclist??[],
disabled:a.disabled=='1'||c.get('wireless',a.device,'disabled')=='1'}));"""
WRITE_CODE = """import {cursor} from 'uci';import {readfile} from 'fs';
let d=json(readfile('/dev/stdin')),c=cursor();
if(c.get('wireless',d.section,'mode')!='ap')exit(1);
for(let k in keys(d.options)){if(index(['key','macfilter','maclist'],k)<0)exit(1);
if(d.options[k]==null)c.delete('wireless',d.section,k);else c.set('wireless',d.section,k,d.options[k]);}
if(!c.commit('wireless'))exit(1);"""


def command(argv, data=None, timeout=4):
    p = subprocess.run(argv, input=data, capture_output=True, timeout=timeout)
    if p.returncode:
        # Never echo command inputs, stdout or stderr: these can contain PSKs.
        raise RuntimeError('设备命令未成功：' + Path(argv[0]).name)
    return p.stdout


def ubus(method, body=None):
    return json.loads(command(['ubus', 'call', OBJ, method, json.dumps(body or {})]) or b'{}')


def ctrl_socket():
    # hostapd is jailed: a client socket in /tmp is not visible to it.
    # Share its mounted control directory and grant only its network group.
    target = '/var/run/hostapd/' + IFACE
    path = '/var/run/hostapd/e5-hs-' + uuid.uuid4().hex
    client = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        client.bind(path)
        os.chown(path, 0, os.stat(target).st_gid)
        os.chmod(path, 0o660)
        client.settimeout(2)
        client.connect(target)
        return client, path
    except Exception:
        client.close()
        Path(path).unlink(missing_ok=True)
        raise


def ctrl(text):
    client, path = ctrl_socket()
    try:
        client.send(text.encode())
        return client.recv(65535).decode().strip()
    finally:
        client.close()
        Path(path).unlink(missing_ok=True)


def runtime_acl(mac, blocked):
    op = 'ADD_MAC' if blocked else 'DEL_MAC'
    if ctrl('DENY_ACL ' + op + ' ' + mac) != 'OK':
        raise RuntimeError('设备访问名单更新失败')
    listed = {row.split()[0].lower() for row in ctrl('DENY_ACL SHOW').splitlines() if row.strip()}
    if (mac in listed) != blocked:
        raise RuntimeError('设备访问名单复核失败')


def config():
    return json.loads(command(['ucode', '-e', CONFIG_CODE]))


def save_options(section, options):
    command(['ucode', '-e', WRITE_CODE], json.dumps({'section': section, 'options': options}).encode())


def password_runtime_ready(c, key):
    """Do not mistake an old ENABLED hostapd for the completed reload."""
    if c.get('disabled'):
        return True
    radios = json.loads(command(['ubus', 'call', 'network.wireless', 'status']))
    radio = radios.get(c.get('radio'), {})
    if radio.get('up') is not True or radio.get('pending') is not False:
        return False
    state = ubus('get_status')
    if state.get('status') != 'ENABLED' or state.get('ssid') != c.get('ssid'):
        return False
    for path in Path('/var/run').glob('hostapd-*.conf'):
        fields = dict(line.split('=', 1) for line in path.read_text().splitlines() if '=' in line)
        if fields.get('interface') == IFACE and fields.get('wpa_passphrase') == key:
            return True
    return False


def apply_wifi_password(c, key):
    if c.get('disabled'):
        return
    radio = c.get('radio')
    if not isinstance(radio, str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,32}', radio):
        raise RuntimeError('无线设备标识无效')
    # This Unisoc driver can retain a previous station's key state after a
    # hostapd-only reload. Password changes already require every client to
    # reconnect: tear down this radio completely, without rebooting the device.
    command(['wifi', 'down', radio], timeout=15)
    deadline = time.monotonic() + 15
    while True:
        state = json.loads(command(['ubus', 'call', 'network.wireless', 'status'])).get(radio, {})
        if state.get('up') is False and state.get('pending') is False:
            break
        if time.monotonic() >= deadline:
            raise RuntimeError('无线接口未完全停止')
        time.sleep(.2)
    command(['wifi', 'up', radio], timeout=25)
    deadline = time.monotonic() + 40
    while time.monotonic() < deadline:
        try:
            if password_runtime_ready(c, key):
                return
        except Exception:
            pass
        time.sleep(1)
    raise RuntimeError('热点未能在时限内恢复')


def mac_value(value):
    if not isinstance(value, str) or not MAC.fullmatch(value):
        raise ValueError('无效设备地址')
    if int(value[:2], 16) & 1 or value in PROTECTED or value == '00:00:00:00:00:00':
        raise ValueError('不能操作系统或 USB 管理设备')
    return value


def valid_password(value):
    if not isinstance(value, str) or not 8 <= len(value) <= 63 or any(not 32 <= ord(c) <= 126 for c in value):
        raise ValueError('密码需为 8–63 位可打印英文字符，支持字母、数字和符号')
    return value


def deny_list(c):
    values = c.get('maclist') or []
    if isinstance(values, str):
        values = values.split()
    return sorted({v.lower() for v in values if isinstance(v, str) and MAC.fullmatch(v.lower())}) if c.get('macfilter') == 'deny' else []


def atomic_json(path, data):
    temp = path.with_name(path.name + '.' + uuid.uuid4().hex)
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(temp, path)


def leases():
    result = {}
    try:
        for line in Path('/tmp/dhcp.leases').read_text().splitlines():
            f = line.split()
            if len(f) >= 4 and MAC.fullmatch(f[1].lower()):
                result[f[1].lower()] = {'ip': f[2], 'name': f[3] if f[3] != '*' else None}
    except OSError:
        pass
    return result


def nft_data():
    return json.loads(command(['nft', '-j', 'list', 'table', 'bridge', TABLE]))['nftables']


def counter_values(items):
    return {o['counter']['name']: o['counter']['bytes'] for o in items if 'counter' in o and 'name' in o['counter']}


def nft_apply(script):
    command(['nft', '-f', '-'], script.encode())


def counter_name(mac, direction):
    return direction + '_' + mac.replace(':', '')


def create_table():
    nft_apply('table bridge ' + TABLE + ''' {
 set blocked { type ether_addr; }
 chain ingress { type filter hook prerouting priority -310; policy accept;
  iifname "wlan0" ether saddr @blocked drop
 }
 chain egress { type filter hook postrouting priority 310; policy accept;
  oifname "wlan0" ether daddr @blocked drop
 }
}''')


def ensure_counter(mac, values):
    lines = []
    for direction, chain, iface, addr in [('up', 'ingress', 'iifname', 'saddr'), ('down', 'egress', 'oifname', 'daddr')]:
        name = counter_name(mac, direction)
        if name not in values:
            lines.extend([f'add counter bridge {TABLE} {name}',
                          f'add rule bridge {TABLE} {chain} {iface} "{IFACE}" ether {addr} {mac} counter name {name}'])
    if lines:
        nft_apply('\n'.join(lines))


def set_blocked(macs):
    script = f'flush set bridge {TABLE} blocked\n'
    if macs:
        script += f'add element bridge {TABLE} blocked {{ ' + ', '.join(macs) + ' }\n'
    nft_apply(script)


class Controller:
    def __init__(self):
        self.lock = threading.RLock()
        self.sessions = {}
        self.started = time.time()
        self.snapshot = {'ok': False, 'error': '正在读取热点状态'}
        self.operation = None
        self.nft_error = None
        self.ban_refresh = 0
        self.last_blocks = None
        self.events = {}

    def association_events(self):
        while True:
            client = None
            path = None
            try:
                client, path = ctrl_socket()
                client.send(b'ATTACH')
                if client.recv(1024).strip() != b'OK':
                    raise RuntimeError('event attach')
                while True:
                    try:
                        event = client.recv(8192).decode(errors='replace')
                    except socket.timeout:
                        client.send(b'PING')
                        continue
                    match = re.search(r'AP-STA-(CONNECTED|DISCONNECTED) ((?:[0-9a-f]{2}:){5}[0-9a-f]{2})', event)
                    if match:
                        kind, mac = match.groups()
                        with self.lock:
                            if mac in self.sessions:
                                self.sessions[mac]['online'] = False
                            if kind == 'CONNECTED':
                                self.events[mac] = (time.time(), time.monotonic())
                            else:
                                self.events.pop(mac, None)
            except Exception:
                time.sleep(3)
            finally:
                if client:
                    client.close()
                if path:
                    Path(path).unlink(missing_ok=True)

    def collect(self):
        with self.lock:
            if self.operation and self.operation.get('state') == 'running':
                return
            c = config()
            try:
                stations = ubus('get_clients').get('clients', {})
                available = True
            except Exception:
                stations, available = {}, False
            observed = time.monotonic()
            wall = time.time()
            values = {}
            try:
                try:
                    values = counter_values(nft_data())
                except Exception:
                    create_table()
                    # A reset table defines a new statistics epoch, never subtract old counters.
                    self.sessions = {}
                    self.last_blocks = None
                blocks = deny_list(c)
                if blocks != self.last_blocks:
                    set_blocked(blocks)
                    self.last_blocks = blocks
                for mac, station in stations.items():
                    if MAC.fullmatch(mac) and station.get('assoc'):
                        ensure_counter(mac, values)
                values = counter_values(nft_data())
                self.nft_error = None
            except Exception:
                self.nft_error = '流量统计暂不可用'
            blocks = deny_list(c)
            if available and wall - self.ban_refresh > 180:
                listed = {row.split()[0].lower() for row in ctrl('DENY_ACL SHOW').splitlines() if row.strip()}
                for mac in blocks:
                    if mac not in listed:
                        runtime_acl(mac, True)
                        # DENY_ACL already deauthenticates matching stations.
                        # Only fall back if this hostapd build left one associated.
                        if ubus('get_clients').get('clients', {}).get(mac, {}).get('assoc'):
                            ubus('del_client', {'addr': mac, 'reason': 1, 'deauth': True})
                self.ban_refresh = wall
            hints = leases()
            online = []
            if available:
                for s in self.sessions.values():
                    s['present'] = False
                for mac, station in stations.items():
                    if not MAC.fullmatch(mac) or not station.get('assoc'):
                        continue
                    up = values.get(counter_name(mac, 'up'))
                    down = values.get(counter_name(mac, 'down'))
                    s = self.sessions.get(mac)
                    if not s or not s.get('online'):
                        event = self.events.pop(mac, None)
                        s = {'since': event[0] if event else wall, 'mono': event[1] if event else observed,
                             'time_source': 'association' if event else 'observed',
                             'up0': up, 'down0': down, 'up': up, 'down': down, 'at': observed, 'online': True}
                        self.sessions[mac] = s
                    elapsed = max(0.001, observed - s['at'])
                    rate_up = max(0, up - s['up']) / elapsed if up is not None and s['up'] is not None else None
                    rate_down = max(0, down - s['down']) / elapsed if down is not None and s['down'] is not None else None
                    if up is not None and (s['up0'] is None or up < s['up0']):
                        s['up0'] = up
                    if down is not None and (s['down0'] is None or down < s['down0']):
                        s['down0'] = down
                    s.update(present=True, online=True, up=up, down=down, at=observed)
                    sig = station.get('signal')
                    if not isinstance(sig, (int, float)) or not -127 <= sig < 0:
                        sig = None
                    online.append({'mac': mac, **hints.get(mac, {}), 'online': True,
                                   'authorized': bool(station.get('authorized')), 'blocked': mac in blocks,
                                   'signal': sig, 'observed_since': s['since'], 'observed_seconds': int(observed-s['mono']),
                                   'time_source': s['time_source'],
                                   'upload_bytes': max(0, up-s['up0']) if up is not None and s['up0'] is not None else None,
                                   'download_bytes': max(0, down-s['down0']) if down is not None and s['down0'] is not None else None,
                                   'upload_rate': rate_up, 'download_rate': rate_down})
                for s in self.sessions.values():
                    if not s.get('present'):
                        s['online'] = False
            self.snapshot = {'ok': True, 'ssid': c.get('ssid'), 'enabled': not c.get('disabled'),
                             'association_available': available, 'clients': online,
                             'blocked': [{'mac': mac, **hints.get(mac, {})} for mac in blocks],
                             'updated_at': wall, 'statistics_started_at': self.started,
                             'statistics_error': self.nft_error, 'interval_seconds': 2,
                             'scope': '本次观察到的连接 · Wi-Fi 单播收发，含代理和本地通信；重启清零，非运营商计费',
                             'password_supported': str(c.get('encryption', '')).startswith(('psk', 'sae')),
                             'block_supported': c.get('macfilter') in (None, '', 'disable', 'deny')}

    def status(self):
        with self.lock:
            value = copy.deepcopy(self.snapshot)
            value['operation'] = copy.deepcopy(self.operation)
            value['stale'] = time.time() - value.get('updated_at', 0) > 8
            return value

    def backup(self):
        BACKUP.mkdir(mode=0o700, exist_ok=True)
        directory = BACKUP / uuid.uuid4().hex
        directory.mkdir(mode=0o700)
        before = WIRELESS.read_bytes()
        fd = os.open(directory/'wireless', os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as f:
            f.write(before)
            f.flush()
            os.fsync(f.fileno())
        return before

    def request(self, req):
        if not isinstance(req, dict):
            raise ValueError('无效请求')
        action = req.get('action')
        if action == 'status' and set(req) == {'action'}:
            return self.status()
        with self.lock:
            if self.operation and self.operation['state'] == 'running':
                raise ValueError('已有操作正在执行')
            c = config()
            if action == 'password':
                if set(req) != {'action', 'password'}:
                    raise ValueError('无效请求')
                key = valid_password(req['password'])
                if not str(c.get('encryption', '')).startswith(('psk', 'sae')):
                    raise ValueError('当前加密方式不支持屏幕改密码')
                if key == c.get('key'):
                    return {'ok': True, 'unchanged': True}
                self.operation = {'id': uuid.uuid4().hex, 'action': action, 'state': 'running'}
                threading.Thread(target=self.password_job, args=(c, key), daemon=True).start()
                return {'ok': True, 'operation': self.operation.copy()}
            if action not in ('kick', 'block', 'unblock') or set(req) != {'action', 'mac'}:
                raise ValueError('无效操作')
            mac = mac_value(req['mac'])
            stations = ubus('get_clients').get('clients', {})
            blocks = deny_list(c)
            if action in ('kick', 'block') and not stations.get(mac, {}).get('assoc'):
                raise ValueError('设备已离线，请刷新后重选')
            if action == 'kick':
                ubus('del_client', {'addr': mac, 'reason': 1, 'deauth': True, 'ban_time': 30000})
            else:
                if c.get('macfilter') not in (None, '', 'disable', 'deny'):
                    raise ValueError('当前为允许名单，请在管理网页调整')
                if action == 'unblock' and mac not in blocks:
                    raise ValueError('该设备不在黑名单')
                self.backup()
                desired = sorted(set(blocks + [mac])) if action == 'block' else [m for m in blocks if m != mac]
                original = {'macfilter': c.get('macfilter'), 'maclist': c.get('maclist')}
                try:
                    save_options(c['section'], {'macfilter': 'deny' if desired else None, 'maclist': desired or None})
                    if deny_list(config()) != desired:
                        raise RuntimeError('黑名单保存复核失败')
                    set_blocked(desired)
                    runtime_acl(mac, action == 'block')
                    if action == 'block' and ubus('get_clients').get('clients', {}).get(mac, {}).get('assoc'):
                        ubus('del_client', {'addr': mac, 'reason': 1, 'deauth': True})
                    # Persistent blocks use the native ACL, not a second timed
                    # ubus ban. In particular, normal unblock sends NO deauth.
                    # Clear a timed ban only when migrating an older block.
                    bans = ubus('list_bans').get('clients', [])
                    if action == 'unblock' and mac in bans:
                        ubus('del_client', {'addr': mac, 'reason': 1, 'deauth': True, 'ban_time': 0})
                        if mac in ubus('list_bans').get('clients', []):
                            raise RuntimeError('旧临时限制未解除')
                    self.last_blocks = desired
                    self.ban_refresh = 0
                except Exception:
                    save_options(c['section'], original)
                    set_blocked(blocks)
                    runtime_acl(mac, mac in blocks)
                    raise RuntimeError('操作未完成，已回退黑名单设置')
            self.operation = {'id': uuid.uuid4().hex, 'action': action, 'state': 'done'}
        self.collect()
        return {'ok': True}

    def password_job(self, c, key):
        # No main lock across reload/wait: status remains available to the screen.
        saved = False
        old_key = c.get('key')
        try:
            self.backup()
            if config() != c:
                raise RuntimeError('热点配置已被其他页面修改，请重新保存')
            save_options(c['section'], {'key': key})
            saved = True
            if config().get('key') != key:
                raise RuntimeError('密码写入复核失败')
            apply_wifi_password(c, key)
            if config().get('key') != key:
                raise RuntimeError('密码已被其他程序修改')
            self.operation.update(state='done')
        except Exception:
            rolled_back = not saved
            if saved:
                try:
                    # Do not overwrite someone else's later password update.
                    if config().get('key') != key:
                        raise RuntimeError('配置冲突')
                    save_options(c['section'], {'key': old_key})
                    apply_wifi_password(c, old_key)
                    rolled_back = config().get('key') == old_key
                except Exception:
                    rolled_back = False
            self.operation.update(state='failed', error='保存未完成，已还原原密码' if rolled_back else '保存未完成，请保持 USB 并检查热点配置', rolled_back=rolled_back)
        finally:
            self.ban_refresh = 0
            try:
                self.collect()
            except Exception:
                pass


def daemon():
    RUN.mkdir(parents=True, mode=0o700, exist_ok=True)
    RUN.chmod(0o700)
    lock = os.open(RUN/'daemon.lock', os.O_RDWR|os.O_CREAT, 0o600)
    fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
    SOCKET.unlink(missing_ok=True)
    controller = Controller()
    threading.Thread(target=controller.association_events, daemon=True).start()

    class Handler(socketserver.StreamRequestHandler):
        def handle(self):
            self.request.settimeout(3)
            try:
                raw = self.rfile.readline(4097)
                if len(raw) > 4096:
                    raise ValueError('请求过长')
                answer = controller.request(json.loads(raw))
            except ValueError as e:
                answer = {'ok': False, 'error': str(e)}
            except Exception:
                answer = {'ok': False, 'error': '操作未完成，请刷新实际状态'}
            self.wfile.write(json.dumps(answer, ensure_ascii=False).encode()+b'\n')

    class Server(socketserver.ThreadingUnixStreamServer):
        daemon_threads = True

    server = Server(str(SOCKET), Handler)
    os.chmod(SOCKET, 0o600)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    while True:
        try:
            controller.collect()
        except Exception:
            controller.snapshot = {'ok': False, 'error': '热点状态暂不可用'}
        # Clean secret request files after a killed HTTP worker; never persistent.
        for path in RUN.glob('request-*'):
            if time.time()-path.stat().st_mtime > 60:
                path.unlink(missing_ok=True)
        time.sleep(2)


def rpc(path=None):
    if path:
        p = Path(path)
        if p.parent != RUN or not p.name.startswith('request-') or p.is_symlink():
            raise ValueError('无效请求路径')
        data = p.read_bytes()
        p.unlink()
    else:
        data = sys.stdin.buffer.read(4097)
    if len(data) > 4096:
        raise ValueError('请求过长')
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(8)
        client.connect(str(SOCKET))
        client.sendall(data.rstrip(b'\n')+b'\n')
        with client.makefile('rb') as f:
            return json.loads(f.readline(1<<20))


if __name__ == '__main__':
    if len(sys.argv) == 2 and sys.argv[1] == 'daemon':
        daemon()
    else:
        try:
            result = rpc(sys.argv[2] if len(sys.argv) == 3 and sys.argv[1] == 'rpc' else None)
        except Exception:
            result = {'ok': False, 'error': '热点管理服务暂不可用'}
        print(json.dumps(result, ensure_ascii=False))
