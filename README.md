# 荣悦 E5 · OpenWrt 随身网络与屏幕控制

[English](README.en.md) · [可直接分享的中文介绍](docs/project-intro.zh-CN.md) · [English introduction](docs/project-intro.en.md)

把荣悦 E5 做成一台能在机身屏幕上查看状态、调整 OpenClash，并保留 Android 的 OpenWrt 随身网络设备。这个仓库整理本机适配代码、开发过程、实机验证记录和介绍截图，基于 [Enceka/e5-linux](https://github.com/Enceka/e5-linux) 等上游项目完成。

## 当前能做什么

- **蜂窝热点：** 当前通过联通 SIM2 上网，手机关闭自身移动数据后连接 E5 热点，已现场验证可访问国内与海外网站。
- **屏幕查看状态：** 网络连接、5G 信号、频段、流量、电量、内存和温度。
- **屏幕调整 OpenClash：** 直连、GFW、大陆白名单、全局四种模式；选择节点；手动测试 HTTPS 延迟。模式和节点选择保存后通过现有核心接口生效。
- **保留双系统：** OpenWrt 侧在屏幕选择“切换到 Android”；Android 侧通过 Magisk 模块“操作”返回 OpenWrt。完成安装后的日常切换无需电脑、TF 卡或重新刷镜像。

![项目界面总览](docs/images/e5-interface-overview.png)

## 从这里开始

| 想了解什么 | 内容 |
| --- | --- |
| 随截图发给别人的介绍 | [中文](docs/project-intro.zh-CN.md) / [English](docs/project-intro.en.md) |
| OpenClash 页面、分流与节点控制 | [组件源码与构建说明](components/openclash-screen/README.md) |
| 双系统切换如何实现 | [使用入口与源码边界](components/system-switch/README.md) |
| 整个项目怎样走到现在 | [过程回顾](docs/history/timeline.zh-CN.md) / [Timeline](docs/history/timeline.en.md) |
| 安装、恢复和扫描器的研发代码 | [过程源码归档](archive/README.md) |
| 已验证什么、还欠什么 | [验证记录](docs/validation.md) |
| 来自谁、遵循什么许可证 | [第三方来源与许可证](THIRD_PARTY_NOTICES.md) |

## 仓库范围

`components/openclash-screen/` 是已在本机使用的屏幕插件源码。`components/system-switch/reference/` 是保留检查与回退逻辑的脱敏参考，**启动即停止，不能作为安装模块使用**。`archive/` 保存过程源码及版本索引；归档中的历史状态不能替代当前版本。

没有收录 Android/基带固件、分区镜像、NV 校准数据、真实代理节点配置、SSH 凭据、本机身份与原始日志备份。上游固件、屏幕主程序和第三方核心以来源链接及许可证说明引用；本仓库不是完整固件镜像或通用刷机包。

## 验证状态

截至 **2026-10-20**，本机已完成热点联网、OpenClash 模式与节点操作、屏幕显示、系统往返切换及普通重启的验证。当前联通 SIM2 正常使用；移动 SIM1 在后续恢复后未检测到，需要重新检查。真实短信收件、断开 USB 后的长期使用仍待验证。

无 TF 的共享 userdata / F2FS 与内部 ext4 路线曾发生存储损坏，长期复发问题尚未解决。这里记录的是单机实践与已有验证，不能据此认为同型号设备可直接套用。

## 本地主机检查

需要 Python 3.10+、Ruby（含 YAML/Psych）和 POSIX shell：

```sh
python3 scripts/check_publication.py
python3 -m unittest discover -s components/openclash-screen -p 'test_*.py' -v
```

这些检查使用临时文件和模拟控制器，不连接 E5、不使用真实节点。其他过程工具的测试见对应目录。

## 许可证与致谢

本仓库新增代码和文档采用 [MIT License](LICENSE)。第三方作品保留各自版权和许可证，见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) 与 `LICENSES/`。截图中的基础界面来自上游信息屏；本项目新增 OpenClash 屏幕入口、节点操作和本机切换适配，不将上游整套系统作为原创。
