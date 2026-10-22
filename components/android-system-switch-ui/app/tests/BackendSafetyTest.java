package cn.e5.switchui;
import java.util.*;
import java.io.*;
import java.lang.reflect.*;
public final class BackendSafetyTest {
 static int count; static String boot="00000000-0000-4000-8000-000000000001";
 static void check(boolean b,String s){if(!b)throw new AssertionError(s);count++;}
 static Map<String,Object> valid(){Map<String,Object> m=new HashMap<>();m.put("schema","e5-switch-ui-v1");m.put("boot_id",boot);m.put("run_id","");m.put("state","IDLE");m.put("phase","IDLE");m.put("message","准备就绪");m.put("elapsed_seconds",0);m.put("exit_code",null);return m;}
 static void rejected(Map<String,Object> m,String label){try{BackendStatus.parse(m);throw new AssertionError(label);}catch(IllegalArgumentException good){count++;}}
 public static void main(String[] args)throws Exception{
  BackendStatus idle=BackendStatus.parse(valid());check(idle.state.equals("IDLE"),"valid idle");
  String[] keys={"schema","boot_id","run_id","state","phase","message","elapsed_seconds","exit_code"};
  for(String k:keys){Map<String,Object> m=valid();m.remove(k);rejected(m,"missing "+k);}
  Map<String,Object> m=valid();m.put("unexpected",true);rejected(m,"unknown field");
  m=valid();m.put("state","SUCCESS");rejected(m,"not TF success");
  m=valid();m.put("boot_id","bad");rejected(m,"invalid boot");
  m=valid();m.put("run_id","another-1");rejected(m,"wrong run");
  m=valid();m.put("elapsed_seconds",-1);rejected(m,"negative time");
  m=valid();m.put("elapsed_seconds",1.0);rejected(m,"float time");
  m=valid();m.put("message","bad\nmessage");rejected(m,"newline");
  m=valid();m.put("exit_code",0);rejected(m,"idle with worker exit");
  m=valid();m.put("state","RUNNING");m.put("phase","ANDROID_VERIFY");rejected(m,"running without run");
  m.put("run_id",boot+"-1");m.put("elapsed_seconds",142);BackendStatus running=BackendStatus.parse(m);check(running.running(),"valid running");
  m.put("state","REBOOTING");m.put("phase","REBOOT");check(BackendStatus.parse(m).running(),"rebooting remains pending");
  m.put("exit_code",0);rejected(m,"rebooting with exit zero");
  m.put("state","FAILED");m.put("exit_code",1);check(!BackendStatus.parse(m).running(),"failed terminal");
  Method command=RootSession.class.getDeclaredMethod("command",String.class);command.setAccessible(true);
  for(String mode:Arrays.asList("start","status","stream")){String c=(String)command.invoke(null,mode);check(c.endsWith(" "+mode)&&c.contains(RootSession.BACKEND_SHA256),"fixed command "+mode);}
  for(String mode:Arrays.asList("start; reboot","--help","stream /data","reboot","",null)){
   try{command.invoke(null,mode);throw new AssertionError("bad command accepted");}catch(InvocationTargetException good){check(good.getCause() instanceof IllegalArgumentException,"mode rejected");}
  }
  check("abc".equals(RootSession.readLine(new ByteArrayInputStream("abc\n".getBytes("UTF-8")))),"bounded line");
  try{RootSession.readLine(new ByteArrayInputStream("abc".getBytes("UTF-8")));throw new AssertionError("partial");}catch(IOException good){count++;}
  byte[] huge=new byte[8194];Arrays.fill(huge,(byte)'a');huge[8193]=10;
  try{RootSession.readLine(new ByteArrayInputStream(huge));throw new AssertionError("oversize");}catch(IOException good){count++;}
  RootSession session=new RootSession(s->{});Method accept=RootSession.class.getDeclaredMethod("accept",BackendStatus.class);accept.setAccessible(true);
  accept.invoke(session,idle);check(session.mayStart(),"read-only fresh idle allows confirmation");
  accept.invoke(session,running);check(!session.mayStart()&&session.wasSubmitted(),"active forbids duplicate start");
  try{accept.invoke(session,idle);throw new AssertionError("idle regression");}catch(InvocationTargetException good){check(good.getCause() instanceof IOException,"idle after active rejected");}
  Map<String,Object> changed=valid();changed.put("boot_id","00000000-0000-4000-8000-000000000002");
  try{accept.invoke(session,BackendStatus.parse(changed));throw new AssertionError("boot change");}catch(InvocationTargetException good){check(good.getCause() instanceof IOException,"boot changed rejected");}
  check(!BackendStatus.local("UNKNOWN","断流",running).state.equals("SUCCESS"),"disconnect never success");
  Method open=RootSession.class.getDeclaredMethod("open",String.class);open.setAccessible(true);
  for(String mode:Arrays.asList("start","status","stream")){
   try{open.invoke(session,mode);throw new AssertionError("public root execution allowed");}
   catch(InvocationTargetException good){check(good.getCause() instanceof IOException&&good.getCause().getMessage().contains("Reference-only"),"public root entry refused "+mode);}
  }
  System.out.println("PASS "+count+" host-only backend protocol/command safety cases; no process started");
 }
}
