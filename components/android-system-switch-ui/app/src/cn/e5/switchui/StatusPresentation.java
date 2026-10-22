package cn.e5.switchui;

/** Unknown/transport failure is not success and never authorizes an automatic retry. */
public final class StatusPresentation {
    private StatusPresentation() {}
    public static String title(String state) {
        if ("IDLE".equals(state)) return "可以开始";
        if ("RUNNING".equals(state)) return "正在检查并准备切换";
        if ("REBOOTING".equals(state)) return "正在重启，请保持供电";
        if ("REFUSED".equals(state)) return "尚未开始切换";
        if ("FAILED".equals(state)) return "切换未完成";
        if ("UNAVAILABLE".equals(state)) return "切换服务尚未接入";
        return "状态暂时无法确认";
    }
    public static String phase(String phase) {
        switch (phase) {
            case "IDLE": return "等待确认";
            case "STARTING": return "正在启动校验";
            case "IDENTITY": return "核对设备与启动状态";
            case "ANDROID_VERIFY": return "校验 Android 保护分区";
            case "BOOT_VERIFY": return "校验 OpenWrt 启动镜像";
            case "TF_READONLY": return "只读校验 TF 卡和系统文件";
            case "CONTROL_BACKUP": return "保存切换前状态";
            case "TF_REQUEST": return "准备返回 OpenWrt 请求";
            case "TF_READBACK": return "复核 TF 卡切换标记";
            case "ARM": return "设置下一次启动";
            case "REBOOT": return "准备自动重启";
            case "FINISHED": return "校验流程已结束";
            default: return "等待状态确认";
        }
    }
    public static boolean mayStart(boolean connected, String state) {
        return connected && "IDLE".equals(state);
    }
    public static String elapsed(long seconds) {
        if (seconds < 0 || seconds > 86400) return "用时未知";
        return "已用时 " + (seconds / 60) + " 分 " + (seconds % 60) + " 秒";
    }
}
