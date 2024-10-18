# Kea DHCP Server Container container image

![Support Level](https://img.shields.io/badge/Support_Level-techpreview-blue)[![SLSA](https://img.shields.io/badge/SLSA_(v1.0)-Build_L3-Green)](https://documentation.suse.com/sbp/server-linux/html/SBP-SLSA4/)
[![Provenance: Available](https://img.shields.io/badge/Provenance-Available-Green)](https://documentation.suse.com/container/all/html/Container-guide/index.html#container-verify)

 Kea DHCP Server Container container based on the SLE Base Container Image.

## How to use this container image

The container image expects dhcp configuration file in the path /etc/kea.
To run dhcp4 for the configuration provided in the directory /etc/kea

```ShellSession
podman container runlabel run \
      registry.suse.com/suse/keadhcp:2.6.1
```
To run dhcp6 for the configuration provided in the directory /etc/kea

```ShellSession
podman container runlabel run_dhcp6 \
      registry.suse.com/suse/keadhcp:2.6.1
```

Dhcp configuration file can also be provided in the current directory.
To run dhcp4 for the configuration provided in the current directory

```ShellSession
podman container runlabel runcwd \
      registry.suse.com/suse/keadhcp:2.6.1
```
To run dhcp6 for the configuration provided in the current directory

```ShellSession
podman container runlabel runcwd_dhcp6 \
      registry.suse.com/suse/keadhcp:2.6.1
```
## Licensing

`SPDX-License-Identifier: MPL-2.0`

This documentation and the build recipe are licensed as MPL-2.0.
The container itself contains various software components under various open source licenses listed in the associated
Software Bill of Materials (SBOM).

This image is a tech preview. Do not use it for production.
Your feedback is welcome.
Please report any issues to the [SUSE Bugzilla](https://bugzilla.suse.com/enter_bug.cgi?product=SUSE%20Linux%20Enterprise%20Base%20Container%20Images).
