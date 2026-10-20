# 验证记录 / Validation

记录日期 / Record date: **2026-10-20**.

## Publication checks / 本次发布检查

The public OpenClash source passed **16 host-only unit tests** during repository preparation. The tests use temporary files and fake API controllers; real Ruby YAML transformations are exercised. They do not connect to an E5 or a proxy service.

本次测试覆盖：

- 四种模式的实际规则差异、未知配置识别和非法输入拒绝。
- `GLOBAL → PROXY` 选择约束。
- 节点与凭据保留、模式与节点选择持久化。
- 已应用但 API 回复丢失、文件保存失败后的回退与核对。
- 只暴露节点信息、不在返回值中暴露凭据。
- 延迟测试不自动换节点，以及节点定义改变后旧缓存失效。

The screen runtime source matches the local 1.1.1 integration. Publication changes add documentation and package license/notice files; they do not change routing behavior. The public system-switch references are deliberately stopped before device access. Their early-stop behavior and shell syntax are checked by `scripts/check_publication.py`.

Independent historical tooling is documented in [tools](../tools/README.md). Its host tests are separate from firmware installation or device acceptance.

The published occupancy scanner passed **128 tests**, with **4 Linux-specific tests skipped** on macOS. The snapshot validator passed **11 tests**. Commands, environment limits and results are recorded in [host validation](../tools/VALIDATION.md).

## Historical device observations / 历史实机验证

These are records from the original project, **not new device tests run while publishing this repository**. Private raw evidence remains outside this repository. Screenshots are an interface record, not a continuous availability or throughput measurement.

| 功能 / Feature | Observed result |
| --- | --- |
| Local versions | OpenWrt 25.12.5; OpenClash v0.48.002; Mihomo v1.19.32 ARM64; screen plugin 1.1.1-local; local switch module 1.0.2-local |
| Proxy core | Native candidate configuration validation passed; the local CN rules loaded |
| Two configured proxy nodes | Independent HTTPS delay requests and node selection succeeded; Google returned 204 and Baidu returned 200 after each selection |
| Routing modes | Four-mode switching and source/UCI readback were exercised; global Google returned 204, while one global-mode Baidu request timed out after 18 seconds |
| LAN forwarding | Host traffic bound to the E5 network interface used its DNS, transparent forwarding and cellular uplink successfully |
| Phone hotspot | User confirmed Baidu and Google loaded on a second phone with that phone's mobile data disabled; the E5 remained connected to USB |
| Disable recovery | Stopping OpenClash removed its core/rules; DNS and direct domestic connectivity recovered; the service was then re-enabled |
| Screen | User confirmed the mode controls, both nodes, latency values and test button appeared on the E5 screen |
| System switching | OpenWrt screen to Android, Android Magisk action back to OpenWrt, default behavior and ordinary reboot had device observations |
| Configuration preservation | Unrelated hotspot/network configuration and switch implementation were checked against their local baselines |

## Current limits / 当前边界

The latest evening state supersedes earlier observations where they differ:

- **SIM2:** China Unicom is the current working cellular uplink.
- **SIM1:** both cards had worked earlier, but China Mobile SIM1 was not detected after a later recovery. Contact and registration need to be checked again.
- **SMS:** backend support remains, but actual message reception has not completed acceptance.
- **Long-term operation:** sustained operation with USB disconnected is not established.
- **Storage:** F2FS/shared-userdata and the internal ext4 image have suffered recurring corruption. Snapshot preservation and targeted recovery do not establish that the underlying cause is fixed.
- **Other devices:** these observations do not validate another E5, a different storage layout, arbitrary firmware, or arbitrary OpenClash configuration.

## Screenshots / 截图

Screenshots were captured from the device's currently deployed screen web service at its **320 × 480** panel size, then locally composed. Scrolling pages were stitched vertically; headers and navigation were retained once. The OpenClash adjustment close-up is a crop of its mode controls, not a separate implementation or mock-up.

The 1131 ms and 547 ms values shown in the screenshots are retained **previous manual-test records**. Capturing the screenshots did not repeat the latency test or change the selected node/mode.
