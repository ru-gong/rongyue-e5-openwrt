package cn.e5.switchui;
import java.util.*;

/** Strict, bounded protocol data. IDs are diagnostics, never shell arguments. */
public final class BackendStatus {
    public final String bootId,runId,state,phase,message;
    public final long elapsed;
    public final Integer exitCode;
    private static final Set<String> KEYS=new HashSet<>(Arrays.asList("schema","boot_id","run_id","state","phase","message","elapsed_seconds","exit_code"));
    private static final Set<String> STATES=new HashSet<>(Arrays.asList("IDLE","RUNNING","REFUSED","FAILED","REBOOTING","UNKNOWN"));
    private static final Set<String> PHASES=new HashSet<>(Arrays.asList("IDLE","STARTING","IDENTITY","ANDROID_VERIFY","BOOT_VERIFY","TF_READONLY","CONTROL_BACKUP","TF_REQUEST","TF_READBACK","ARM","REBOOT","FINISHED","UNKNOWN"));
    private BackendStatus(String boot,String run,String state,String phase,String message,long elapsed,Integer code) {
        bootId=boot;runId=run;this.state=state;this.phase=phase;this.message=message;this.elapsed=elapsed;exitCode=code;
    }
    private static String string(Map<String,Object> m,String k) {
        Object v=m.get(k);if(!(v instanceof String))throw new IllegalArgumentException("invalid "+k);return (String)v;
    }
    public static BackendStatus parse(Map<String,Object> m) {
        if(!m.keySet().equals(KEYS)||!"e5-switch-ui-v1".equals(string(m,"schema")))throw new IllegalArgumentException("schema");
        String boot=string(m,"boot_id"),run=string(m,"run_id"),state=string(m,"state"),phase=string(m,"phase"),message=string(m,"message");
        if(!boot.matches("[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
                ||(!run.isEmpty()&&!run.equals(boot+"-1"))||!STATES.contains(state)||!PHASES.contains(phase))throw new IllegalArgumentException("identity/state");
        if(message.length()>512||message.isEmpty())throw new IllegalArgumentException("message");
        for(int i=0;i<message.length();i++)if(message.charAt(i)<32)throw new IllegalArgumentException("control character");
        Object seconds=m.get("elapsed_seconds"),code=m.get("exit_code");
        if(!(seconds instanceof Integer||seconds instanceof Long))throw new IllegalArgumentException("elapsed type");
        long elapsed=((Number)seconds).longValue();if(elapsed<0||elapsed>86400)throw new IllegalArgumentException("elapsed range");
        Integer exit=null;
        if(code!=null) {
            if(!(code instanceof Integer||code instanceof Long)||((Number)code).longValue()<0||((Number)code).longValue()>255)throw new IllegalArgumentException("exit code");
            exit=((Number)code).intValue();
        }
        if("IDLE".equals(state)&&(!run.isEmpty()||!"IDLE".equals(phase)||elapsed!=0||exit!=null))throw new IllegalArgumentException("idle");
        if(("RUNNING".equals(state)||"REBOOTING".equals(state))&&(run.isEmpty()||exit!=null))throw new IllegalArgumentException("active");
        return new BackendStatus(boot,run,state,phase,message,elapsed,exit);
    }
    public static BackendStatus local(String state,String message,BackendStatus previous) {
        return new BackendStatus(previous==null?"":previous.bootId,previous==null?"":previous.runId,state,
            previous==null?"UNKNOWN":previous.phase,message,previous==null?0:previous.elapsed,previous==null?null:previous.exitCode);
    }
    public boolean running() { return "RUNNING".equals(state)||"REBOOTING".equals(state); }
    public String diagnostic() { return "状态："+state+"\n阶段："+phase+"\n任务："+(runId.isEmpty()?"未提交":runId)+"\n退出码："+(exitCode==null?"未返回":exitCode)+"\n"+message; }
}
