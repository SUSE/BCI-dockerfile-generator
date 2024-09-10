# The Podman Container Image

![Redistributable](https://img.shields.io/badge/Redistributable-Yes-green)

## Description

Podman (the POD MANager) is a tool for managing containers and images, volumes
mounted into those containers, and pods made from groups of containers. Podman
runs containers on Linux, but can also be used on Mac and Windows systems using
a Podman-managed virtual machine. Podman is based on libpod, a library for
container lifecycle management that.

This Container Image ships Podman pre-configured to allow running it inside a
container.


## Usage

This Container Image is intended for interactive usage only and it must be
launched in privileged mode:

```ShellSession
$ podman run --rm -it --privileged \
      registry.opensuse.org/opensuse/podman:%%podman_version%%
# podman run --rm -it leap grep ^ID= /etc/os-release
ID="opensuse-leap"
```

The container ships the unprivileged user `podman`, which can launch rootless
containers inside a container:
```ShellSession
$ podman run --rm -it --privileged \
      registry.opensuse.org/opensuse/podman:%%podman_version%%
# su podman
podman:/> podman run --rm -it leap grep ^ID= /etc/os-release
ID="opensuse-leap"
```


## Limitations

- The container must be run in privileged mode.
- Podman inside the container has to use the slow `fuse-overlayfs` storage
  driver. This driver is significantly slower than the default `overlay` driver,
  which is unavailable in a container.


## Licensing

`SPDX-License-Identifier: Apache-2.0`

This documentation and the build recipe are licensed as Apache-2.0.
The container itself contains various software components under various open source licenses listed in the associated
Software Bill of Materials (SBOM).

This image is based on [openSUSE Tumbleweed](https://get.opensuse.org/tumbleweed/).
