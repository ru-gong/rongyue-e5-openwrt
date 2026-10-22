# License texts / 许可证原文

These are unmodified texts fetched from the official upstream repositories at the revisions recorded in [sources.json](../sources.json). Inclusion of a license text does not mean the corresponding program or binary is bundled. See [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md) for component scope.

这些文件是按固定版本从上游直接读取的未改写许可证原文。保留许可文本不代表本仓库分发了对应软件或二进制；各组件实际范围见第三方声明。

`MIT-Enceka.txt` covers the identically licensed e5-linux and infoscreen sources cited here. OpenWrt packages retain their own licenses in addition to the build-system notice. `Unlicense-spreadtrum-original.txt` applies only to the original ilyakurdyukov project; it is not a license grant for TomKing062's additions.

The new TF `bootctl.c` and hardware/init adaptations also retain Enceka's MIT grant. The Android UI and local progress/occupancy code use the root project MIT license. Android SDK, Magisk, BusyBox, libc and kernel interfaces remain external; no SDK, vendor implementation or native binary is redistributed in the new reference components. A dependency's license text is not a grant to redistribute unlisted vendor files.

新增 TF bootctl 与硬件/init 改编继续保留 Enceka MIT 授权；原创 Android 界面、进度与占用检查代码适用根 MIT 许可。SDK、Magisk、BusyBox、libc 与内核接口是外部依赖，新参考组件不分发 SDK、厂商实现或原生二进制。保留某个依赖的许可证不代表获得其他厂商文件的再分发权。
