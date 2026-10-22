package cn.e5.switchui;
import java.util.*;
public final class UiSafetyTest {
 private static int count;
 static void check(boolean b,String n){if(!b)throw new AssertionError(n);count++;}
 static MenuMatcher.Item item(String pkg,String id,String label,boolean inside){return new MenuMatcher.Item(pkg,id,label,true,true,inside);}
 public static void main(String[] args){
  String pkg=MenuMatcher.SYSTEM_UI; MenuMatcher.Profile p=VerifiedPowerMenu.PROFILE;
  MenuMatcher.Item anchor=item(pkg,p.anchorId,"",true),shutdown=item(pkg,p.labelId,"关机",true),restart=item(pkg,p.labelId,"重启",true),emergency=item(pkg,p.labelId,"紧急呼救",true);
  List<MenuMatcher.Item> good=Arrays.asList(anchor,shutdown,restart,emergency);
  check(p.configured()&&MenuMatcher.contentsMatch(p,pkg,good),"observed exact profile");
  check(MenuMatcher.windowMatches(p,true,""),"observed empty accessibility title");
  check(!MenuMatcher.windowMatches(p,true,"ActionsDialog"),"dumpsys title not substituted");
  check(!MenuMatcher.windowMatches(p,false,""),"non-system window");
  check(MenuMatcher.eventMatches(p,pkg,p.eventClass,Arrays.asList("手机选项")),"exact event");
  check(!MenuMatcher.eventMatches(p,"other",p.eventClass,Arrays.asList("手机选项")),"foreign event");
  check(!MenuMatcher.eventMatches(p,pkg,"other.Dialog",Arrays.asList("手机选项")),"wrong event class");
  check(!MenuMatcher.eventMatches(p,pkg,p.eventClass,Arrays.asList("通知")),"notification event");
  check(!MenuMatcher.eventMatches(p,pkg,p.eventClass,Arrays.asList("手机选项","extra")),"ambiguous event text");
  check(!MenuMatcher.contentsMatch(p,"other",good),"foreign root");
  check(!MenuMatcher.contentsMatch(p,pkg,Arrays.asList(shutdown,restart,emergency)),"missing anchor");
  check(!MenuMatcher.contentsMatch(p,pkg,Arrays.asList(anchor,shutdown,restart)),"missing emergency");
  check(!MenuMatcher.contentsMatch(p,pkg,Arrays.asList(anchor,anchor,shutdown,restart,emergency)),"duplicate anchor");
  check(!MenuMatcher.contentsMatch(p,pkg,Arrays.asList(anchor,shutdown,restart,restart,emergency)),"duplicate restart");
  check(!MenuMatcher.contentsMatch(p,pkg,Arrays.asList(anchor,shutdown,item("other",p.labelId,"重启",true),emergency)),"embedded foreign node");
  check(!MenuMatcher.contentsMatch(p,pkg,Arrays.asList(anchor,shutdown,item(pkg,p.labelId,"重启",false),emergency)),"label outside anchor");
  check(!MenuMatcher.contentsMatch(p,pkg,Arrays.asList(anchor,shutdown,restart,emergency,item(pkg,p.labelId,"新按钮",true))),"unknown message under anchor");
  check(!MenuMatcher.contentsMatch(p,pkg,Arrays.asList(anchor,shutdown,new MenuMatcher.Item(pkg,p.labelId,"重启",false,true,true),emergency)),"hidden label");
  check(!MenuMatcher.contentsMatch(p,pkg,Arrays.asList(anchor,shutdown,item(pkg,"wrong:id/restart","重启",true),emergency)),"text only spoof");
  check(!MenuMatcher.contentsMatch(p,pkg,Arrays.asList(anchor,shutdown,item(pkg,p.labelId,"Restart",true),emergency)),"unknown locale");
  List<MenuMatcher.Item> huge=new ArrayList<>();for(int i=0;i<129;i++)huge.add(anchor);
  check(!MenuMatcher.contentsMatch(p,pkg,huge),"huge tree");
  check(!StatusPresentation.mayStart(false,"IDLE"),"unconnected");
  check(!StatusPresentation.mayStart(true,"UNKNOWN"),"unknown cannot retry");
  check(!StatusPresentation.mayStart(true,"FAILED"),"failed cannot retry");
  check(!StatusPresentation.mayStart(true,"REBOOTING"),"rebooting cannot retry");
  check(!StatusPresentation.title("success").contains("成功"),"no unknown success");
  check(!new SwitchBackend.Unavailable().connected(),"inert review backend");
  System.out.println("PASS "+count+" host-only UI safety cases");
 }
}
