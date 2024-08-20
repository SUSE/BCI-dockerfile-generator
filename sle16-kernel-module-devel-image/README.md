# SLE Framework One Kernel Module Development Container
![Redistributable](https://img.shields.io/badge/Redistributable-Yes-green)![Support Level](https://img.shields.io/badge/Support_Level-techpreview-blue)
[![SLSA](https://img.shields.io/badge/SLSA_(v0.1)-Level_4-Green)](https://documentation.suse.com/sbp/server-linux/html/SBP-SLSA4/)
[![Provenance: Available](https://img.shields.io/badge/Provenance-Available-Green)](https://documentation.suse.com/container/all/html/Container-guide/index.html#container-verify)

## Description

The SLE Framework One Kernel Module
Development Container Image includes all necessary tools to build kernel modules
for SLE and SLE Micro. It is intended to be used for building out-of-tree kernel
modules in restricted environments for the SLE kernel.


## Usage

The image can be used to launch a container and build a kernel
module. The following example below shows how to do this for the DRBD kernel module:
```ShellSession
$ podman run --rm -it --name drbd-build registry.suse.com/bci/bci-sle16-kernel-module-devel:16.0
# zypper -n in coccinelle tar
# curl -Lsf -o - https://pkg.linbit.com/downloads/drbd/9/drbd-9.2.11.tar.gz | tar xzf -
# cd drbd-9.2.11/
# make -C drbd all KDIR=/usr/src/linux-obj/$(uname -m)/default
```

The built kernel module is then available in
`/drbd-9.2.11/drbd/build-current/drbd.ko`. It can be copied to the host system
as follows:
```ShellSession
$ podman cp drbd-build:/drbd-9.2.11/drbd/build-current/drbd.ko .
$ sudo modprobe drbd.ko
```

Alternatively, the kernel module can be built as part of a container build using
a `Dockerfile`:

```Dockerfile
FROM registry.suse.com/bci/bci-sle16-kernel-module-devel:16.0
ENV DRBD_VERSION=9.2.11
WORKDIR /src/
RUN zypper -n in coccinelle tar

RUN set -euxo pipefail; \
    curl -Lsf -o - https://pkg.linbit.com/downloads/drbd/9/drbd-${DRBD_VERSION}.tar.gz | tar xzf - ; \
    cd drbd-${DRBD_VERSION}; \
    make -C drbd all KDIR=/usr/src/linux-obj/$(uname -m)/default
```

Build the container image, launch the container, and copy the kernel module to
the local machine:
```ShellSession
$ buildah bud --layers -t drbd-ko .
$ podman run --name drbd drbd-ko
$ podman cp drbd:/src/drbd-9.2.11/drbd/build-current/drbd.ko .
$ podman rm drbd
```

## Licensing

`SPDX-License-Identifier: MIT`

This documentation and the build recipe are licensed as MIT.
The container itself contains various software components under various open source licenses listed in the associated
Software Bill of Materials (SBOM).

This image is a tech preview. Do not use it for production.
Your feedback is welcome.
Please report any issues to the [SUSE Bugzilla](https://bugzilla.suse.com/enter_bug.cgi?product=SUSE%20Linux%20Enterprise%20Base%20Container%20Images).
