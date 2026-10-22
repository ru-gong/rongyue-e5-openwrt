# Source attribution

The Java UI/client, status protocol, detached-worker glue, read-only observer and local test adaptations are covered by the repository [MIT license](../../LICENSE).

The Android switching design and its boot-control dependency build on [Enceka/e5-linux at 569f13d4](https://github.com/Enceka/e5-linux/tree/569f13d4ce15585f70817c2a1e03bb574a84720b/magisk). Copyright (c) 2026 Enceka; preserve [the complete upstream MIT notice](../../LICENSES/MIT-Enceka.txt). The derived native boot-control and init source are published separately in [tf-system-switch](../tf-system-switch/NOTICE.md).

The app uses Android SDK APIs and the installed Magisk `su` interface. It does not bundle or copy Magisk/libsu implementation code, the SDK, BusyBox, Linux, firmware or signed APKs. Those external dependencies retain their own licenses; our MIT license does not relicense them. Official API/reference links and dependency licenses are recorded in the repository [third-party notices](../../THIRD_PARTY_NOTICES.md).

`SOURCE-PROVENANCE.json` describes the local source lineage and explicit publication-only disablement. The reference build is intentionally incapable of submitting device work.
