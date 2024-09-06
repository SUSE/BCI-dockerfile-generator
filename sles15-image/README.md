# SLE BCI 15 SP6 Base Container Image
![Redistributable](https://img.shields.io/badge/Redistributable-Yes-green)[![SLSA](https://img.shields.io/badge/SLSA_(v1.0)-Build_L3-Green)](https://documentation.suse.com/sbp/server-linux/html/SBP-SLSA4/)
[![Provenance: Available](https://img.shields.io/badge/Provenance-Available-Green)](https://documentation.suse.com/container/all/html/Container-guide/index.html#container-verify)

## Description

SUSE Linux Enterprise Base Container Images (SLE BCI) provide open, flexible,
and secure container images. The images include container environments based on
SUSE Linux Enterprise Server and are available at no cost, they can be freely
re-distributed, and they are supported across different environments.

The Base Container Image is an image used as a foundation for most SLE BCIs. The
image is intended to be extended for further use, such as a development or a
testing environment.


## Usage

The container image comes with the `zypper` package manager, the free `SLE_BCI`
repository and the `container-suseconnect` utility. This allows you to access to
the full SLE repositories with a valid SLE subscription. The image is designed
to be extended by installing packages required for your specific scenario.

To build a custom image using a `Containerfile` that includes the
[`skopeo`](https://github.com/containers/skopeo) utility, create the following
`Containerfile`:
```Dockerfile
FROM registry.suse.com/bci/bci-base:15.6
RUN set -euo pipefail; \
    zypper -n ref; \
    zypper -n in skopeo; \
    zypper -n clean; \
    rm -rf /var/log/{lastlog,tallylog,zypper.log,zypp/history,YaST2}
```

Then build the container using `buildah`:
```bash
buildah bud -t bci-skopeo .
```

The image can also be used interactively to create a container with skopeo
installed in it:
```ShellSession
$ podman run -ti --rm registry.suse.com/bci/bci-base:15.6
# zypper -n in skopeo
...
# skopeo inspect -f "{{ .Name }}" docker://registry.suse.com/bci/bci-base:15.6
registry.suse.com/bci/bci-base
```

### The SLE_BCI repository

The container image comes with the free `SLE_BCI` repository. The repository
contains a subset of all packages from SUSE Linux Enterprise. The packages are
available free of charge, and they can be redistributed freely. However, they
are provided without support. The repository also contains the latest version of
packages only.


### Getting access to the SLE repositories

The `container-suseconnect` utility in the image can automatically add the full
SUSE Linux Enterprise repositories into the running container if you have a
valid SLE subscription.

Find more information about container-suseconnect in the
[`container-suseconnect`](https://documentation.suse.com/container/all/single-html/Container-guide/index.html#sec-container-suseconnect)
section in the container guide or in the tutorial ["How to use
container-suseconnect"](https://opensource.suse.com/bci-docs/guides/container-suseconnect/).


## Licensing

`SPDX-License-Identifier: MIT`

This documentation and the build recipe are licensed as MIT.
The container itself contains various software components under various open source licenses listed in the associated
Software Bill of Materials (SBOM).

This image is based on [SLE BCI](https://opensource.suse.com/bci/), a stable and redistributable foundation for software innovation. SLE BCI is enterprise-ready, and it comes with an option for support.

See the [SLE BCI EULA](https://www.suse.com/licensing/eula/#bci) for further information.
