# 荣悦 E5 · OpenWrt 随身 Wi-Fi

[English](README.en.md) · [项目介绍](docs/project-intro.zh-CN.md)

在荣悦 E5 上整合蜂窝热点、机身屏幕网络管理和 Android / OpenWrt 双系统。屏幕可以查看信号与流量、管理热点，并直接调整 OpenClash 的分流模式和代理节点。

**当前 OpenWrt 运行在 TF（microSD）卡上，Android 保留在内部存储。** 日常切换通过屏幕完成，无需电脑或重新刷机；运行 OpenWrt 时需保持这张已适配的 TF 卡插入。

## 主要功能

- **随身热点：** 将蜂窝网络共享给连接 E5 Wi-Fi 的手机、电脑等设备。
- **屏幕状态面板：** 查看连接状态、信号、频段、流量、电量、温度和内存使用情况。
- **OpenClash 屏幕控制：** 切换四种分流模式、保存节点选择、手动测试 HTTPS 延迟。
- **热点管理：** 修改密码并刷新二维码，查看连接设备、流量与连接时长，踢下线、拉黑或解除。
- **双系统切换：** 从 OpenWrt 屏幕进入 Android；从 Android 电源菜单的附加入口返回 OpenWrt，并设为默认系统。

![概览、信号、OpenClash、流量与系统切换界面](docs/images/e5-interface-overview.png)

## 在机身屏幕上调整 OpenClash

打开 **应用 → OpenClash**，通过触摸或方向键、确认键操作：

- 在**直连、GFW、大陆白名单、全局**四种模式之间切换。
- 选择代理节点，选择会保存并应用。
- 点击**测试全部**，查看各节点的 HTTPS 请求延迟和测试时间。

模式和节点调整无需重启设备。测试由用户手动发起，不会自动更换节点。

![OpenClash 状态、模式调整与节点选择](docs/images/e5-openclash-focus.png)

## Android 与 OpenWrt 切换

| 切换方向 | 操作入口与默认行为 |
| --- | --- |
| OpenWrt → Android | **高级 → 系统 → 切换到 Android**，确认后重启；普通 Android 重启继续停留 Android |
| Android → OpenWrt | 长按电源键，在原菜单下方点击 **返回 OpenWrt / 设为默认系统**，再确认；检查通过后自动重启，恢复 OpenWrt 默认 |

![Android 电源菜单下方的返回入口](docs/images/e5-android-power-menu.png)

Android 返回流程显示实际阶段和已用时间，可关闭页面后重新查看同一任务。本机一次完整返回约需 **11 分钟**，不是固定时限。只点击一次、保持供电，等待自动重启；期间不要手动重启或拔卡。切换会中断热点，网络还需等待系统和蜂窝服务启动。

详见[双系统使用与 TF 架构说明](docs/tf-system-switch.zh-CN.md)。Android 应用为 `1.0-local`，本机切换模块为 `1.1.3-tf-local`。

## 热点密码与连接设备

**热点 → 修改热点密码** 支持屏幕键盘和实体数字键，保存后刷新二维码，客户端需重新连接。**管理连接设备 / 黑名单**提供连接状态、上传下载累计与速率、连接或观察时长，以及断开、拉黑与解除。

计数从发现连接后开始，含代理和本地通信，重启清零，不等同于运营商计费流量。实现与验证边界见[热点插件说明](components/hotspot-screen/README.md)。

## 文档与源码

- **项目介绍：** [中文](docs/project-intro.zh-CN.md) / [English](docs/project-intro.en.md)
- **双系统使用与架构：** [中文](docs/tf-system-switch.zh-CN.md) / [English](docs/tf-system-switch.en.md)
- **屏幕插件：** [OpenClash](components/openclash-screen/README.md) · [热点管理](components/hotspot-screen/README.md)
- **当前切换实现：** [Android 电源菜单与进度页](components/android-system-switch-ui/README.md) · [TF 启动与切换参考](components/tf-system-switch/README.md)
- **开发过程：** [中文](docs/history/timeline.zh-CN.md) / [English](docs/history/timeline.en.md) · [历史源码目录](archive/CATALOG.md)
- **验证：** [实机观察与已知边界](docs/validation.md) · [主机工具](tools/README.md)

## 项目状态与来源

这是单台 E5 的适配实践。TF 迁移、双向切换、默认启动行为和新 Android 入口已有实机验证；实体屏幕功能、客户端联网与长期稳定性的具体范围见[验证记录](docs/validation.md)。迁移和一次联网成功不代表历史偶发断网已根治。

仓库提供源码和脱敏实现参考，不提供完整固件或可直接部署到其他设备的切换包。公开启动、切换脚本默认拒绝设备操作，私有绑定、配置和备份不随仓库发布。[旧无 TF 方案](components/system-switch/README.md)仅保留为历史参考。

基础系统与屏幕框架来自 [Enceka/e5-linux](https://github.com/Enceka/e5-linux) 和 [Enceka/infoscreen](https://github.com/Enceka/infoscreen)，并使用 [OpenClash](https://github.com/vernesong/OpenClash)、[Mihomo](https://github.com/MetaCubeX/mihomo) 和 [Magisk](https://github.com/topjohnwu/Magisk)。本项目原创代码和文档采用 [MIT 许可证](LICENSE)；第三方作品保留各自版权和许可证，见[来源与许可证说明](THIRD_PARTY_NOTICES.md)。
