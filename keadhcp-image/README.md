# Kea DHCP Server Container container image

![Redistributable](https://img.shields.io/badge/Redistributable-Yes-green)

 Kea DHCP Server Container container based on the openSUSE Tumbleweed Base Container Image.

## How to use this container image

The container image expects dhcp configuration file in the path /etc/kea.
To run dhcp4 for the configuration provided in the directory /etc/kea

```ShellSession
podman container runlabel run \
      registry.opensuse.org/opensuse/keadhcp:2.6.1
```
To run dhcp6 for the configuration provided in the directory /etc/kea

```ShellSession
podman container runlabel run_dhcp6 \
      registry.opensuse.org/opensuse/keadhcp:2.6.1
```

Dhcp configuration file can also be provided in the current directory.
To run dhcp4 for the configuration provided in the current directory

```ShellSession
podman container runlabel runcwd \
      registry.opensuse.org/opensuse/keadhcp:2.6.1
```
To run dhcp6 for the configuration provided in the current directory

```ShellSession
podman container runlabel runcwd_dhcp6 \
      registry.opensuse.org/opensuse/keadhcp:2.6.1
```
## Licensing

`SPDX-License-Identifier: MPL-2.0`

This documentation and the build recipe are licensed as MPL-2.0.
The container itself contains various software components under various open source licenses listed in the associated
Software Bill of Materials (SBOM).

This image is based on [openSUSE Tumbleweed](https://get.opensuse.org/tumbleweed/).
