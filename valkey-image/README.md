# The Valkey 8.0 container image


[![SLSA](https://img.shields.io/badge/SLSA_(v0.1)-Level_4-Green)](https://documentation.suse.com/sbp/security/html/SBP-SLSA4/)
[![Provenance: Available](https://img.shields.io/badge/Provenance-Available-Green)](https://documentation.suse.com/container/all/html/Container-guide/index.html#container-verify)

## Description

Valkey is a high-performance data structure server that primarily serves
key/value workloads. It supports a wide range of native structures and
an extensible plugin system for adding new data structures and access
patterns.

## How to use the image

The image ships with the valkey server and a persistent storage configured
to `/data`.

To start an instance, follow these instructions:


```ShellSession
podman run --rm registry.suse.com/suse/valkey:8.0
```

In case you want start with persistent storage, run this:

```ShellSession
podman run --rm registry.suse.com/suse/valkey:8.0 valkey-server --save 60 1
```

This one will save a snapshot of the DB every 60 seconds if at least 1
write operation was performed. If persistence is enabled, data is stored
in the VOLUME /data, which can be used with `-v /host/dir:/data`.


## Licensing

`SPDX-License-Identifier: BSD-3-Clause`

This documentation and the build recipe are licensed as BSD-3-Clause.
The container itself contains various software components under various open source licenses listed in the associated
Software Bill of Materials (SBOM).

This image is based on [SUSE Linux Enterprise Server](https://www.suse.com/products/server/), a reliable,
secure, and scalable server operating system built to power mission-critical workloads in physical and virtual environments.