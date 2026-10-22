# Screenshot provenance / 截图来源

These are captures of the project device's interfaces. They are not renders or
generated mock-ups. Screenshots show a particular moment; they are not evidence
of continuous connectivity, throughput or successful completion of a switch.

这些图片来自项目设备的实际界面，不是生成的效果图。截图仅记录拍摄时的状态，
不能单独证明持续联网、吞吐量或系统切换已经完成。

## OpenWrt screen / OpenWrt 机身屏幕

The existing overview, signal, OpenClash, traffic and system-control captures
were prepared on 20 October 2026 from the deployed screen web service at the
panel's 320 × 480 resolution. The two presentation sheets combine these captures;
scrolling content is stitched and the adjustment detail is cropped from the
OpenClash controls. The displayed latency values are earlier manual test results.

原有概览、信号、OpenClash、流量与系统控制截图于 2026 年 10 月 20 日从已部署的
屏幕网页服务采集，面板分辨率为 320 × 480。两张展示拼图由这些截图组合，滚动内容
经过拼接，调整区域为 OpenClash 控件裁切。图中的延迟是此前手动测试记录。
它们记录的是当时的屏幕布局，不是 TF 迁移后的再次采集。

## Android return controls / Android 返回入口

| File / 文件 | Captured / 采集日期 | Content / 内容 |
| --- | --- | --- |
| [e5-android-power-menu.png](e5-android-power-menu.png) | 2026-10-22 | Native power menu with the added return-to-OpenWrt card / 原电源菜单与附加返回入口 |
| [e5-android-switch-progress.png](e5-android-switch-progress.png) | 2026-10-22 | Same background task after leaving and reopening the app, at 54 seconds / 返回桌面后重新打开，同一任务已运行 54 秒 |

Both Android images are unmodified 320 × 480 device captures, visually reviewed
before publication. Their PNG chunks contain no embedded text or EXIF metadata.
The progress image is an intermediate state. The completed automatic return and
subsequent checks are described in [validation](../validation.md).

两张 Android 图片均为未经修改的 320 × 480 实机截图，发布前已检查可见内容；
PNG 不含嵌入文本或 EXIF 元数据。进度图属于执行中状态；自动返回完成后的核对结果
见[验证记录](../validation.md)。

| File | SHA-256 |
| --- | --- |
| e5-android-power-menu.png | `34197729874e2f91c505c367c6b642897637710453cfde7617c5eb6009e37c0b` |
| e5-android-switch-progress.png | `2625e5cd8900d1c91dde412e7be3371ee1231e29e343203069a7e07ee2378012` |
