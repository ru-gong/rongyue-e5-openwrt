package cn.e5.switchui;

/** UI boundary. Implementation must be reviewed against the frozen root-worker protocol. */
public interface SwitchBackend {
    final class Status {
        public final String state, phase, message;
        public final long elapsedSeconds;
        public Status(String state, String phase, String message, long elapsedSeconds) {
            this.state=state; this.phase=phase; this.message=message; this.elapsedSeconds=elapsedSeconds;
        }
    }
    boolean connected();
    Status status();
    Status start();

    /** Review APK cannot start any root process, access /data/adb, mount, or reboot. */
    final class Unavailable implements SwitchBackend {
        public boolean connected() { return false; }
        public Status status() { return new Status("UNAVAILABLE", "NOT_CONNECTED",
            "切换服务尚未接入。本版仅供界面审查，不会执行切换。", 0); }
        public Status start() { return status(); }
    }
}
