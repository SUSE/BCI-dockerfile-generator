# Go 1.25-openssl development container image

![Redistributable](https://img.shields.io/badge/Redistributable-Yes-green)[![SLSA](https://img.shields.io/badge/SLSA_(v1.0)-Build_L3-Green)](https://documentation.suse.com/sbp/security/html/SBP-SLSA4/)
[![Provenance: Available](https://img.shields.io/badge/Provenance-Available-Green)](https://documentation.suse.com/container/all/html/Container-guide/index.html#container-verify)

## Description

[Go](https://go.dev/) (a.k.a. Golang) is a statically-typed programming
language, with syntax loosely derived from C. Go offers additional features
such as garbage collection, type safety, certain dynamic-typing capabilities,
additional built-in types (for example, variable-length arrays and key-value
maps) and a large standard library.

## FIPS 140-3

This container image includes a FIPS 140-3-enabled Go toolchain wrapper that
routes cryptographic operations through OpenSSL when available at runtime.
This allows applications to use FIPS 140-3-validated routines provided by the
system OpenSSL library in the container environment.

### Restricting TLS configuration in Go-openssl

To restrict all TLS configurations to FIPS-approved settings when using Go-openssl,
add the following import to your Go application:

```go
import _ "crypto/tls/fipsonly"
```

### Migrating from Go-openssl to the native Go FIPS 140-3 cryptographic module

Go binaries can natively operate in a mode that facilitates
[FIPS 140-3 compliance](https://go.dev/doc/security/fips140).

Starting with SLE BCI Go 1.27, the Go-openssl variant—which routes cryptographic
operations through OpenSSL—will no longer be supported or provided in SLE BCI.
Users requiring FIPS 140-3 compliance must migrate to the standard Go container
image (`registry.suse.com/bci/golang:<version>`), which uses Go's native in-tree
cryptographic module.

#### Why migrate to native Go FIPS 140-3?

Go natively includes an in-tree cryptographic module
(`crypto/internal/fips140`) certified under NIST's Cryptographic Module
Validation Program (CMVP). Migrating from Go-openssl to native Go FIPS offers
several advantages:

- **Pure Go static binaries**: Applications can be compiled with `CGO_ENABLED=0`
  to produce fully static, self-contained binaries.
- **Ultra-minimal deployment containers**: Because OpenSSL is no longer required
  at runtime, applications can be deployed in minimal container images such as
  `bci-nano`, drastically reducing resulting container size.

#### Step-by-step migration guide

##### 1. Switch to the standard Go container image

In your `Dockerfile` or build configuration, replace the Go-openssl image reference
with the standard Go container image:

```Dockerfile
# Deprecated:
# FROM registry.suse.com/bci/golang:1.25-openssl AS build

# Migrated:
FROM registry.suse.com/bci/golang:1.25 AS build
```

##### 2. Enable FIPS 140-3 mode at build time (`GOFIPS140=certified`)

When compiling your application, set the `GOFIPS140` environment variable to
`certified` with `go build`, `go install`, or `go test`:

```ShellSession
$ GOFIPS140=certified go build -o myapp .
```

In a `Dockerfile`:

```Dockerfile
ENV GOFIPS140=certified
RUN go build -o /hello .
```

Or inline:

```Dockerfile
RUN GOFIPS140=certified go build -o /hello .
```

**What `GOFIPS140=certified` does:**
- It links your application against the latest frozen snapshot of the Go
  Cryptographic Module that has achieved an official NIST CMVP validation certificate.
- It automatically configures the compiled binary to execute in FIPS 140-3 mode
  by default (`fips140=on`) at runtime. No additional runtime environment variables
  are required for the binary to operate in FIPS mode.

##### 3. Configure runtime settings (`GODEBUG=fips140`)

Binaries built with `GOFIPS140=certified` run in FIPS mode automatically. The Go
runtime controls FIPS behavior via the `fips140` option in the `GODEBUG` environment
variable:

- **`fips140=on`**: Enables FIPS 140-3 mode. The binary runs Power-On Self-Tests (POST)
  during startup and key generation, generates random numbers using the approved
  SP 800-90A DRBG, and restricts TLS configurations to approved algorithms. This is
  the default behavior for binaries built with `GOFIPS140=certified`.
- **`fips140=only`**: Strict FIPS 140-3 mode. Any invocation of a non-approved
  cryptographic algorithm or unapproved key size immediately returns an error or
  panics. This mode is recommended in testing and CI/CD pipelines to verify that no
  unapproved algorithms are called.
- **`fips140=off`**: Disables FIPS 140-3 mode.

To set this option when executing a container:

```ShellSession
$ podman run -e GODEBUG="fips140=on" my-golang-app
```

##### 4. Verify the compiled binary

You can verify that a binary contains the validated cryptographic module snapshot
by inspecting its build metadata:

```ShellSession
$ go version -m /path/to/myapp
```

The output indicates the embedded cryptographic module version under
`crypto/internal/fips140`.

##### 5. Review TLS settings (`crypto/tls/fipsonly`)

If your existing application imported `crypto/tls/fipsonly`:

```go
import _ "crypto/tls/fipsonly"
```

In native Go FIPS mode (`fips140=on`), the standard `crypto/tls` package
automatically restricts cipher suites, elliptic curves, and protocol versions
to FIPS-approved algorithms (TLS 1.2 and TLS 1.3). The `crypto/tls/fipsonly` import
remains supported for backward compatibility, but is no longer required and can
safely be removed from your codebase.


## Usage
We recommend using the Go image solely as a build environment so that
the compiler does not need to be shipped as part of deployed images.

There are two options for working with Go images. First, you can encapsulate your
application in a `bci-nano` container image, a minimal runtime environment containing
only basic locale data and CA certificates. This approach only works if your Go application does not
depend on libc or any other libraries or binaries, as they will not be available.

The second option uses a slim base container image (such as `bci-micro`) with the minimal
packages required to run the Go application.

To compile and deploy an application, copy the sources, fetch dependencies
(assuming `go.mod` is used for dependency management), and build the binary using
the following Dockerfile options.


### Building from `bci-nano`

```Dockerfile
# Build the application using the Go 1.25-openssl development container image
FROM registry.suse.com/bci/golang:1.25-openssl AS build

WORKDIR /app

# Pre-copy/cache go.mod for pre-downloading dependencies and only
# redownloading them in subsequent builds if they change
COPY go.mod go.sum ./
RUN go mod download && go mod verify

COPY . ./

# Disable CGO to create a statically linked binary using Go's built-in
# implementations rather than host operating system C libraries. This is
# required for bci-nano images as C runtime libraries (libc) are not available.
RUN CGO_ENABLED=0 go build -o /hello

# Bundle the application into a bci-nano image
FROM registry.suse.com/bci/bci-nano:latest

COPY --from=build /hello /usr/local/bin/hello

CMD ["/usr/local/bin/hello"]
```

Build and run the container image:

```ShellSession
$ podman build -t my-golang-app .
$ podman run -it --rm my-golang-app
```

To compile an application on the host using the containerized Go toolchain (without creating an application container image), run:

```ShellSession
$ podman run --rm -v "$PWD":/app:Z -w /app registry.suse.com/bci/golang:1.25-openssl go build -v
```

To run application tests inside a container, run:

```ShellSession
$ podman run --rm -v "$PWD":/app:Z -w /app registry.suse.com/bci/golang:1.25-openssl go test -v
```


### Building from SLE BCI

The [SLE BCI General Purpose Base Container Images](https://opensource.suse.com/bci-docs/documentation/general-purpose-bci/)
documentation describes four different options for deployment, depending on your exact requirements.

```Dockerfile
# Build the application using the Go 1.25-openssl development container image
FROM registry.suse.com/bci/golang:1.25-openssl AS build

WORKDIR /app

# Pre-copy/cache go.mod for pre-downloading dependencies and only
# redownloading them in subsequent builds if they change
COPY go.mod go.sum ./
RUN go mod download && go mod verify

COPY . ./

RUN go build -o /hello

# Bundle the application into a bci-micro image
FROM registry.suse.com/bci/bci-micro:latest

COPY --from=build /hello /usr/local/bin/hello

CMD ["/usr/local/bin/hello"]
```

The above example uses the SLE BCI micro image as the deployment image for
the resulting application. See the [SLE BCI use with Go
documentation](https://opensource.suse.com/bci-docs/guides/use-with-golang/)
for further details.


## Additional tools

In addition to the standard SLE BCI development packages, the following tools
are included in the image:

- go1.25-openssl-race
- make

## Licensing

`SPDX-License-Identifier: MIT`

This documentation and the build recipe are licensed as MIT.
The container itself contains various software components under various open source licenses listed in the associated
Software Bill of Materials (SBOM).

This image is based on [SLE BCI](https://opensource.suse.com/bci/), a stable and redistributable foundation for software innovation. SLE BCI is enterprise-ready, and it comes with an option for support.

See the [SLE BCI EULA](https://www.suse.com/licensing/eula/#bci) for further information.
