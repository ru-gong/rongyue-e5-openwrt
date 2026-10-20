# Rongyue E5: network controls on the built-in screen

[中文](project-intro.zh-CN.md) · [Project home](../README.en.md)

The Rongyue E5 OpenWrt project brings a portable Wi-Fi hotspot, on-device network controls and system switching together in one device. Phones and computers can share its cellular connection over Wi-Fi. The built-in screen shows signal and data usage and provides direct access to OpenClash routing modes, proxy selection and HTTPS latency checks. Android remains available alongside OpenWrt, with a reboot to switch between them. Once installation is complete, routine switching needs no computer or reflashing.

![Rongyue E5 screen overview](images/e5-interface-overview.png)

## View network and device status

The overview shows connectivity, hotspot status, traffic rates, battery level, memory usage and temperatures. The signal page shows network technology, radio band and signal measurements. The data usage page shows daily, monthly and historical usage.

## Manage hotspot credentials and connected clients

Use **Hotspot → Change hotspot password** to edit the password with the screen
keyboard or physical number keys. Saving reinitializes the radio and refreshes
the QR code, so clients need to reconnect.

**Hotspot → Manage clients / Blacklist** shows client names, IP/MAC addresses,
state, upload/download totals and rates, and connection or observation time.
Clients can be disconnected, blocked or unblocked. Counters start after
discovery, include proxy/local traffic, reset after restart, and do not replace
cellular billing records.

See the [hotspot plugin guide](../components/hotspot-screen/README.md) for the
implementation and validation limits. A separate end-to-end reconnection
after native-ACL unblock remains deferred.

## Control OpenClash from the screen

Open **Apps → OpenClash** to see the core status, routing mode and selected proxy. Touch controls or the direction and confirm keys provide three main actions:

1. **Change routing mode.** Choose Direct, GFW, Mainland whitelist or Global.
2. **Select a proxy.** The selection is saved and applied automatically, without rebooting the device.
3. **Check proxy latency.** Choose **Test all** to see each proxy's HTTPS request latency, result and test time.

| Mode | Routing behavior |
| --- | --- |
| Direct | Connect directly to destinations without using a proxy |
| GFW | Proxy requests matching the GFW domain list; connect directly otherwise |
| Mainland whitelist | Connect directly for requests matching China domain or IP rules; proxy the rest |
| Global | Use global proxy mode to route through the selected proxy |

GFW and Mainland whitelist modes send local-domain and private-network requests directly before applying their other rules. Routing mode changes are also saved and applied without a device reboot. Latency tests compare response times to a probe address and do not automatically change the selected proxy.

![OpenClash status, routing controls and proxy selection](images/e5-openclash-focus.png)

*These are device screen captures, with scrolling content stitched vertically.*

## Switch between Android and OpenWrt

- **Enter Android:** on the OpenWrt screen, select **Advanced → System → Switch to Android**, then confirm the reboot.
- **Return to OpenWrt:** in Android, open **Magisk → Modules → E5 System Switch · Enter OpenWrt → Action**. The device then reboots into OpenWrt.

Routine switching needs no computer, microSD card or reflashing. The hotspot disconnects during the switch; wait for the system to boot and the network to reconnect.

## Project and open-source information

The project builds on [Enceka/e5-linux](https://github.com/Enceka/e5-linux) and [Enceka/infoscreen](https://github.com/Enceka/infoscreen), adding hotspot and OpenClash screen controls and device-specific switching integration. The repository includes plugin source, development history and sanitized implementation references.

Original code and documentation use the [MIT License](../LICENSE). Upstream components retain their own licenses; see the [third-party notices](../THIRD_PARTY_NOTICES.md). This is an integration project for a single device. Known issues, including storage reliability, are documented in the [validation record](validation.md). Published switching code is a reference, not an installable module.
