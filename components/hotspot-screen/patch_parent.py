"""Minimal entry points in the author's existing hotspot page; exact anchors."""
from pathlib import Path
import sys

folder=Path(sys.argv[1]); destination=Path(sys.argv[2])
html=(folder/'index.html').read_text()
anchor='\t\t\t<button id="hs-showkey" class="btn small" data-t="show_key"></button>'
assert html.count(anchor)==1
html=html.replace(anchor,anchor+'\n\t\t\t<button id="hs-manage-password" class="btn small">修改热点密码</button>')
anchor='\t\t\t<div id="hs-list"></div>'
assert html.count(anchor)==1
html=html.replace(anchor,anchor+'\n\t\t\t<button id="hs-manage-devices" class="btn small">管理连接设备 / 黑名单</button>')
html=html.replace('<script src="app.js"></script>','<script src="app.js?v=hotspot-1.0.0"></script>')
js=(folder/'app.js').read_text()
anchor="function closeApp() {\n"
assert js.count(anchor)==1
js=js.replace(anchor,anchor+"\tif (appOpen?.id === 'hotspot') { qrFor = null; showKey = false; setText('hs-key',''); $('hs-showkey').textContent = t('show_key'); if(last) renderHotspot(last); }\n")
js+='''
// Local hotspot management, entered directly from the existing hotspot page.
async function openHotspotManager(view) {
    try {
        const r=await fetch('/api/plugins',{cache:'no-store'}).then(r=>r.json());
        const m=r.plugins?.find(m=>m.id==='hotspot');
        if(!m)throw Error('热点管理尚未安装');
        openApp({...m,entry:m.entry+'#'+view});
    }catch(e){toast(e.message||'热点管理无法打开');}
}
on('hs-manage-password','click',()=>openHotspotManager('password'));
on('hs-manage-devices','click',()=>openHotspotManager('devices'));
'''
(destination/'index.html').write_text(html)
(destination/'app.js').write_text(js)
