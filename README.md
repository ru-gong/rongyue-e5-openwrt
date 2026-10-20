# 荣悦 E5 · OpenWrt 随身 Wi-Fi

[English](README.en.md) · [项目介绍](docs/project-intro.zh-CN.md)

为荣悦 E5 增加 OpenWrt 网络管理和机身屏幕操作能力：提供蜂窝 Wi-Fi 热点、查看信号与流量、直接调整 OpenClash，并保留 Android 与 OpenWrt 双系统切换。

## 主要功能

- **随身热点：** 将蜂窝网络共享给连接 E5 Wi-Fi 的手机、电脑等设备。
- **屏幕状态面板：** 查看网络连接、信号强度、频段、流量、电量、温度和内存使用情况。
- **OpenClash 屏幕控制：** 切换分流模式、选择代理节点、手动测试 HTTPS 延迟。
- **双系统切换：** 从 OpenWrt 屏幕重启进入 Android，通过 Android 的 Magisk 模块重启返回 OpenWrt。

![概览、信号、OpenClash、流量与系统切换界面](docs/images/e5-interface-overview.png)

## 在机身屏幕上调整 OpenClash

打开 **应用 → OpenClash**，即可查看运行状态、分流模式和所选节点，并通过触摸或方向键、确认键操作：

- 在**直连、GFW、大陆白名单、全局**四种模式之间切换。
- 从节点列表中选择代理节点，选择会自动保存并应用。
- 点击**测试全部**，查看各节点的 HTTPS 请求延迟和测试时间。

模式和节点调整无需重启设备。延迟测试由用户手动发起，不会自动更换节点。

![OpenClash 状态、模式调整与节点选择](docs/images/e5-openclash-focus.png)

## Android 与 OpenWrt 切换

| 切换方向 | 操作入口 |
| --- | --- |
| OpenWrt → Android | 机身屏幕：高级 → 系统 → 切换到 Android |
| Android → OpenWrt | Magisk → 模块 → E5 系统切换 · 进入 OpenWrt → 操作 |

系统切换通过重启完成，期间热点会断开。完成安装后，日常切换不需要电脑、TF 卡或重新刷机。

## 文档与源码

- **项目介绍：** [中文](docs/project-intro.zh-CN.md) / [English](docs/project-intro.en.md)
- **OpenClash 屏幕插件：** [源码、构建与适配要求](components/openclash-screen/README.md)
- **双系统切换：** [操作说明与实现参考](components/system-switch/README.md)
- **开发过程：** [中文记录](docs/history/timeline.zh-CN.md) / [English timeline](docs/history/timeline.en.md)
- **过程代码：** [分阶段源码目录](archive/CATALOG.md) · [主机工具与测试](tools/README.md)
- **验证记录：** [实机测试、已知问题与截图说明](docs/validation.md)

## 项目状态

本项目记录一台荣悦 E5 的适配与开发实践。已知存储稳定性问题和其他待验证项目详见[验证记录](docs/validation.md)。公开的系统切换代码为脱敏实现参考；仓库不提供完整固件或可直接安装的切换模块。

## 来源与许可证

基础系统与屏幕界面基于 [Enceka/e5-linux](https://github.com/Enceka/e5-linux) 和 [Enceka/infoscreen](https://github.com/Enceka/infoscreen)。本项目增加 OpenClash 屏幕控制与本机双系统切换适配，使用 [OpenClash](https://github.com/vernesong/OpenClash)、[Mihomo](https://github.com/MetaCubeX/mihomo) 和 [Magisk](https://github.com/topjohnwu/Magisk) 的相关能力。

新增代码和文档采用 [MIT 许可证](LICENSE)。第三方作品保留各自版权与许可证，具体版本和引用范围见[第三方来源与许可证](THIRD_PARTY_NOTICES.md)。
