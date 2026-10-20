'use strict';
const $=id=>document.getElementById(id),esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let tab=location.hash.startsWith('#password')?'password':'devices',busy=false,reading=false,timer,last=null,confirmAction=null,focusId=null,qrVisible=false,lastOp=null;
function message(text,error=false){$('message').textContent=text;$('message').classList.toggle('error',error);}
function bytes(n){if(n==null)return'--';const u=['B','KiB','MiB','GiB'];let i=0;while(n>=1024&&i<3){n/=1024;i++;}return n.toFixed(i?1:0)+' '+u[i];}
function duration(n){if(n<60)return n+' 秒';if(n<3600)return Math.floor(n/60)+' 分 '+n%60+' 秒';return Math.floor(n/3600)+' 小时 '+Math.floor(n%3600/60)+' 分';}
function controls(){return Array.from(document.querySelectorAll('button')).filter(b=>!b.disabled&&b.offsetParent!==null&&(!$('confirm').hidden?$('confirm').contains(b):true));}
function button(id,label,action,cls=''){return '<button id="'+id+'" class="'+cls+'" data-action="'+action+'">'+label+'</button>';}
function setTab(name){tab=name;for(const p of ['password','devices','blocked']){$(p+'-pane').hidden=p!==name;document.querySelector('[data-tab="'+p+'"]').classList.toggle('active',p===name);}if(last)render(last);}
function render(s){
 last=s;busy=s.operation?.state==='running';e5.keepAwake(busy);$('status').textContent=busy?'正在保存…':s.stale?'状态已过期':s.association_available?'热点已就绪':'热点未就绪';$('ssid').textContent=s.ssid||'--';
 const active=document.activeElement?.id;const scroll=window.scrollY;
 let rows='';for(const c of s.clients||[]){const id=c.mac.replaceAll(':','');rows+='<div class="card" data-mac="'+esc(c.mac)+'"><div class="title name">'+esc(c.name||c.ip||'未命名设备')+'</div><div class="sub">'+esc(c.ip||'正在分配 IP')+' · '+esc(c.mac)+'</div><div class="sub">'+(c.authorized?'已连接':'认证中')+(c.signal!=null?' · '+c.signal+' dBm':'')+' · '+(c.time_source==='association'?'已连接 ':'已观察 ')+duration(c.observed_seconds)+'</div><div class="values">↑ '+bytes(c.upload_bytes)+'　↓ '+bytes(c.download_bytes)+'<br><span class="rate">↑ '+bytes(c.upload_rate)+'/s　↓ '+bytes(c.download_rate)+'/s</span></div><div class="actions">'+button('kick-'+id,'踢下线','kick')+button('block-'+id,'拉黑','block','danger')+'</div></div>';}
 $('device-list').innerHTML=rows||'<div class="empty">'+(s.association_available?'当前没有 Wi-Fi 设备连接':'无法读取连接列表，暂不可操作')+'</div>';
 $('blocked-list').innerHTML=(s.blocked||[]).map(c=>'<div class="card" data-mac="'+esc(c.mac)+'"><div class="title">'+esc(c.name||'已拉黑设备')+'</div><div class="sub">'+esc(c.mac)+'</div>'+button('unblock-'+c.mac.replaceAll(':',''),'解除拉黑','unblock')+'</div>').join('')||'<div class="empty">黑名单为空</div>';
 for(const b of document.querySelectorAll('[data-action]'))b.disabled=busy||s.stale||(!s.block_supported&&b.dataset.action!=='kick');
 $('save').disabled=busy||!s.password_supported;$('edit').disabled=busy||!s.password_supported;
 for(const b of document.querySelectorAll('#editor button'))b.disabled=busy;
 if(active&&$(active))$(active).focus({preventScroll:true});window.scrollTo(0,scroll);
 const op=s.operation;if(op&&op.id!==lastOp&&op.state!=='running'){
  lastOp=op.id;if(op.state==='failed')message(op.error||'操作未完成',true);
  else if(op.action==='password'){message('新密码已保存，二维码已更新');$('password').value='';$('editor').hidden=true;qrVisible=true;refreshQr();}
  else message(op.action==='kick'?'已踢下线，30 秒后允许重新连接':op.action==='block'?'已拉黑并保存':'已解除拉黑，可以重新连接');
 }
 if(s.statistics_error&&tab==='devices')message(s.statistics_error,true);
}
async function refresh(){if(reading)return;reading=true;try{const s=await e5.api('/status');if(!s.ok)throw Error(s.error);render(s);}catch(e){$('status').textContent='状态不可用';message(e.message||'读取失败',true);document.querySelectorAll('[data-action],#save').forEach(b=>b.disabled=true);}finally{reading=false;clearTimeout(timer);timer=setTimeout(refresh,2000);}}
async function refreshQr(){if(!qrVisible)return;try{const r=await fetch('/api/qr?t='+Date.now(),{cache:'no-store'});if(!r.ok)throw Error();$('qr').innerHTML=await r.text();$('qr-show').textContent='隐藏连接二维码';}catch(e){message('二维码读取失败，请重新查看',true);}}
function ask(text,fn){confirmAction=fn;$('confirm-text').textContent=text;$('confirm').hidden=false;$('confirm-no').focus();$('confirm').scrollIntoView({block:'nearest'});}
async function submit(path,body){if(busy)return;busy=true;e5.keepAwake(true);$('confirm').hidden=true;confirmAction=null;message('正在执行…');document.querySelectorAll('[data-action],#save').forEach(b=>b.disabled=true);try{const r=await e5.api(path,{body});if(!r.ok)throw Error(r.error||'操作失败');if(r.unchanged){message('密码与当前相同，无需修改');qrVisible=true;await refreshQr();}}catch(e){message(e.message||'操作未完成，请刷新',true);}finally{await refresh();}}
document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>{if(!$('confirm').hidden)return;setTab(b.dataset.tab);});
for(const id of ['device-list','blocked-list'])$(id).onclick=e=>{const b=e.target.closest('[data-action]'),row=b?.closest('[data-mac]');if(!row||busy)return;const a=b.dataset.action,mac=row.dataset.mac;const text=a==='kick'?'踢下线这台设备？30 秒后它可以重新连接。':a==='block'?'拉黑这台设备？它会立即断线，并禁止再次接入。':'解除这台设备的拉黑？';ask(text+'\n'+mac,()=>submit('/device',{action:a,mac}));};
$('confirm-yes').onclick=()=>confirmAction?.();$('confirm-no').onclick=()=>{$('confirm').hidden=true;confirmAction=null;};
$('edit').onclick=()=>{$('editor').hidden=false;layout('lower');$('keyboard').querySelector('button')?.focus();};
$('show').onclick=()=>{$('password').type=$('password').type==='password'?'text':'password';$('show').textContent=$('password').type==='password'?'显示':'隐藏';};
$('delete').onclick=()=>{$('password').value=$('password').value.slice(0,-1);};$('clear').onclick=()=>{$('password').value='';};
function append(char){if($('password').value.length<63)$('password').value+=char;}
function layout(name){const chars=name==='upper'?'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789':name==='symbols'?'!@#$%^&*()-_=+[]{};:,.?/\\|~`\'"<> ':'abcdefghijklmnopqrstuvwxyz0123456789';$('keyboard').replaceChildren();for(const c of chars){const b=document.createElement('button');b.textContent=c===' '?'空格':c;b.onclick=()=>append(c);$('keyboard').append(b);}}
document.querySelectorAll('[data-layout]').forEach(b=>b.onclick=()=>layout(b.dataset.layout));
$('save').onclick=()=>{const password=$('password').value;if(!/^[\x20-\x7e]{8,63}$/.test(password)){message('请输入 8–63 位字母、数字或英文符号',true);return;}ask('保存新密码并更新二维码？所有 Wi-Fi 设备会断线，需要用新密码重新连接。',()=>submit('/password',{password}));};
$('qr-show').onclick=()=>{qrVisible=!qrVisible;if(qrVisible)refreshQr();else{$('qr').replaceChildren();$('qr-show').textContent='查看当前连接二维码';}};
e5.onKey(k=>{if(k.kind==='back'){if(!$('confirm').hidden){$('confirm-no').click();return true;}if(!$('editor').hidden){$('editor').hidden=true;$('password').value='';return true;}return false;}if(k.kind==='digit'&&!$('editor').hidden){append(k.key);return true;}const list=controls();let i=list.indexOf(document.activeElement);if(['left','right','up','down'].includes(k.kind)){const step=k.kind==='left'||k.kind==='up'?-1:1;let next;
 const keys=Array.from($('keyboard').querySelectorAll('button')),j=keys.indexOf(document.activeElement);
 if(j>=0&&(k.kind==='up'||k.kind==='down'))next=keys[j+step*6]||(step>0?$('save'):document.querySelector('[data-layout="symbols"]'));
 else{ i=i<0?(step>0?0:list.length-1):(i+step+list.length)%list.length;next=list[i]; }
 next?.focus();next?.scrollIntoView({block:'nearest'});return true;}if(k.kind==='ok'){e5.press(list[i<0?0:i]);return true;}return false;});
window.addEventListener('pagehide',()=>{clearTimeout(timer);$('password').value='';e5.keepAwake(false);});setTab(tab);refresh();
