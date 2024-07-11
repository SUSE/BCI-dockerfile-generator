# OpenJDK 17 runtime container image

![Redistributable](https://img.shields.io/badge/Redistributable-Yes-green)
[![SLSA](https://img.shields.io/badge/SLSA_(v0.1)-Level_4-Green)](https://documentation.suse.com/sbp/server-linux/html/SBP-SLSA4/)
[![Provenance: Available](https://img.shields.io/badge/Provenance-Available-Green)](https://documentation.suse.com/container/all/html/Container-guide/index.html#container-verify)

## Description

[OpenJDK](https://openjdk.org/) (Open Java Development Kit) is a free and open source implementation of the Java Platform, Standard Edition (Java SE). OpenJDK is the official reference implementation of Java SE since version 7.

The OpenJDK runtime image is intended to be used as a runtime environment. For development, use the OpenJDK development image.

## Usage

To run a jar or war application inside a container instance, use the following command:

```ShellSession
$ podman run --rm -v "$PWD":/app:Z -w /app registry.suse.com/bci/openjdk:17 java -jar hello.jar
```

Or create a new contained based on OpenJDK 17 runtime image:

```Dockerfile
FROM registry.suse.com/bci/openjdk:17

WORKDIR /app

COPY . ./

CMD ["java", "-jar", "hello.jar"]
```

To compile and deploy an application, copy the sources and build the application:

```Dockerfile
# Build the application using the OpenJDK development image
FROM registry.suse.com/bci/openjdk-devel:17  as build

WORKDIR /app

COPY . ./

RUN javac Hello.java

# Bundle the application into OpenJDK runtime image
FROM registry.suse.com/bci/openjdk:17

WORKDIR /app

COPY --from=build /app/Hello.class /app

CMD ["java", "Hello"]
```

Build and run the container image:

```ShellSession
$ podman build -t my-java-app .
$ podman run -it --rm my-java-app
```

## Licensing

`SPDX-License-Identifier: MIT`

This documentation and the build recipe are licensed as MIT.
The container itself contains various software components under various open source licenses listed in the associated
Software Bill of Materials (SBOM).

This image is based on [SLE BCI](https://opensource.suse.com/bci/), a stable and redistributable foundation for software innovation. SLE BCI is enterprise-ready, and it comes with an option for support.

See the [SLE BCI EULA](https://www.suse.com/licensing/eula/#bci) for further information.
