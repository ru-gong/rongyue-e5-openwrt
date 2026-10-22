package cn.e5.switchui;

/** Immutable profile from saved actual E5 observer/event captures (2026-10-22).
 * AccessibilityWindowInfo title is genuinely empty; dumpsys ActionsDialog is NOT its title.
 */
public final class VerifiedPowerMenu {
    public static final MenuMatcher.Profile PROFILE = new MenuMatcher.Profile(
        true, "com.android.systemui.globalactions.GlobalActionsDialogLite$ActionsDialogLite",
        "手机选项", "", "com.android.systemui:id/global_actions_view", "android:id/message");
    private VerifiedPowerMenu() {}
}
