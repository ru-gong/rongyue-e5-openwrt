package cn.e5.switchui;

import android.accessibilityservice.AccessibilityService;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.PixelFormat;
import android.graphics.drawable.GradientDrawable;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.view.Gravity;
import android.view.View;
import android.view.WindowManager;
import android.view.accessibility.AccessibilityEvent;
import android.view.accessibility.AccessibilityNodeInfo;
import android.view.accessibility.AccessibilityWindowInfo;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;
import java.util.ArrayList;
import java.util.List;

/** Displays an additional entry. Never clicks a SystemUI node and never starts the backend. */
public final class PowerMenuService extends AccessibilityService {
    private final MenuDiagnostic diagnostic=new MenuDiagnostic();
    private final Handler handler = new Handler(Looper.getMainLooper());
    private View overlay;
    private int menuWindow = -1, dismissedWindow = -1;
    private boolean navigating;
    private int navigationGeneration;
    private final Runnable visibilityCheck = new Runnable() {
        public void run() {
            int id = menuWindow;
            if (id < 0) return;
            if (LockGate.locked(PowerMenuService.this) || !verifiedWindow(id)) {
                hide(); menuWindow=-1; dismissedWindow=-1;
            } else {
                handler.postDelayed(this, 600);
            }
        }
    };

    @Override public void onAccessibilityEvent(AccessibilityEvent event) {
        if (LockGate.locked(this)) { onInterrupt(); return; }
        if (navigating) return;
        MenuMatcher.Profile p=VerifiedPowerMenu.PROFILE;
        if (!p.configured()) { diagnostic.observe(this,event); return; }
        if (!p.configured() || event == null
                || event.getEventType() != AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED || !event.isFullScreen()
                || !MenuMatcher.SYSTEM_UI.contentEquals(string(event.getPackageName()))
                || !p.eventClass.equals(string(event.getClassName()))) return;
        int id=event.getWindowId();
        if (id < 0) return;
        List<String> title=new ArrayList<>();
        for (CharSequence s:event.getText()) {
            if (s == null || s.length() > 128) return;
            title.add(s.toString());
        }
        if (!MenuMatcher.eventMatches(p, string(event.getPackageName()),
                string(event.getClassName()), title)) return;
        // Exact saved event first. Empty window title is not sufficient by itself.
        if(!verifiedWindow(id))return;
        if (menuWindow != id) { hide(); dismissedWindow=-1; }
        menuWindow=id;
        handler.removeCallbacks(visibilityCheck);
        handler.postDelayed(visibilityCheck, 600);
        if (dismissedWindow != id && overlay == null) showEntry();
    }

    private boolean verifiedWindow(int wanted) {
        List<AccessibilityWindowInfo> windows=getWindows();
        if (windows == null) return false;
        try {
            for (AccessibilityWindowInfo w:windows) {
                if (w.getId() != wanted) continue; // Never request another window's root.
                if (!w.isActive() || !w.isFocused() || !MenuMatcher.windowMatches(VerifiedPowerMenu.PROFILE,
                        w.getType()==AccessibilityWindowInfo.TYPE_SYSTEM, string(w.getTitle()))) return false;
                AccessibilityNodeInfo root=w.getRoot();
                if (root == null) return false;
                try {
                    if (!MenuMatcher.SYSTEM_UI.equals(string(root.getPackageName()))) return false;
                    List<MenuMatcher.Item> items=new ArrayList<>();
                    return collect(root, items, 0, false) && MenuMatcher.contentsMatch(
                        VerifiedPowerMenu.PROFILE, string(root.getPackageName()), items);
                } finally { root.recycle(); }
            }
            return false;
        } catch (RuntimeException e) {
            return false;
        } finally {
            for (AccessibilityWindowInfo w:windows) w.recycle();
        }
    }

    private boolean collect(AccessibilityNodeInfo node, List<MenuMatcher.Item> items, int depth, boolean inside) {
        if (depth > 24 || items.size() >= 128) return false;
        String pkg=string(node.getPackageName());
        if (!MenuMatcher.SYSTEM_UI.equals(pkg)) return false;
        String id=node.getViewIdResourceName();
        MenuMatcher.Profile p=VerifiedPowerMenu.PROFILE;
        if(p.anchorId.equals(id) && node.isVisibleToUser() && node.isEnabled())inside=true;
        String label="";
        // Read text only from the two pinned menu labels, never arbitrary node content.
        if (inside && p.labelId.equals(id)) label=string(node.getText());
        items.add(new MenuMatcher.Item(pkg,id,label,node.isVisibleToUser(),node.isEnabled(),inside));
        if (node.getChildCount() > 128) return false;
        for (int i=0;i<node.getChildCount();i++) {
            AccessibilityNodeInfo child=node.getChild(i);
            if (child == null) return false;
            try { if (!collect(child,items,depth+1,inside)) return false; }
            finally { child.recycle(); }
        }
        return true;
    }

    private void showEntry() {
        LinearLayout box=new LinearLayout(this);
        box.setOrientation(LinearLayout.HORIZONTAL);
        box.setPadding(dp(5),dp(5),dp(5),dp(5));
        GradientDrawable background=new GradientDrawable();
        background.setColor(Color.rgb(245,250,247)); background.setCornerRadius(dp(12));
        background.setStroke(dp(1),Color.rgb(23,107,82)); box.setBackground(background);
        Button open=new Button(this); open.setText("返回 OpenWrt\n设为默认系统"); open.setTextSize(14);
        open.setAllCaps(false);open.setFilterTouchesWhenObscured(true);
        box.addView(open,new LinearLayout.LayoutParams(0,-1,1));
        Button dismiss=new Button(this); dismiss.setText("×");dismiss.setTextSize(20);
        dismiss.setContentDescription("留在 Android，关闭附加入口");
        box.addView(dismiss,new LinearLayout.LayoutParams(dp(44),-1));
        dismiss.setOnClickListener(v -> { dismissedWindow=menuWindow; hide(); });
        open.setOnClickListener(v -> {
            if (navigating || LockGate.locked(this) || !verifiedWindow(menuWindow)) { hide(); return; }
            // Sole global action: explicit click, freshly verified foreground power menu.
            // Android exposes no atomic window-targeted BACK; do not retry if it fails.
            final int target=menuWindow;
            navigating=true; final int generation=++navigationGeneration;
            dismissedWindow=target; hide(); handler.removeCallbacks(visibilityCheck);
            if (!performGlobalAction(GLOBAL_ACTION_BACK)) { navigationFailed(); return; }
            awaitMenuGone(target,generation,SystemClock.uptimeMillis()+1500);
        });
        WindowManager.LayoutParams lp=new WindowManager.LayoutParams(
            Math.min(dp(328),getResources().getDisplayMetrics().widthPixels-dp(24)),
            dp(72),
            WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE | WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL,
            PixelFormat.TRANSLUCENT);
        // At the saved density 140, 72dp is 63px; below the original menu's y=381 bottom.
        lp.gravity=Gravity.BOTTOM|Gravity.CENTER_HORIZONTAL; lp.y=dp(8);
        lp.setTitle("E5 OpenWrt return entry");
        try { ((WindowManager)getSystemService(WINDOW_SERVICE)).addView(box,lp); overlay=box; }
        catch (RuntimeException e) { overlay=null; }
    }
    private static String string(CharSequence s) { return s == null ? "" : s.toString(); }
    private void awaitMenuGone(int target,int generation,long deadline) {
        if (!navigating || generation!=navigationGeneration) return;
        if (LockGate.locked(this) || SystemClock.uptimeMillis()>=deadline) { navigationFailed(); return; }
        List<AccessibilityWindowInfo> windows=getWindows();
        if (windows==null) { navigationFailed(); return; }
        boolean present=false;
        try { for(AccessibilityWindowInfo w:windows)if(w.getId()==target)present=true; }
        finally { for(AccessibilityWindowInfo w:windows)w.recycle(); }
        if(present) {
            handler.postDelayed(()->awaitMenuGone(target,generation,deadline),100);return;
        }
        navigating=false; menuWindow=-1; dismissedWindow=-1;
        if(LockGate.locked(this))return;
        // Only opens a confirmation page. No root/backend call is reachable here.
        Intent intent=new Intent(this,MainActivity.class);
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK|Intent.FLAG_ACTIVITY_SINGLE_TOP);
        try { startActivity(intent); }
        catch(RuntimeException e) { Toast.makeText(this,"请从桌面打开返回 OpenWrt 页面。",Toast.LENGTH_SHORT).show(); }
    }
    private void navigationFailed() {
        navigating=false; navigationGeneration++;menuWindow=-1;
        Toast.makeText(this,"电源菜单尚未关闭；请关闭菜单后从桌面打开。",Toast.LENGTH_SHORT).show();
    }
    private int dp(int n) { return Math.round(n*getResources().getDisplayMetrics().density); }
    private void hide() {
        if (overlay != null) {
            try { ((WindowManager)getSystemService(WINDOW_SERVICE)).removeView(overlay); }
            catch (RuntimeException ignored) { }
            overlay=null;
        }
    }
    @Override public void onInterrupt() { handler.removeCallbacksAndMessages(null); hide(); menuWindow=-1; navigating=false;navigationGeneration++; }
    @Override public void onDestroy() { onInterrupt(); super.onDestroy(); }
}
