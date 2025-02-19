# SLE Xorg Server
![Support Level](https://img.shields.io/badge/Support_Level-techpreview-blue)[![SLSA](https://img.shields.io/badge/SLSA_(v1.0)-Build_L3-Green)](https://documentation.suse.com/sbp/server-linux/html/SBP-SLSA4/)
[![Provenance: Available](https://img.shields.io/badge/Provenance-Available-Green)](https://documentation.suse.com/container/all/html/Container-guide/index.html#container-verify)

## Description

X.Org Server is the free and open-source implementation of the X Window System
(X11) display server stewarded by the X.Org Foundation.


## Usage

This container image is intended for consumption via a helm chart which launches
the container in the intended fashion.

To launch the container manually, switch to a tty and execute the following
command as `root`:

```ShellSession
# podman run \
      --privileged -d \
      -e XAUTHORITY=/home/user/xauthority/.xauth \
      -v xauthority:/home/user/xauthority:rw \
      -v xsocket:/tmp/.X11-unix:rw \
      -v /run/udev/data:/run/udev/data:rw \
      --security-opt=no-new-privileges \
      registry.suse.com/suse/xorg:21
```

The volumes are optional and can be omitted if you wish to only start X. The
volumes are necessary to launch additional graphical applications using the
containerized Xorg container.


## Licensing

`SPDX-License-Identifier: MIT`

This documentation and the build recipe are licensed as MIT.
The container itself contains various software components under various open source licenses listed in the associated
Software Bill of Materials (SBOM).

This image is a tech preview. Do not use it for production.
Your feedback is welcome.
Please report any issues to the [SUSE Bugzilla](https://bugzilla.suse.com/enter_bug.cgi?product=SUSE%20Linux%20Enterprise%20Base%20Container%20Images).
