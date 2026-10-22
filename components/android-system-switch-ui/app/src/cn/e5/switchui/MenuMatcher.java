package cn.e5.switchui;

import java.util.List;

/** Pure matcher: no Android calls, file access, text collection or action execution. */
public final class MenuMatcher {
    public static final String SYSTEM_UI = "com.android.systemui";
    public static final class Profile {
        public final boolean verified;
        public final String eventClass, title, windowTitle, anchorId, labelId;
        public Profile(boolean verified, String eventClass, String title, String windowTitle, String anchorId, String labelId) {
            this.verified = verified;
            this.eventClass = eventClass;
            this.title = title;
            this.windowTitle=windowTitle; this.anchorId=anchorId; this.labelId=labelId;
        }
        public boolean configured() {
            return verified && nonempty(eventClass) && nonempty(title) && windowTitle!=null
                && nonempty(anchorId) && anchorId.startsWith(SYSTEM_UI+":id/")
                && "android:id/message".equals(labelId);
        }
    }
    public static final class Item {
        public final String packageName, resourceId, label;
        public final boolean visible, enabled, insideAnchor;
        public Item(String packageName, String resourceId, String label, boolean visible, boolean enabled, boolean insideAnchor) {
            this.packageName=packageName; this.resourceId=resourceId; this.label=label;
            this.visible=visible; this.enabled=enabled; this.insideAnchor=insideAnchor;
        }
    }
    private MenuMatcher() {}
    private static boolean nonempty(String s) { return s != null && !s.isEmpty(); }
    public static boolean eventMatches(Profile p, String pkg, String cls, List<String> eventText) {
        return p.configured() && SYSTEM_UI.equals(pkg) && p.eventClass.equals(cls)
            && eventText != null && eventText.size() == 1 && p.title.equals(eventText.get(0));
    }
    public static boolean windowMatches(Profile p, boolean systemWindow, String title) {
        return p.configured() && systemWindow && p.windowTitle.equals(title);
    }
    public static boolean contentsMatch(Profile p, String rootPackage, List<Item> items) {
        if (!p.configured() || !SYSTEM_UI.equals(rootPackage) || items == null
                || items.isEmpty() || items.size() > 128) return false;
        int anchor=0, shutdown=0, restart=0, emergency=0;
        for (Item n : items) {
            // A foreign embedded window is never accepted as part of this menu.
            if (!SYSTEM_UI.equals(n.packageName)) return false;
            if (!n.visible || !n.enabled) continue;
            if(p.anchorId.equals(n.resourceId))anchor++;
            if(n.insideAnchor && p.labelId.equals(n.resourceId)) {
                if("关机".equals(n.label))shutdown++;
                else if("重启".equals(n.label))restart++;
                else if("紧急呼救".equals(n.label))emergency++;
                else return false;
            }
        }
        return anchor==1 && shutdown==1 && restart==1 && emergency==1;
    }
}
