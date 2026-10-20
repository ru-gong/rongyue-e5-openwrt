'use strict';
const labels={direct:'直连模式',gfw:'GFW 模式',mainland:'大陆白名单',global:'全局模式',custom:'自定义规则',unknown:'未取得运行模式'};
const modeButtons=Array.from(document.querySelectorAll('[data-mode]'));
const byId=id=>document.getElementById(id);
modeButtons.forEach(b=>b.dataset.control='mode:'+b.dataset.mode);
byId('test-nodes').dataset.control='test';
let focusKey='mode:mainland',busy=false,submitting=false,reading=false,timer=null,lastOperation=null,lastStatus=null,refreshFailed=false;
let nodeIds='';

function controls(){return [...modeButtons,byId('test-nodes'),...document.querySelectorAll('[data-node]')];}
function focusControl(index){const list=controls();const el=list[(index+list.length)%list.length];if(el){focusKey=el.dataset.control;el.focus({preventScroll:true});el.scrollIntoView({block:'nearest'});}}
function message(text,error=false){byId('message').textContent=text;byId('message').classList.toggle('error',error);}
function renderNodes(s){
 const nodes=s.nodes||[],ids=nodes.map(n=>n.id).join(',');
 if(ids!==nodeIds){
  nodeIds=ids;byId('node-list').replaceChildren();
  for(const n of nodes){
   const button=document.createElement('button');button.className='node-choice';button.dataset.node=n.id;button.dataset.control='node:'+n.id;
   const name=document.createElement('span');name.className='node-name';const delay=document.createElement('span');delay.className='node-delay';button.append(name,delay);
   button.addEventListener('click',()=>{focusKey=button.dataset.control;submit('/node',{id:n.id},'正在切换节点…');});byId('node-list').append(button);
  }
 }
 for(const n of nodes){
  const button=byId('node-list').querySelector('[data-node="'+n.id+'"]');
  button.querySelector('.node-name').textContent=n.name;
  const delay=button.querySelector('.node-delay');delay.textContent=n.test_status==='ok'?n.delay_ms+' ms':n.test_status==='failed'?'超时/失败':'未测试';
  delay.classList.toggle('good',n.test_status==='ok');delay.classList.toggle('bad',n.test_status==='failed');
  button.classList.toggle('active',n.selected);button.setAttribute('aria-pressed',String(n.selected));
 }
 if(!nodes.length)byId('node-list').textContent='没有可选择的代理节点';
 byId('test-time').textContent=s.last_tested_at?'HTTPS 延迟 · 上次 '+e5.time(s.last_tested_at*1000):'HTTPS 延迟 · 尚未测试';
}
function render(s){
 lastStatus=s;const op=s.operation||{},pending=op.state==='running';busy=submitting||pending;
 e5.keepAwake(busy);
 byId('service').textContent=pending?(op.action==='test'?'测试中':'切换中'):s.running?'核心运行':s.enabled?'核心未就绪':'已停用';
 byId('service').classList.toggle('good',s.running&&!pending);
 byId('mode').textContent=s.running?(labels[s.mode]||labels.unknown):'服务未运行';
 byId('node').textContent=s.mode==='direct'?'直连中 · 代理节点待用':'节点：'+(s.node||'--');
 modeButtons.forEach(b=>{b.classList.toggle('active',s.running&&b.dataset.mode===s.mode);b.setAttribute('aria-pressed',String(s.running&&b.dataset.mode===s.mode));});
 renderNodes(s);
 controls().forEach(b=>b.disabled=busy||!s.running||!s.managed);
 byId('test-nodes').disabled=busy||!s.running||!s.managed||!s.nodes?.length;
 byId('test-nodes').textContent=pending&&op.action==='test'?'测试中…':'测试全部';
 if(pending)message(op.action==='test'?'正在测试节点 HTTPS 延迟…':op.action==='node'?'正在切换到 '+op.label+'…':'正在切换到'+(labels[op.target]||'新模式')+'…');
 else if(op.state==='failed'||op.state==='interrupted')message(op.error||'操作未完成',true);
 else if(!s.managed)message('当前配置未接入屏幕控制，请使用管理页操作',true);
 else if(!s.running)message('请先在 OpenClash 管理页启动服务',true);
 else if(refreshFailed){message('状态连接已恢复');refreshFailed=false;}
 else if(op.state==='done'&&op.id!==lastOperation){
  message(op.action==='test'?'测试完成：'+op.passed+'/'+op.tested+' 可用':op.action==='node'?(s.mode==='direct'?'节点已保存，当前仍为直连模式':'已切换节点：'+op.node):'已切换并保存：'+labels[s.mode]);lastOperation=op.id;
 }
}
async function refresh(){
 if(reading)return;reading=true;
 try{const s=await e5.api('/status');if(!s.ok)throw new Error(s.error||'状态读取失败');render(s);}
 catch(e){refreshFailed=true;busy=false;e5.keepAwake(false);byId('service').textContent='连接中断';byId('service').classList.remove('good');controls().forEach(b=>b.disabled=true);message('状态暂不可用，正在重新连接…',true);}
 finally{reading=false;clearTimeout(timer);timer=setTimeout(refresh,busy?900:5000);}
}
async function submit(path,body,text){
 if(busy||!lastStatus?.running||!lastStatus?.managed)return;
 submitting=true;busy=true;controls().forEach(b=>b.disabled=true);message(text);e5.keepAwake(true);
 try{const r=await e5.api(path,{body});if(!r.ok)throw new Error(r.error||'操作失败');if(r.unchanged)message('当前已使用此设置');}
 catch(e){message(e.message||'请求未完成，请刷新实际状态',true);}
 finally{submitting=false;await refresh();}
}
modeButtons.forEach(b=>b.addEventListener('click',()=>{focusKey=b.dataset.control;submit('/mode',{mode:b.dataset.mode},'正在提交'+labels[b.dataset.mode]+'…');}));
byId('test-nodes').addEventListener('click',()=>{focusKey='test';submit('/test',{},'正在启动延迟测试…');});
e5.onKey(k=>{
 const list=controls();let i=list.findIndex(b=>b.dataset.control===focusKey);if(i<0)i=2;
 if(['left','right','up','down'].includes(k.kind)){
  if(!busy){
   let next;
   if(i<4){next=k.kind==='left'||k.kind==='right'?(i%2===0?i+1:i-1):k.kind==='up'?(i>=2?i-2:list.length-1):(i<2?i+2:4);}
   else next=k.kind==='up'||k.kind==='left'?(i===4?2:i-1):i+1;
   focusControl(next);
  }return true;
 }
 if(k.kind==='ok'){if(!busy)e5.press(list[i]);return true;}
 return false;
});
document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh();});
window.addEventListener('pagehide',()=>{clearTimeout(timer);e5.keepAwake(false);});
modeButtons.forEach(b=>b.disabled=true);byId('test-nodes').disabled=true;refresh();
