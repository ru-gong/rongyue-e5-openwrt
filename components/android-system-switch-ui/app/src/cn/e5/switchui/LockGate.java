package cn.e5.switchui;
import android.app.KeyguardManager;
import android.content.Context;
public final class LockGate {
    private LockGate() {}
    public static boolean locked(Context context) {
        try {
            KeyguardManager manager=context.getSystemService(KeyguardManager.class);
            return manager == null || manager.isDeviceLocked() || manager.isKeyguardLocked();
        } catch (RuntimeException e) { return true; }
    }
}
