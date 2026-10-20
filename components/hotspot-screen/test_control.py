import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import control as c

M='02:12:34:56:78:9a'
C={'section':'default_radio0','radio':'radio0','ssid':'test','key':'original123','encryption':'psk2','disabled':False,'macfilter':None,'maclist':[]}

class ControlTests(unittest.TestCase):
    def test_password_boundaries_and_symbols(self):
        for key in ['abcdefgh','a'*63,"a'\\;:!<&b"]:
            self.assertEqual(c.valid_password(key),key)
        for key in ['a'*7,'a'*64,'abc\ndefgh','中文password',None]:
            with self.assertRaises(ValueError):c.valid_password(key)

    def test_protected_mac_and_injection_rejected(self):
        for mac in ['ff:ff:ff:ff:ff:ff','00:00:00:00:00:00','02:50:00:00:e5:02',M+';reboot',M.upper()]:
            with self.assertRaises(ValueError):c.mac_value(mac)
        self.assertEqual(c.mac_value(M),M)

    def test_denylists_no_accidental_allow_conversion(self):
        self.assertEqual(c.deny_list({**C,'macfilter':'allow','maclist':[M]}),[])
        self.assertEqual(c.deny_list({**C,'macfilter':'deny','maclist':[M,M,'invalid']}),[M])

    @patch.object(c,'config',return_value=C)
    def test_unchanged_key_no_reload(self,_):
        a=c.Controller()
        with patch.object(c,'command') as run:
            self.assertTrue(a.request({'action':'password','password':C['key']})['unchanged'])
            run.assert_not_called()

    @patch.object(c,'config',return_value=C)
    def test_offline_device_never_kicked(self,_):
        with patch.object(c,'ubus',return_value={'clients':{}}) as bus:
            with self.assertRaises(ValueError):c.Controller().request({'action':'kick','mac':M})
            self.assertEqual(bus.call_count,1)

    @patch.object(c,'config',return_value=C)
    def test_unknown_request_fields_rejected(self,_):
        with self.assertRaises(ValueError):c.Controller().request({'action':'kick','mac':M,'command':'reboot'})

    def test_password_success_keeps_options_and_no_secret_argv(self):
        cfg=copy.deepcopy(C); a=c.Controller();a.operation={'state':'running'}
        def save(section,options):cfg.update(options)
        with patch.object(c,'config',side_effect=lambda:cfg.copy()),patch.object(c.Controller,'backup'),patch.object(c,'save_options',side_effect=save) as save_,patch.object(c,'command') as cmd,patch.object(c,'apply_wifi_password',return_value=None),patch.object(a,'collect'):
            a.password_job(C,'newkey123')
        self.assertEqual(a.operation['state'],'done')
        save_.assert_called_once_with(C['section'],{'key':'newkey123'})
        self.assertNotIn('newkey123',str(cmd.call_args_list))
        self.assertNotIn('newkey123',json.dumps(a.status()))

    def test_password_reload_failure_restores_only_key(self):
        cfg=copy.deepcopy(C);a=c.Controller();a.operation={'state':'running'}
        def save(section,options):cfg.update(options)
        with patch.object(c,'config',side_effect=lambda:cfg.copy()),patch.object(c.Controller,'backup'),patch.object(c,'save_options',side_effect=save),patch.object(c,'apply_wifi_password',side_effect=[RuntimeError('fail'),None]),patch.object(a,'collect'):
            a.password_job(C,'newkey123')
        self.assertEqual(cfg,C)
        self.assertTrue(a.operation['rolled_back'])

    def test_password_concurrent_change_not_overwritten(self):
        cfg=copy.deepcopy(C);a=c.Controller();a.operation={'state':'running'}
        def save(section,options):cfg.update(options)
        def change(*args,**kwargs):cfg['key']='someoneelse';raise RuntimeError('fail')
        with patch.object(c,'config',side_effect=lambda:cfg.copy()),patch.object(c.Controller,'backup'),patch.object(c,'save_options',side_effect=save),patch.object(c,'apply_wifi_password',side_effect=change),patch.object(a,'collect'):
            a.password_job(C,'newkey123')
        self.assertEqual(cfg['key'],'someoneelse');self.assertFalse(a.operation['rolled_back'])

    def test_block_failure_rolls_back_uci_nft_and_runtime_acl(self):
        cfg=copy.deepcopy(C);a=c.Controller()
        def save(section,options):cfg.update(options)
        def bus(method,body=None):return {'clients':{M:{'assoc':True}}} if method=='get_clients' else {'clients':[]}
        with patch.object(c,'config',side_effect=lambda:cfg.copy()),patch.object(c.Controller,'backup'),patch.object(c,'save_options',side_effect=save),patch.object(c,'ubus',side_effect=bus),patch.object(c,'set_blocked') as nft,patch.object(c,'runtime_acl',side_effect=[RuntimeError('ACL failure'),None]) as acl:
            with self.assertRaises(RuntimeError):a.request({'action':'block','mac':M})
        self.assertEqual(cfg,C);self.assertEqual(nft.call_args.args[0],[]);self.assertEqual(acl.call_args.args,(M,False))

    def test_counter_parser_ignores_rule_inline_counters(self):
        self.assertEqual(c.counter_values([{'rule':{'counter':{}}},{'counter':{'name':'up_123','bytes':42}}]),{'up_123':42})

    def test_collect_totals_session_reset_and_unknown_signal(self):
        a=c.Controller();a.ban_refresh=10**20
        values={'up_02123456789a':100,'down_02123456789a':200}
        def items():return [{'counter':{'name':n,'bytes':v}} for n,v in values.items()]
        stations={M:{'assoc':True,'authorized':True,'signal':0}}
        with patch.object(c,'config',return_value=C),patch.object(c,'ubus',side_effect=lambda *_:{'clients':stations}),patch.object(c,'nft_data',side_effect=items),patch.object(c,'ensure_counter'),patch.object(c,'set_blocked'),patch.object(c,'leases',return_value={}):
            a.collect();first=a.status()['clients'][0]
            self.assertIsNone(first['signal']);self.assertEqual(first['upload_bytes'],0)
            values['up_02123456789a']+=1024;a.collect();self.assertEqual(a.status()['clients'][0]['upload_bytes'],1024)
            stations.clear();a.collect();self.assertEqual(a.status()['clients'],[])
            stations[M]={'assoc':True};a.collect();self.assertEqual(a.status()['clients'][0]['upload_bytes'],0)

    def test_missing_counter_is_unknown_not_zero(self):
        a=c.Controller();a.ban_refresh=10**20
        with patch.object(c,'config',return_value=C),patch.object(c,'ubus',return_value={'clients':{M:{'assoc':True}}}),patch.object(c,'nft_data',return_value=[]),patch.object(c,'ensure_counter',side_effect=RuntimeError()),patch.object(c,'set_blocked'),patch.object(c,'leases',return_value={}):
            a.collect();self.assertIsNone(a.status()['clients'][0]['upload_bytes']);self.assertIsNotNone(a.status()['statistics_error'])

    def test_private_backup_exact_original(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'wireless').write_bytes(b'private fixture')
            with patch.object(c,'WIRELESS',root/'wireless'),patch.object(c,'BACKUP',root/'backups'):
                self.assertEqual(c.Controller().backup(),b'private fixture')
                p=next((root/'backups').glob('*/wireless'));self.assertEqual(p.stat().st_mode&0o777,0o600)

    def test_old_enabled_ap_is_not_reload_success(self):
        with patch.object(c,'command',return_value=b'{"radio0":{"up":true,"pending":true}}'):
            self.assertFalse(c.password_runtime_ready(C,'newkey123'))
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'hostapd-phy0.conf';p.write_text('interface=wlan0\nwpa_passphrase=oldkey123\n')
            with patch.object(c,'command',return_value=b'{"radio0":{"up":true,"pending":false}}'),patch.object(c,'ubus',return_value={'status':'ENABLED','ssid':'test'}),patch.object(c.Path,'glob',return_value=[p]):
                self.assertFalse(c.password_runtime_ready(C,'newkey123'))
                p.write_text('interface=wlan0\nwpa_passphrase=newkey123\n')
                self.assertTrue(c.password_runtime_ready(C,'newkey123'))

    def test_password_radio_stop_settle_then_start_and_verify(self):
        calls=[]
        def run(argv,**kwargs):
            calls.append(argv)
            return b'{"radio0":{"up":false,"pending":false}}' if argv[0]=='ubus' else b''
        with patch.object(c,'command',side_effect=run),patch.object(c,'password_runtime_ready',return_value=True) as ready:
            c.apply_wifi_password(C,'newkey123')
        self.assertEqual(calls,[['wifi','down','radio0'],['ubus','call','network.wireless','status'],['wifi','up','radio0']])
        ready.assert_called_once_with(C,'newkey123')

    def test_disabled_hotspot_password_save_never_enables_radio(self):
        with patch.object(c,'command') as cmd:
            c.apply_wifi_password({**C,'disabled':True},'newkey123')
            cmd.assert_not_called()

    def test_native_acl_block_and_unblock_do_not_send_extra_deauth(self):
        cfg=copy.deepcopy(C);a=c.Controller();stations={M:{'assoc':True}}
        def save(section,options):cfg.update(options)
        def acl(mac,blocked):
            if blocked:stations.clear()
        def bus(method,body=None):return {'clients':stations.copy()} if method=='get_clients' else {'clients':[]}
        with patch.object(c,'config',side_effect=lambda:cfg.copy()),patch.object(c.Controller,'backup'),patch.object(c,'save_options',side_effect=save),patch.object(c,'ubus',side_effect=bus) as ub,patch.object(c,'set_blocked'),patch.object(c,'runtime_acl',side_effect=acl),patch.object(a,'collect'):
            self.assertTrue(a.request({'action':'block','mac':M})['ok'])
            self.assertTrue(a.request({'action':'unblock','mac':M})['ok'])
        self.assertFalse(any(call.args[0]=='del_client' for call in ub.call_args_list))

    def test_unblock_clears_legacy_timed_ban_only_when_present(self):
        cfg={**copy.deepcopy(C),'macfilter':'deny','maclist':[M]};a=c.Controller();bans=[M]
        def save(section,options):cfg.update(options)
        def bus(method,body=None):
            if method=='list_bans':return {'clients':bans.copy()}
            if method=='del_client':bans.clear();return {}
            return {'clients':{}}
        with patch.object(c,'config',side_effect=lambda:cfg.copy()),patch.object(c.Controller,'backup'),patch.object(c,'save_options',side_effect=save),patch.object(c,'ubus',side_effect=bus) as ub,patch.object(c,'set_blocked'),patch.object(c,'runtime_acl'),patch.object(a,'collect'):
            self.assertTrue(a.request({'action':'unblock','mac':M})['ok'])
        del_calls=[call.args[1] for call in ub.call_args_list if call.args[0]=='del_client']
        self.assertEqual(del_calls,[{'addr':M,'reason':1,'deauth':True,'ban_time':0}])

if __name__=='__main__':unittest.main()
