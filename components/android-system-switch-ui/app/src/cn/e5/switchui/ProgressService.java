package cn.e5.switchui;
import android.app.*;
import android.content.*;
import android.os.*;
import java.util.*;

/** Foreground status viewer only; destroying it never cancels the detached root worker. */
public final class ProgressService extends Service {
    public interface Observer{void changed(BackendStatus s);}
    public final class LocalBinder extends Binder{public ProgressService service(){return ProgressService.this;}}
    private final LocalBinder binder=new LocalBinder();
    private final Handler main=new Handler(Looper.getMainLooper());
    private final Set<Observer> observers=new HashSet<>();
    private RootSession session;
    private boolean foreground;
    private long receivedAt;
    private final Runnable health=new Runnable(){public void run(){
        if(session!=null&&session.snapshot().running()&&SystemClock.elapsedRealtime()-receivedAt>10000)session.stale();
        main.postDelayed(this,1000);
    }};
    @Override public void onCreate(){super.onCreate();session=new RootSession(s->main.post(()->{
        receivedAt=SystemClock.elapsedRealtime();
        for(Observer o:new ArrayList<>(observers))o.changed(s);
        if(foreground)((NotificationManager)getSystemService(NOTIFICATION_SERVICE)).notify(7,notification(s));
    }));receivedAt=SystemClock.elapsedRealtime();main.postDelayed(health,1000);}
    @Override public IBinder onBind(Intent i){return binder;}
    @Override public int onStartCommand(Intent i,int flags,int id){
        // Even an internal service start only shows status; it cannot submit root work.
        NotificationManager n=(NotificationManager)getSystemService(NOTIFICATION_SERVICE);
        n.createNotificationChannel(new NotificationChannel("status","OpenWrt 切换进度",NotificationManager.IMPORTANCE_LOW));
        startForeground(7,notification(session.snapshot()));foreground=true;return START_NOT_STICKY;
    }
    public void add(Observer o){observers.add(o);o.changed(session.snapshot());}
    public void remove(Observer o){observers.remove(o);}
    public void connect(){session.connect();}
    public boolean mayStart(){return !LockGate.locked(this)&&session.mayStart();}
    public void confirmedStart(){if(mayStart())session.start();}
    public boolean wasSubmitted(){return session.wasSubmitted();}
    public BackendStatus snapshot(){return session.snapshot();}
    public long elapsedForDisplay(){BackendStatus s=snapshot();return s.elapsed+(s.running()?Math.max(0,SystemClock.elapsedRealtime()-receivedAt)/1000:0);}
    private Notification notification(BackendStatus s){
        PendingIntent p=PendingIntent.getActivity(this,0,new Intent(this,MainActivity.class),PendingIntent.FLAG_IMMUTABLE|PendingIntent.FLAG_UPDATE_CURRENT);
        return new Notification.Builder(this,"status").setSmallIcon(android.R.drawable.ic_popup_sync)
            .setContentTitle(StatusPresentation.title(s.state)).setContentText("点击查看进度；请勿手动重启。")
            .setContentIntent(p).setOngoing(true).build();
    }
    @Override public void onDestroy(){if(session!=null)session.close();main.removeCallbacksAndMessages(null);observers.clear();super.onDestroy();}
}
