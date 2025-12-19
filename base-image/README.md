# SUSE Linux BCI 16.1 Base Container Image
![Redistributable](https://img.shields.io/badge/Redistributable-Yes-green)![Support Level](https://img.shields.io/badge/Support_Level-techpreview-blue)
[![SLSA](https://img.shields.io/badge/SLSA_(v0.1)-Level_4-Green)](https://documentation.suse.com/sbp/security/html/SBP-SLSA4/)
[![Provenance: Available](https://img.shields.io/badge/Provenance-Available-Green)](https://documentation.suse.com/container/all/html/Container-guide/index.html#container-verify)

## Description

SUSE Linux Base Container Images provide open, flexible,
and secure container images. The images include container environments based on
SUSE Linux Enterprise Server
and are available at no cost, may be freely redistributed under the BCI EULA,
and are supported across a large variety of environments.

This image serves as a foundation for many SUSE Linux BCIs. It is designed to
be extended for additional use cases, such as development or testing environments.


## Usage


The container image includes the `zypper` package manager
, the free `SLE_BCI` repository
and the `container-suseconnect` utility. This enables access to the full
SUSE Linux Enterprise Server repositories with a valid subscription.
The image is intended to be extended by installing packages required for your specific use case.

To build a custom image that includes the [`skopeo`](https://github.com/containers/skopeo) utility,
 use the following `Containerfile`:

```Dockerfile
FROM registry.suse.com/bci/bci-base:16.1
RUN set -euo pipefail; \
    zypper -n ref; \
    zypper -n install skopeo; \
    zypper -n clean -a ; \
    rm -rf /var/log/{lastlog,tallylog,zypper.log,zypp/history,YaST2}
```

Then build the container using `buildah`:
```bash
buildah bud -t bci-skopeo .
```

You can also use the image interactively to create a container with `skopeo` installed:

```ShellSession
$ podman run -ti --rm registry.suse.com/bci/bci-base:16.1
# zypper -n install skopeo
...
# skopeo inspect -f "{{ .Name }}" docker://registry.suse.com/bci/bci-base:16.1
registry.suse.com/bci/bci-base
```
### The SLE_BCI repository

The container image includes the free `SLE_BCI` repository, which provides
the latest versions of a subset of packages from SUSE Linux Enterprise Server.
These packages are available at no cost and may be freely redistributed.

### Getting access to the SUSE Linux repositories


The `container-suseconnect` utility in the image can automatically add the full
repositories into the running container if you have a valid
SUSE Linux Enterprise Server subscription.

Find more information about container-suseconnect in the
[`container-suseconnect`](https://documentation.suse.com/container/all/single-html/Container-guide/index.html#sec-container-suseconnect)
section in the container guide or in the tutorial ["How to use
container-suseconnect"](https://opensource.suse.com/bci-docs/guides/container-suseconnect/).



## Licensing

`SPDX-License-Identifier: MIT`

This documentation and the build recipe are licensed as MIT.
The container itself contains various software components under various open source licenses listed in the associated
Software Bill of Materials (SBOM).

This image is a tech preview. Do not use it for production.
Your feedback is welcome.
Please report any issues to the [SUSE Bugzilla](https://bugzilla.suse.com/enter_bug.cgi?product=PUBLIC%20SUSE%20Linux%20Enterprise%20Base%20Container%20Images).
