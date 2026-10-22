# Android power-menu return UI / Android 电源菜单返回入口

This is the source reference for the local E5 Android → TF OpenWrt interface, including its Android app, fixed root API, detached worker, progress observer and tests. **The public export cannot switch systems:** all shell entry points stop with exit 64, normal native builds are inert, and the app's root-process entry unconditionally refuses. No installable APK, module ZIP or signing key is supplied.

这是本机方案的源码公开版，涵盖界面到后台的完整核心调用链；公开版已主动禁用设备执行。它不是通用安装包，不能靠删除一行保护或复制他机绑定来部署。

## Demonstrated local behavior / 本机已验证的体验

On the project device, the installed private build added a compact entry below the original Android power menu. The user sees a confirmation that returning to OpenWrt also makes it the default. The page reads status automatically, shows Chinese phase labels and elapsed time, and warns that checks can take several minutes and will reboot automatically. It does not promise an instant switch or a fixed countdown.

本机已验证安装、通知与独立 root 授权、普通 Android 重启后入口/授权保留、一次真实界面确认后的自动返回，以及关闭页面再打开时任务和进度继续。这里只陈述这一台设备的历史实测，不表示其他固件、Magisk 版本或硬件组合已经通过。

## Source map

| Path | Contents |
| --- | --- |
| `app/src/cn/e5/switchui/` | Activity, narrowly filtered accessibility service, menu matcher, fixed root client, status model and foreground observer |
| `app/AndroidManifest.xml`, `app/res/` | Android API 33 component/permission declarations and resources |
| `app/build.py` | Portable unsigned review build using a separately installed SDK/JDK |
| `app/test_host.py`, `app/test_backend_host.py` | Java matcher, protocol and public execution-refusal fixtures |
| `backend/reference/` | Guarded Android action, switch, storage library, API, worker and shared observer support |
| `backend/ui-stream.c` | Read-only NDJSON observer; default build refuses, explicit tests use synthetic files |
| `backend/reference-baseline/switch.sh` | Guarded pre-progress switch for the progress-only source comparison |
| `backend/test_*.py`, `tests/test_publication.py` | Isolated backend/namespace/zram behavior and public-export boundary tests |
| `SOURCE-PROVENANCE.json` | Logical source-path mapping, publication transformations and published-file SHA256 |
| `PUBLICATION-GUARDS.json` | Machine-readable list of disabled entry points |

The TF initramfs, OpenWrt return handling and native helpers are in [tf-system-switch](../tf-system-switch/README.md). There is no automatic deployment or binding generator in either component.

## UI and execution boundary

The accessibility service subscribes only to `com.android.systemui` window-state events. It requires the observed event class/title/fullscreen, same window ID, active/focused system-window type, exact empty accessibility title, a fixed anchor and all three native menu labels. Other app content and notification events are not read. The fixed profile matches the tested Android 13 image; unknown layouts fail closed.

The supplemental button rechecks the unlocked menu before a single `GLOBAL_ACTION_BACK`, waits at most 1.5 seconds for that same menu window to disappear, then opens the confirmation Activity. This is an added accessibility window, not a SystemUI replacement. The Android global action is not an atomic targeted close, so a small check/action race remains.

外部 Intent、URI、通知点击或 Activity 恢复都不能提交切换。可见页面自动进行的只是状态读取；执行必须来自已解锁页面的明确确认。提交后无法通过关闭页面取消后台；失去状态流时显示 UNKNOWN，绝不自动重提，也不会把 REBOOTING 或断连写成「已进入 OpenWrt」。

The installed design uses only the fixed `start|status|stream` API and pins its script version. A single root stream supplies status; the app does not spawn one root process every second. The worker is detached from Activity lifetime. Raw logs remain root-only; the app offers phase/run/exit-code diagnostics, not unrestricted log access. The public app preserves this implementation for review but `RootSession.open()` always throws before process creation.

Only foreground-service and notification-output permissions are declared. The accessibility service and progress service are not exported. No Internet, storage, boot receiver, notification reader, arbitrary command API, or automatic switch on boot is provided.

## Build and host tests

Requirements: Python 3, a C compiler, JDK 17, Android SDK Platform 33 and Build Tools 35.0.0. Set `JAVA_HOME` or have `javac` on `PATH`; set `ANDROID_HOME` or `ANDROID_SDK_ROOT`. The SDK is an external dependency and is not included. See the official [SDK package-manager documentation](https://developer.android.com/tools/sdkmanager) for installing the pinned packages.

Run from the repository root:

```sh
python3 -B components/android-system-switch-ui/app/test_host.py
python3 -B components/android-system-switch-ui/app/test_backend_host.py
python3 -B -m unittest discover -s components/android-system-switch-ui/backend -p 'test_*.py' -v
python3 -B -m unittest discover -s components/android-system-switch-ui/tests -p 'test_*.py' -v
python3 -B components/android-system-switch-ui/app/build.py
```

The review APK and reports go to ignored `app/build/`; no signing or device installation command is included. The public APK uses a reference label and cannot execute root work. Java host tests exercise protocol maps and fixed commands without launching a process; full Android JSON/permission/runtime behavior is a separate device acceptance task.

Shell behavioral tests remove only the exact publication stop block **inside temporary copies**, replace all accessed device paths with synthetic trees and replace BusyBox/action execution with mocks. Native tests require `E5_PUBLIC_FIXTURE` and a matching test macro; they do not use the real runtime path. Default native builds exit 64. These fixtures are not an opt-in production switch.

## Omitted private inputs / 未公开内容

Device/card CID and serial, installation ID, partition/manifest binding values, protected-partition hashes, original evidence/logs, firmware, APK/ELF, helper binaries, SDK, signing material and deployment tools are omitted. Runtime paths in the source explain the local design; they are not proof that another device has the same layout. See [NOTICE](NOTICE.md) and the repository's [third-party notices](../../THIRD_PARTY_NOTICES.md).
