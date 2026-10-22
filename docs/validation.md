# 验证记录 / Validation

整理日期 / Updated: **2026-10-23**. 实机观察截至 / Device observations through **2026-10-22**.

本页区分当前 TF 部署、早期内部镜像方案和主机测试。私有原始日志、绑定、配置、短信及备份保留在仓库之外；下表是脱敏结论，不是其他设备的兼容保证。

This page separates the current TF deployment, the earlier internal-image layout, and host tests. Private raw logs, bindings, configuration, messages and backups are excluded. Results apply to the observed device and execution, not every E5.

## 当前 TF 部署 / Current TF deployment

| 项目 / Item | 已观察结果与边界 / Observation and scope |
| --- | --- |
| 版本 / Versions | OpenWrt 25.12.5; kernel 6.18.54-e5-mobile4-tfmmc1; screen 1.6.7; OpenClash 0.48.002; Mihomo 1.19.32; OpenClash screen 1.1.1-local; hotspot screen 1.0.3-local; Android app 1.0-local; switch module 1.1.3-tf-local |
| TF 迁移 / Migration | 全卡写入、读回比较、干净根系统部署、ext4 扩容及离线检查通过。使用干净材料重建并选择性恢复功能与配置，没有直接克隆故障根镜像。 / Full-card write/read comparison, clean-root deployment, ext4 expansion and offline checks passed. Features and configuration were selectively restored onto a clean build, not cloned from the faulty root image. |
| 当前根系统 / Current root | TF 上直接 ext4 根可读写，UUID/几何匹配，错误计数 0；1,830 项关键文件和完整 B 启动镜像匹配。 / Direct TF ext4 root was writable with matching UUID/geometry and zero error count; 1,830 critical files and the complete B boot image matched. |
| Android 数据与 NV / Data and NV | 正常 TF 运行中，userdata 内核只读且所有可观察进程命名空间均未挂载；9 个 NV 工作 loop 的结构/几何与物理 NV 只读状态通过。可变 NV 内容未按初始哈希锁死。 / Userdata was kernel-read-only and unmounted in all observable namespaces. Nine NV working-loop geometries and physical-NV read-only state passed; mutable NV contents were not required to retain initial hashes. |
| 双向与普通重启 / Switching and ordinary reboots | 迁移阶段验证 OpenWrt 屏幕 API 进入 Android、Android 普通重启停留、模块返回 TF，以及普通 TF 重启保持 OpenWrt 默认。新 UI 阶段另验证了 Android 普通重启和 UI 自动返回；没有为新 UI 再重复一次普通 TF 重启。 / Migration validation covered the OpenWrt screen API, Android stay/default behavior, return to TF and an ordinary TF reboot. The later UI phase separately checked an Android reboot and UI-triggered return; it did not repeat another ordinary TF reboot. |
| 新 Android 入口 / New Android entry | 实际电源菜单识别、附加入口、确认框、取消和单次确认通过界面点击验证。取消没有创建任务或修改启动控制。 / The actual power menu, added entry, dialog, cancellation and one confirmation were exercised through UI input. Cancellation created no task or boot-control change. |
| 关闭与重开 / Close and reopen | 返回桌面后仍为同一任务、同一 worker；重开显示中文阶段和增长的用时，开始按钮呈禁用状态。未测试强制停止应用或任意进程杀除。 / Back to the launcher retained the same task and worker. Reopening showed progress and increasing elapsed time with the start button disabled. Force-stop and arbitrary process killing were not tested. |
| Android 重启保持 / Android persistence | 应用、无障碍菜单入口、通知和本应用 root 授权在普通 Android 重启后保留，启动后无自动提交任务。 / The app, accessibility entry, notifications and its root grant persisted; no task was automatically submitted at boot. |
| UI 自动返回 / Automatic return | 单次确认至重启断连约 647 秒，随后独立观察到新 TF 启动。default/next 为 OpenWrt，返回请求已消费，启动控制 CRC 与尝试次数读回符合预期。断连返回码单独保留，不把它改写为成功。 / About 647 seconds from confirmation to disconnect, followed by an independently observed new TF boot. Default/next target, consumed request, boot-control CRC and attempt count matched. Disconnect status was retained rather than relabelled as success. |
| 屏幕与代理 / Screen and proxy | 屏幕三个服务实例、静态页面、热点 AP、OpenClash 控制器/核心、模式及保存的节点选择通过。服务运行不代替当前实体像素、触摸或按键验收。 / Three screen instances, static UI, hotspot AP, OpenClash controller/core, mode and saved selection passed. Service health does not establish physical display, touch or button behavior. |
| 配置与消息 / Configuration and messages | 原 66 项配置基线保持不变；已批准的数据卡选择、运行电量和流量累计作单独语义核对，其余静态配置匹配。原有消息及待处理记录保留，未由验收触发重放。 / The original 66-file baseline was retained. Approved data-SIM selection, battery state and traffic accumulation were reviewed separately; other static configuration matched. Existing message and pending records were preserved without replay by validation. |

### 网络启动过程 / Network startup

新 UI 返回后的首次采集约在开机一分钟：WAN 仍 pending，DNS 服务尚未就绪；设备两站 HTTPS 失败，USB 客户端两站也没有获得 DNS 地址。没有为此修改网络配置。随后约两分钟时服务启动完成，WAN up、DNS 服务运行，设备自身及 Mac 经固定 E5 USB 接口/DNS 的两站 HTTPS 均返回 204，TLS 校验开启且未使用应用代理。

The first collection after the UI return ran around one minute into boot: WAN was pending and DNS was not ready. Both device HTTPS checks failed; both USB-client checks lacked DNS addresses. No network configuration was changed to recover. Around two minutes, WAN and DNS were ready; both device-origin requests and both Mac requests through the bound E5 USB interface/DNS returned HTTP 204 with TLS verification and no application proxy.

**初始失败与后续成功均保留。** 原采集报告中的待审状态没有覆盖成全绿：配置、日志及早期 WAN/DNS 分别由同次启动的旁证闭合。设备自身测试不等于客户端转发；USB 客户端成功不等于手机 Wi-Fi 已验收。

**Initial failures remain alongside later success.** The original report was not rewritten as entirely green; configuration, log and startup-network items were resolved with separate evidence from the same boot. Device-origin tests do not prove client forwarding, and USB-client success does not prove phone Wi-Fi.

### 日志与未完成项 / Logs and remaining limits

- 历史内部 F2FS/嵌套 ext4 存在复发故障；OpenClash 安装前已经发生。TF 迁移改变了根系统的存储路径，没有据此证明所有历史损坏或断网原因已消除。 / Recurring faults affected the old F2FS/nested-ext4 layout before OpenClash was installed. Moving the root to TF does not prove all historical storage or disconnect causes are fixed.
- 新 UI 返回这次采集中，明确的 TF/eMMC、F2FS、ext4、loop 存储错误候选为 0，ext4 错误计数为 0。两条被通用扫描器命中的记录实际上是 SMS `mmcli` 失败；短信异常仍保留，不能当成健康短信收件。 / The UI-return samples contained no explicit TF/eMMC, F2FS, ext4 or loop storage-error candidates, and ext4 reported zero errors. Two broad-classifier hits were actual SMS `mmcli` failures; those failures remain unresolved service observations.
- 早期 TF 启动有真实 mmc2 SDIO command-interrupt 异常。新 UI 返回这次文本日志未见同一条异常，但仍有 SDIO 移除/重枚举；不能据一次未出现宣布驱动问题已修复。环形 dmesg 不含完整启动前缀，文本快照也不能证明内核序号全程连续。 / Earlier TF boots had a real mmc2 SDIO command-interrupt anomaly. It was absent from the UI-return text snapshot, which still showed SDIO removal/re-enumeration. That absence does not prove a driver fix. Ring-buffer and text-log coverage limits remain.
- 当前新启动没有新增实体屏幕触摸、手机关闭移动数据后的 Wi-Fi 上网、双卡往返、真实短信接收或脱离 USB 长期运行验收。此前用户确认过屏幕显示与触摸，但不扩大到每次启动与全部操作。 / No fresh acceptance covers physical touch, phone Wi-Fi with mobile data disabled, a full two-SIM cycle, actual SMS reception or sustained untethered use. Earlier user screen/touch confirmations remain scoped to those observations.
- 热点插件 1.0.3 的“解除后直接重连，不改密码、不重启热点”独立手机复测仍待完成。 / The separate 1.0.3 phone reconnection test after unblock, without password change or hotspot restart, remains deferred.

## 早期实机观察 / Earlier device observations

这些结果来自 10 月 20—21 日的内部镜像方案，不是当前 TF 版本的新一轮手机或全部硬件验收。

These observations came from the internal-image deployment on 20–21 October, not fresh phone or complete hardware acceptance of the TF version.

| 功能 / Feature | 历史结果 / Historical result |
| --- | --- |
| OpenClash | 两节点选择、手动 HTTPS 延迟、四模式、DNS/透明转发及停用恢复曾测试；一次全局模式请求超时保留。 / Two proxies, manual HTTPS delay, four modes, DNS/transparent forwarding and disable recovery were exercised; one global-mode timeout was retained. |
| 手机热点 / Phone hotspot | 用户曾确认另一台手机关闭移动数据后可访问国内与代理路径；当时 E5 连接 USB。 / A user confirmed domestic and proxied access from a phone with mobile data disabled while the E5 was USB-connected. |
| 热点密码与计数 / Password and counters | 用户改密、二维码刷新、其他手机连接及实际计数增长有观察。一次热重载后特定手机掉线，经完整无线初始化恢复，底层原因未唯一定位。 / Password/QR changes, phone connection and increasing counters were observed. One phone disconnected after a hot reload and recovered after full radio initialization; the underlying cause was not uniquely established. |
| 拉黑与解除 / Block and unblock | 早期实现的 UCI、hostapd ACL 与 nft 名单同步通过；它不代替当前版本独立解除重连测试。 / Earlier UCI, hostapd ACL and nft-list synchronization passed; this does not replace the deferred reconnect-after-unblock test. |

## 主机验证与公开边界 / Host tests and public boundary

早期公开 OpenClash 源码有 **16 项**主机测试，热点插件有 **19 项**；占用扫描器有 **128 项通过、4 项 Linux 专用测试在 macOS 跳过**，快照检查器有 **11 项**。命令和环境边界见[主机验证](../tools/VALIDATION.md)。这些结果不能代替安装或硬件验收。

The earlier public OpenClash source had **16** host tests and the hotspot plugin **19**. The occupancy scanner recorded **128 passes and 4 Linux-only skips on macOS**; the snapshot validator recorded **11**. See [host validation](../tools/VALIDATION.md) for commands and environment limits. These results are not device-installation acceptance.

**2026-10-23 公开参考源码**在 macOS arm64 上通过 Android 组件 **116 项**用例：菜单/展示 27 项、协议与 root 执行拒绝 42 项、后台 43 项、发布门禁 4 项；TF 组件 **40 项**用例通过，共 **156 项**。未签名参考 APK 编译通过，产物不提交；这些主机测试没有执行真实设备切换。精确命令与环境见 [Android 验证清单](../components/android-system-switch-ui/VALIDATION.json)和 [TF 验证清单](../components/tf-system-switch/VALIDATION.json)。公开入口拒绝与构建边界见相应组件 README；本地已部署源码与公开参考包不是可互换的安装产物。

On **2026-10-23**, the **public reference source** passed **116 Android-component cases** on macOS arm64: 27 menu/presentation, 42 protocol/root-refusal, 43 backend and 4 publication-gate cases. The TF component passed **40**, for **156 cases** in total. An unsigned reference APK also compiled; its output is not committed. These host tests performed no real device switch. See the [Android validation manifest](../components/android-system-switch-ui/VALIDATION.json) and [TF validation manifest](../components/tf-system-switch/VALIDATION.json) for exact commands and environment. Component READMEs describe public refusal/build boundaries; the deployed local source and public reference package are not interchangeable installable artifacts.

## 截图 / Screenshots

OpenWrt 截图来自已部署屏幕 Web 界面，按 **320 × 480** 面板尺寸捕获并拼接；长页纵向拼接，重复标题和导航保留一次，OpenClash 调整特写是模式控件裁切。它们是界面记录，不是当前启动、延迟或持续联网的证明。图中 1131 ms、547 ms 是先前手动测试记录，截图没有重新测速或换节点。

OpenWrt images were captured from the deployed screen web UI at **320 × 480**, with scrolling content stitched and repeated headers/navigation retained once. The OpenClash adjustment close-up crops the mode controls. These are interface records, not evidence of the latest boot, latency or sustained availability. The displayed 1131 ms and 547 ms are previous manual-test results; capture did not retest or change the proxy.

新增 Android 两张图是实际电源菜单和任务关闭重开后的进度画面，未重绘界面；它们与启动、状态和网络验收分别记录。

The two new Android images show the actual power menu and progress after reopening the task page. They are not redrawn mock-ups; screenshot, boot, status and network evidence remain distinct.
