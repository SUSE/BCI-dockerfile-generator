# Rust 1.78 Container Image

![Redistributable](https://img.shields.io/badge/Redistributable-Yes-green)[![SLSA](https://img.shields.io/badge/SLSA_(v1.0)-Build_L3-Green)](https://documentation.suse.com/sbp/server-linux/html/SBP-SLSA4/)
[![Provenance: Available](https://img.shields.io/badge/Provenance-Available-Green)](https://documentation.suse.com/container/all/html/Container-guide/index.html#container-verify)

## Description

[Rust](https://www.rust-lang.org/) is a systems programming language sponsored by Mozilla Research. It is designed to be a safe, concurrent, practical language, supporting functional and imperative-procedural paradigms. While syntactically similar to C++, Rust is designed for better memory safety without performance penalty.

## Usage

To compile and deploy an application, copy the sources, fetch dependencies, and build the binary:

```Dockerfile
# Build the application using the Rust 1.78 container image
FROM registry.suse.com/bci/rust:1.78 as build

WORKDIR /app

COPY . ./

RUN cargo build --release

# Bundle the application into a BCI micro (or other BCI image)
FROM registry.suse.com/bci/bci-micro:latest

COPY --from=build /app/target/release/hello /usr/local/bin/hello

CMD ["hello"]
```

Build and run the container image:

```ShellSession
$ podman build -t my-rust-app .
$ podman run -it --rm my-rust-app
```

There are situations, where you don't want to run an application inside a container.

To compile the application, without running it inside a container instance, use the following command:

```ShellSession
$ podman run --rm -v "$PWD":/app:Z -w /app registry.suse.com/bci/rust:1.78 cargo build --release
```

**Note:** The Rust image is intended to be used as a build environment. For runtime, use smaller images such as `bci-base`, `bci-micro`, or `bci-minimal`.

## Licensing

`SPDX-License-Identifier: MIT`

This documentation and the build recipe are licensed as MIT.
The container itself contains various software components under various open source licenses listed in the associated
Software Bill of Materials (SBOM).

This image is based on [SLE BCI](https://opensource.suse.com/bci/), a stable and redistributable foundation for software innovation. SLE BCI is enterprise-ready, and it comes with an option for support.

See the [SLE BCI EULA](https://www.suse.com/licensing/eula/#bci) for further information.
