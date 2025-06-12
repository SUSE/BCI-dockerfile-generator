# Samba Toolbox Container Image

[![SLSA](https://img.shields.io/badge/SLSA_(v1.0)-Build_L3-Green)](https://documentation.suse.com/sbp/server-linux/html/SBP-SLSA4/)
[![Provenance: Available](https://img.shields.io/badge/Provenance-Available-Green)](https://documentation.suse.com/container/all/html/Container-guide/index.html#container-verify)

## Description

Samba is a feature-rich Open Source implementation of the SMB and Active Directory protocols for Linux and UNIX-like systems.

This image comes with Samba tools and TDB tools.

## Usage

To check the available shares in a SMB file server, run the following command:

```ShellSession
$ podman run -it --rm registry.suse.com/suse/samba-toolbox:4.19 smbclient -L //SERVER/SHARE -U "DOMAIN\\username"
```

To check the available shares anonymously in a SMB file server, run the following command:

```ShellSession
$ podman run -it --rm registry.suse.com/suse/samba-toolbox:4.19 smbclient -L //SERVER/SHARE -N
```

To list all Samba users in the Samba database, run the following command:

```ShellSession
$ podman run -it --rm -v /path/to/samba/data:/var/lib/samba registry.suse.com/suse/samba-toolbox:4.19 pdbedit -L
```

To print all records in the Samba secrets database, run the following command:

```ShellSession
$ podman run -it --rm -v /path/to/samba/data:/var/lib/samba registry.suse.com/suse/samba-toolbox:4.19 tdbdump /var/lib/samba/private/secrets.tdb
```

## Licensing

`SPDX-License-Identifier: GPL-3.0-or-later`

This documentation and the build recipe are licensed as GPL-3.0-or-later.
The container itself contains various software components under various open source licenses listed in the associated
Software Bill of Materials (SBOM).

This image is based on [SUSE Linux Enterprise Server](https://www.suse.com/products/server/), a reliable,
secure, and scalable server operating system built to power mission-critical workloads in physical and virtual environments.