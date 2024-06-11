# Go 1.20-openssl development Container Image

![Redistributable](https://img.shields.io/badge/Redistributable-Yes-green)
[![SLSA](https://img.shields.io/badge/SLSA_(v0.1)-Level_4-Green)](https://documentation.suse.com/sbp/server-linux/html/SBP-SLSA4/)
[![Provenance: Available](https://img.shields.io/badge/Provenance-Available-Green)](https://documentation.suse.com/container/all/html/Container-guide/index.html#container-verify)

## Description

[Go](https://go.dev/) (a.k.a., Golang) is a statically-typed programming language, with syntax loosely derived from C. Go offers additional features such as garbage collection, type safety, certain dynamic-typing capabilities, additional built-in types (for example, variable-length arrays and key-value maps) as well as a large standard library.

## Usage

To compile and deploy an application, copy the sources, fetch dependencies (assuming go.mod is used for dependency management), and build the binary:

```Dockerfile
# Build the application using the Go 1.20-openssl development Container Image
FROM registry.suse.com/bci/golang:1.20-openssl as build

WORKDIR /app

# pre-copy/cache go.mod for pre-downloading dependencies and only redownloading them in subsequent builds if they change
COPY go.mod go.sum ./
RUN go mod download && go mod verify

COPY . ./

# Make sure to build the application with CGO disabled.
# This will force Go to use some Go implementations of code
# rather than those normally supplied by the host operating system.
# You need this for scratch images as those supporting libraries
# are not available.
RUN CGO_ENABLED=0 go build -o /hello

# Bundle the application into a scratch image
FROM scratch

COPY --from=build /hello /hello

CMD ["/hello"]
```

Build and run the container image:

```ShellSession
$ podman build -t my-golang-app .
$ podman run -it --rm my-golang-app
```

There are situations when you don't want to run an application inside a container.

To compile the application, without running it inside a container instance, use the following command:

```ShellSession
$ podman run --rm -v "$PWD":/app:Z -w /app registry.suse.com/bci/golang:1.20-openssl go build -v
```

To run the application tests inside a container, use the following command:

```ShellSession
$ podman run --rm -v "$PWD":/app:Z -w /app registry.suse.com/bci/golang:1.20-openssl go test -v
```

**Note:** The Golang image should be used as a build environment. For runtime, self-contained Go binaries should use a `scratch` image and for applications that require external dependencies use the `bci-base` image.

## Additional tools

The following additional tools are included in the image:

- go1.20-openssl-race
- make
- git-core


## FIPS 140

The image includes a FIPS 140 enabled Go toolchain using OpenSSL.

To restrict all TLS configuration to FIPS-approved settings, add the following line:

```go
import _ "crypto/tls/fipsonly"
```


## Licensing

`SPDX-License-Identifier: MIT`

This documentation and the build recipe are licensed as MIT.
The container itself contains various software components under various open source licenses listed in the associated
Software Bill of Materials (SBOM).

This image is based on [SLE BCI](https://opensource.suse.com/bci/), a stable and redistributable foundation for software innovation. SLE BCI is enterprise-ready, and it comes with an option for support.

See the [SLE BCI EULA](https://www.suse.com/licensing/eula/#bci) for further information.
