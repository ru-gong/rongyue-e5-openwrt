package cn.e5.switchui;

import android.accessibilityservice.AccessibilityService;
import android.util.Log;
import android.view.accessibility.AccessibilityEvent;
import android.view.accessibility.AccessibilityNodeInfo;
import android.view.accessibility.AccessibilityWindowInfo;
import java.util.List;
import org.json.JSONObject;

/** Temporary observer: exact saved power-menu event only. No overlay, root call or action. */
public final class MenuDiagnostic {
    public static final boolean ENABLED=false;
    private static final String EVENT_CLASS="com.android.systemui.globalactions.GlobalActionsDialogLite$ActionsDialogLite";
    private static final String ANCHOR="com.android.systemui:id/global_actions_view";
    private int observedWindow=-1;
    public void observe(AccessibilityService service, AccessibilityEvent event) {
        if (!ENABLED || LockGate.locked(service) || event == null
                || event.getEventType()!=AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED
                || !"com.android.systemui".contentEquals(str(event.getPackageName()))
                || !EVENT_CLASS.equals(str(event.getClassName())) || !event.isFullScreen()
                || event.getText().size()!=1 || !"手机选项".contentEquals(str(event.getText().get(0)))) return;
        int wanted=event.getWindowId();
        if (wanted<0 || wanted==observedWindow) return;
        List<AccessibilityWindowInfo> windows=service.getWindows();
        if (windows==null) return;
        try {
            for(AccessibilityWindowInfo window:windows) {
                if(window.getId()!=wanted) continue;
                JSONObject record=new JSONObject();
                record.put("kind","E5_POWER_MENU_PROFILE_OBSERVER_V1");
                record.put("event_exact",true);record.put("unlocked",true);
                record.put("window_id",wanted);record.put("window_type",window.getType());
                String title=str(window.getTitle());
                record.put("window_title",title.length()<=128?title:"[too-long]");
                record.put("window_active",window.isActive());record.put("window_focused",window.isFocused());
                AccessibilityNodeInfo root=window.getRoot();
                int[] counts=new int[6];
                boolean valid=false;
                if(root!=null) {
                    try { valid=scan(root,counts,0,false); }
                    finally { root.recycle(); }
                }
                record.put("tree_complete_systemui",valid);
                record.put("node_count",counts[0]);record.put("anchor_count",counts[1]);
                record.put("shutdown_count",counts[2]);record.put("restart_count",counts[3]);
                record.put("emergency_count",counts[4]);record.put("unknown_label_count",counts[5]);
                record.put("backend_enabled",false);record.put("overlay_enabled",false);
                Log.i("E5PowerMenuProfile",record.toString());
                observedWindow=wanted;
                return;
            }
        } catch(Exception e) {
            // Constant failure marker: exception text can contain unrelated window data.
            Log.i("E5PowerMenuProfile","PROFILE_READ_UNAVAILABLE");
        } finally { for(AccessibilityWindowInfo w:windows)w.recycle(); }
    }
    private boolean scan(AccessibilityNodeInfo n,int[] count,int depth,boolean inside) {
        if(depth>24 || count[0]>=128 || !"com.android.systemui".equals(str(n.getPackageName())))return false;
        count[0]++;
        if(ANCHOR.equals(n.getViewIdResourceName()) && n.isVisibleToUser() && n.isEnabled()) {
            count[1]++;inside=true;
        }
        if(inside && "android:id/message".equals(n.getViewIdResourceName()) && n.isVisibleToUser() && n.isEnabled()) {
            String label=str(n.getText());
            if("关机".equals(label))count[2]++;
            else if("重启".equals(label))count[3]++;
            else if("紧急呼救".equals(label))count[4]++;
            else count[5]++;
        }
        if(n.getChildCount()>128)return false;
        for(int i=0;i<n.getChildCount();i++) {
            AccessibilityNodeInfo c=n.getChild(i);if(c==null)return false;
            try { if(!scan(c,count,depth+1,inside))return false; }
            finally { c.recycle(); }
        }
        return true;
    }
    private static String str(CharSequence s) { return s==null?"":s.toString(); }
}
