package cn.e5.switchui;
import android.Manifest;
import android.app.*;
import android.content.*;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.os.*;
import android.provider.Settings;
import android.widget.*;

/** All external intents are display-only. A visible confirmation is the sole start path. */
public final class MainActivity extends Activity implements ProgressService.Observer {
 private ProgressService service;
 private TextView status,detail,time;
 private Button start,connect,leave;
 private boolean bound,confirmationOpen,visible;
 private AlertDialog confirmation;
 private final Handler main=new Handler(Looper.getMainLooper());
 private final Runnable tick=new Runnable(){public void run(){render();main.postDelayed(this,1000);}};
 private final ServiceConnection connection=new ServiceConnection(){
  public void onServiceConnected(ComponentName n,IBinder b){service=((ProgressService.LocalBinder)b).service();service.add(MainActivity.this);if(visible)connect();}
  public void onServiceDisconnected(ComponentName n){service=null;render();}
 };
 @Override public void onCreate(Bundle state){
  super.onCreate(state);
  ScrollView scroll=new ScrollView(this);LinearLayout body=new LinearLayout(this);
  body.setOrientation(LinearLayout.VERTICAL);body.setPadding(dp(20),dp(12),dp(20),dp(18));body.setBackgroundColor(Color.rgb(245,247,245));
  scroll.addView(body);setContentView(scroll);
  text(body,"E5 双系统",13,Color.rgb(70,90,78));text(body,"返回 OpenWrt",24,Color.rgb(17,47,33));
  text(body,"将重启到 OpenWrt，并设为默认系统。",15,Color.rgb(42,58,48));
  text(body,"校验可能需要数分钟；完成后自动重启，请勿手动重启。",15,Color.rgb(42,58,48));
  status=text(body,"",18,Color.rgb(23,107,82));detail=text(body,"",14,Color.rgb(45,55,49));detail.setTextIsSelectable(true);
  time=text(body,"",13,Color.rgb(72,82,76));
  connect=button(body,"连接 / 重新读取状态");connect.setOnClickListener(v->connect());
  start=button(body,"返回并设为默认");start.setOnClickListener(v->confirm());
  button(body,"复制当前状态").setOnClickListener(v->{
   String report=service==null?"状态服务未连接。":service.snapshot().diagnostic();
   ((ClipboardManager)getSystemService(CLIPBOARD_SERVICE)).setPrimaryClip(ClipData.newPlainText("E5 切换状态",report));
   Toast.makeText(this,"状态已复制",Toast.LENGTH_SHORT).show();
  });
  leave=button(body,"留在 Android");leave.setOnClickListener(v->finish());
  button(body,"电源菜单入口设置").setOnClickListener(v->new AlertDialog.Builder(this)
   .setTitle("电源菜单附加入口").setMessage("只识别已解锁的 SystemUI 电源菜单。不会读取其他应用或通知，不联网，不会自动切换；可在系统设置停用。")
   .setNegativeButton("取消",null).setPositiveButton("打开设置",(d,w)->startActivity(new Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))).show());
  text(body,"进度只显示真实阶段和已用时。任务启动后退出此页面不会取消；失败时请保持开机并复制状态，详细日志仅由维护工具读取。",12,Color.rgb(80,90,84));
  render();
 }
 @Override protected void onStart(){super.onStart();visible=true;bound=bindService(new Intent(this,ProgressService.class),connection,BIND_AUTO_CREATE);main.post(tick);}
 @Override protected void onStop(){
  visible=false;main.removeCallbacks(tick);if(confirmation!=null)confirmation.dismiss();confirmationOpen=false;
  if(service!=null)service.remove(this);if(bound)unbindService(connection);bound=false;service=null;super.onStop();
 }
 @Override protected void onNewIntent(Intent i){super.onNewIntent(i);/* Ignore action, URI and extras. */}
 @Override public void changed(BackendStatus s){render();}
 private void connect(){
  if(!visible||service==null||LockGate.locked(this))return;
  if(checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)!=PackageManager.PERMISSION_GRANTED)
   requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS},1);
  startForegroundService(new Intent(this,ProgressService.class));
  service.connect();
 }
 private void confirm(){
  if(confirmationOpen||service==null||LockGate.locked(this)||!service.mayStart())return;
  confirmationOpen=true;
  confirmation=new AlertDialog.Builder(this).setTitle("返回 OpenWrt 并设为默认？")
   .setMessage("将重启到 OpenWrt，并设为默认系统。\n\n校验可能需要数分钟；完成后自动重启，请勿手动重启。请保持供电，不要拔卡、不要重复点击。")
   .setNegativeButton("留在 Android",null).setPositiveButton("确认返回",(d,w)->{
    if(service!=null&&!LockGate.locked(this)&&service.mayStart())service.confirmedStart();
   }).create();
  confirmation.setOnShowListener(d->confirmation.getButton(AlertDialog.BUTTON_POSITIVE).setFilterTouchesWhenObscured(true));
  confirmation.setOnDismissListener(d->{confirmationOpen=false;confirmation=null;});confirmation.show();
 }
 private void render(){
  if(status==null)return;
  BackendStatus s=service==null?BackendStatus.local("UNKNOWN","正在连接切换服务；首次连接会请求 Magisk root 授权。",null):service.snapshot();
  boolean locked=LockGate.locked(this);
  status.setText(locked?"请先解锁设备":StatusPresentation.title(s.state));
  detail.setText(s.message+(s.runId.isEmpty()?"":"\n阶段："+StatusPresentation.phase(s.phase)));
  time.setText(s.runId.isEmpty()?"尚未提交切换任务":StatusPresentation.elapsed(service==null?s.elapsed:service.elapsedForDisplay()));
  start.setEnabled(!locked&&service!=null&&service.mayStart());connect.setEnabled(!locked&&service!=null);
  boolean submitted=service!=null&&service.wasSubmitted();
  leave.setText(submitted?(s.running()?"返回桌面（切换继续）":"返回桌面（请保持开机）"):"留在 Android");
  if(locked&&confirmation!=null)confirmation.dismiss();
 }
 private int dp(int n){return Math.round(n*getResources().getDisplayMetrics().density);}
 private TextView text(LinearLayout p,String s,int size,int color){TextView v=new TextView(this);v.setText(s);v.setTextSize(size);v.setTextColor(color);v.setPadding(0,dp(4),0,dp(5));p.addView(v);return v;}
 private Button button(LinearLayout p,String s){Button b=new Button(this);b.setText(s);b.setTextSize(15);b.setAllCaps(false);b.setFilterTouchesWhenObscured(true);p.addView(b,new LinearLayout.LayoutParams(-1,dp(48)));return b;}
}
