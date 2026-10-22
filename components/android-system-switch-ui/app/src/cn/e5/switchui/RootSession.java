package cn.e5.switchui;

import org.json.JSONObject;
import org.json.JSONTokener;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

/** Only three immutable API commands. Root worker is NOT this process's child job owner. */
public final class RootSession {
    public static final String BACKEND_SHA256="1afeab4d8aa34c2cd6dd0679663fe52edd8a45b732b314c00a55ea77f9cb2fa2";
    public interface Listener { void changed(BackendStatus value); }
    private final Listener listener;
    private BackendStatus latest=BackendStatus.local("UNKNOWN","请先连接切换服务。",null);
    private String boot="";
    private boolean connected,submitted,reading,closed;
    private Process stream;
    public RootSession(Listener listener){this.listener=listener;}
    public synchronized BackendStatus snapshot(){return latest;}
    public synchronized boolean mayStart(){return connected&&!reading&&!submitted&&"IDLE".equals(latest.state);}
    public synchronized boolean wasSubmitted(){return submitted||!latest.runId.isEmpty();}
    public synchronized void connect(){
        if(closed||reading)return;
        reading=true;
        publish(BackendStatus.local("UNKNOWN","正在连接服务；如出现 Magisk 授权提示，请确认本应用。",latest));
        new Thread(()->readStream(),"e5-status-stream").start();
    }
    public synchronized void start(){
        if(!mayStart())return;
        submitted=true;reading=true;
        publish(BackendStatus.local("UNKNOWN","请求已发出，正在确认任务状态。请勿手动重启或再次提交。",latest));
        new Thread(()->{
            try {
                Process p=open("start");
                String line=readLine(p.getInputStream());
                if(line==null)throw new IOException("empty start reply");
                BackendStatus value=parse(line);
                if(readLine(p.getInputStream())!=null)throw new IOException("multiple start replies");
                int rc=p.waitFor();
                if(rc!=0&&!("UNKNOWN".equals(value.state)||"REFUSED".equals(value.state)||"FAILED".equals(value.state)))throw new IOException("start exit");
                accept(value);
            } catch(Exception e){unknown("提交结果暂时无法确认。请保持开机；仅重新读取状态，不会再次提交。");}
            // Querying the same fixed read-only stream cannot submit another job.
            synchronized(RootSession.this){reading=false;}
            connect();
        },"e5-confirmed-start").start();
    }
    private static String command(String mode){
        if(!Arrays.asList("start","status","stream").contains(mode))throw new IllegalArgumentException("mode");
        String path="/data/adb/modules/e5_local_system_switch/ui-backend.sh";
        // Every token is compiled in. No Intent, status field, path or text reaches this command.
        return "BB=/data/adb/magisk/busybox; P="+path+"; "
            +"[ -f \"$P\" ] && [ ! -L \"$P\" ] && "
            +"[ \"$(\"$BB\" sha256sum \"$P\" | \"$BB\" cut -d ' ' -f1)\" = "+BACKEND_SHA256+" ] || exit 70; "
            +"exec \"$BB\" sh \"$P\" "+mode;
    }
    private Process open(String mode)throws IOException{
        throw new IOException("Reference-only export: device execution is disabled.");
    }
    /** Preserved for review only; no call site reaches this implementation. */
    private Process referenceOpenNeverCalled(String mode)throws IOException{
        Process p=new ProcessBuilder("/debug_ramdisk/su","-c",command(mode)).start();
        p.getOutputStream().close();
        // Drain stderr independently without persisting or interpreting it as protocol.
        Thread errors=new Thread(()->{try(InputStream in=p.getErrorStream()){byte[] b=new byte[1024];while(in.read(b)!=-1){}}catch(IOException ignored){}},"e5-root-stderr");
        errors.setDaemon(true);errors.start();return p;
    }
    private void readStream(){
        BackendStatus last=null;
        Process p=null;
        try {
            p=open("stream"); synchronized(this){if(closed){p.destroy();return;}stream=p;}
            String line;
            while((line=readLine(p.getInputStream()))!=null){last=parse(line);accept(last);}
            int rc=p.waitFor();
            if(rc!=0||last==null||last.running())throw new IOException("stream ended without terminal snapshot");
        }catch(Exception e){
            synchronized(this){if(!closed)unknown("状态连接已中断或授权未完成。请保持开机；可重新读取状态，不要重复提交。");}
        }finally{
            if(p!=null)p.destroy(); // Only the read-only observer, never the worker/start process.
            synchronized(this){stream=null;reading=false;if(!closed)publish(latest);}
        }
    }
    private synchronized void accept(BackendStatus s)throws IOException{
        if(closed)return;
        if(!boot.isEmpty()&&!boot.equals(s.bootId))throw new IOException("boot changed");
        if((submitted||!latest.runId.isEmpty())&&"IDLE".equals(s.state))throw new IOException("unexpected idle after submission");
        if(!latest.runId.isEmpty()&&latest.runId.equals(s.runId)&&s.elapsed<latest.elapsed)throw new IOException("elapsed regressed");
        boot=s.bootId;connected=true;if(!s.runId.isEmpty())submitted=true;publish(s);
    }
    private synchronized void unknown(String message){connected=false;publish(BackendStatus.local("UNKNOWN",message,latest));}
    private synchronized void publish(BackendStatus s){latest=s;listener.changed(s);}
    public synchronized void close(){closed=true;if(stream!=null)stream.destroy();}
    public synchronized void stale(){if(latest.running()){unknown("状态更新已中断。请保持开机，重新读取状态；不要重复提交。");if(stream!=null)stream.destroy();}}
    static String readLine(InputStream in)throws IOException{
        ByteArrayOutputStream out=new ByteArrayOutputStream();int b;
        while((b=in.read())!=-1){if(b==10)return new String(out.toByteArray(),StandardCharsets.UTF_8);if(out.size()>=8192)throw new IOException("line too large");out.write(b);}
        if(out.size()!=0)throw new IOException("incomplete line");return null;
    }
    static BackendStatus parse(String line)throws Exception{
        JSONTokener tokener=new JSONTokener(line);Object parsed=tokener.nextValue();
        if(!(parsed instanceof JSONObject)||tokener.nextClean()!=0)throw new IOException("JSON frame");
        for(String key:Arrays.asList("schema","boot_id","run_id","state","phase","message","elapsed_seconds","exit_code")) {
            java.util.regex.Matcher m=java.util.regex.Pattern.compile("\""+key+"\"\\s*:").matcher(line);
            int count=0;while(m.find())count++;if(count!=1)throw new IOException("duplicate/missing key");
        }
        JSONObject json=(JSONObject)parsed;Map<String,Object> map=new HashMap<>();
        Iterator<String> keys=json.keys();while(keys.hasNext()){String k=keys.next();Object v=json.get(k);map.put(k,v==JSONObject.NULL?null:v);}
        return BackendStatus.parse(map);
    }
}
