# SLE BCI 15 SP7 Nano: Suitable for deploying static binaries
![Redistributable](https://img.shields.io/badge/Redistributable-Yes-green)[![SLSA](https://img.shields.io/badge/SLSA_(v1.0)-Build_L3-Green)](https://documentation.suse.com/sbp/security/html/SBP-SLSA4/)
[![Provenance: Available](https://img.shields.io/badge/Provenance-Available-Green)](https://documentation.suse.com/container/all/html/Container-guide/index.html#container-verify)

## Description

The `bci-nano` image is providing timezone and TLS trusted CA certificates,
but no shell or glibc. This means that the image is smaller than `bci-micro`.
The primary use case for the image is deploying static binaries produced
externally or during multi-stage builds which do not require any shell
environment.


## Usage

As there is no straightforward way to install additional
dependencies inside the container image, we recommend deploying a project
using the `bci-nano` image only when the final build artifact bundles all
dependencies and needs no further installation of packages.

Example using a Go application:

```Dockerfile
FROM registry.suse.com/bci/golang:stable as build

WORKDIR /app

RUN go install github.com/go-training/helloworld@latest

# Create an image to bundle the app
FROM registry.suse.com/bci/bci-nano:latest

COPY --from=build /go/bin/helloworld /usr/local/bin/helloworld

CMD ["/usr/local/bin/helloworld"]
```


## Licensing

`SPDX-License-Identifier: MIT`

This documentation and the build recipe are licensed as MIT.
The container itself contains various software components under various open source licenses listed in the associated
Software Bill of Materials (SBOM).

This image is based on [SLE BCI](https://opensource.suse.com/bci/), a stable and redistributable foundation for software innovation. SLE BCI is enterprise-ready, and it comes with an option for support.

See the [SLE BCI EULA](https://www.suse.com/licensing/eula/#bci) for further information.
