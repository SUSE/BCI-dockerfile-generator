# .NET SDK 8.0 container image

![Redistributable](https://img.shields.io/badge/Redistributable-Yes-green)![Support Level](https://img.shields.io/badge/Support_Level-techpreview-blue)
[![SLSA](https://img.shields.io/badge/SLSA_(v0.1)-Level_4-Green)](https://documentation.suse.com/sbp/server-linux/html/SBP-SLSA4/)
[![Provenance: Available](https://img.shields.io/badge/Provenance-Available-Green)](https://documentation.suse.com/container/all/html/Container-guide/index.html#container-verify)

## Description

.NET is a general purpose development platform.
It is cross-platform, and can be used in devices, cloud, and embedded/IoT scenarios.
You can use C# or F# to write .NET applications.

This image contains the .NET SDK, consisting of three parts:

- .NET CLI
- .NET Runtime
- ASP.NET Core Runtime

You can use the image to develop, build, and test of .NET and ASP.NET Core applications.

## Notice

The .NET packages in the image come from a third-party repository 
[packages.microsoft.com](https://packages.microsoft.com).

The source code is available on [github.com/dotnet](https://github.com/dotnet).

SUSE does not provide any support or warranties for the third-party components in the image.

## Usage

To compile an application, copy the sources and build the binary:

```Dockerfile
FROM registry.suse.com/bci/dotnet-sdk:8.0 AS build
WORKDIR /source

# copy csproj and restore as distinct layers
COPY *.csproj .
RUN dotnet restore

# copy and publish app and libraries
COPY . .
RUN dotnet publish --no-restore -o /app

# final image
FROM registry.suse.com/bci/dotnet-runtime:8.0
WORKDIR /app
COPY --from=build /app .

# uncomment to run as non-root user
# USER $APP_UID

ENTRYPOINT ["./dotnetapp"]
```

Build and run the container image:

```ShellSession
podmanbuild -t my-dotnet-app .
podman run -it --rm my-dotnet-app
```

There are situations, where you don't want to run an application inside a container.

To compile the application without running it inside a container, use the following command:

```ShellSession
podman run --rm -v "$PWD":/app:Z -w /app registry.suse.com/bci/dotnet-sdk:8.0 dotnet run
```

To run unit tests in an isolated environment, use the following command:

```ShellSession
podman run --rm -v "$PWD":/app:Z -w /app/tests registry.suse.com/bci/dotnet-sdk:8.0 dotnet test --logger:trx
```

## Globalization

.NET includes [globalization](https://learn.microsoft.com/dotnet/core/extensions/globalization-and-localization) capabilities, including support for processing natural language text, calendars, currency, and timezones. The .NET implementation for these capabilities is based on system libraries available in the container image, such as [International Components for Unicode (ICU)](https://icu.unicode.org/) and [tzdata](https://wikipedia.org/wiki/Tz_database).

It's considered a good practice to pass timezone information into a container via environment variable `TZ`.

```bash
podman run --rm -it -e TZ="Europe/Berlin" app
```

## Licensing

`SPDX-License-Identifier: MIT`

This documentation and the build recipe are licensed as MIT.
The container itself contains various software components under various open source licenses listed in the associated
Software Bill of Materials (SBOM).

This image is a tech preview. Do not use it for production.
Your feedback is welcome.
Please report any issues to the [SUSE Bugzilla](https://bugzilla.suse.com/enter_bug.cgi?product=SUSE%20Linux%20Enterprise%20Base%20Container%20Images).
