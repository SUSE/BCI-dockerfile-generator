# Python 3.6 development container image

![Redistributable](https://img.shields.io/badge/Redistributable-Yes-green)
[![SLSA](https://img.shields.io/badge/SLSA_(v0.1)-Level_4-Green)](https://documentation.suse.com/sbp/server-linux/html/SBP-SLSA4/)
[![Provenance: Available](https://img.shields.io/badge/Provenance-Available-Green)](https://documentation.suse.com/container/all/html/Container-guide/index.html#container-verify)

## Description

[Python](https://www.python.org/) is an interpreted, interactive, object-oriented, open-source programming language. It incorporates modules, exceptions, dynamic typing, high-level dynamic data types, and classes. It provides interfaces to many system calls, libraries, and various window systems, and it is extensible in C or C++. It is also usable as an extension language for applications that require programmable interfaces.

## Usage

To deploy an application, install dependencies, copy the sources, and configure the application's main script:

```Dockerfile
FROM registry.suse.com/bci/python:3.6

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD [ "python3", "./main-script.py" ]
```

Build and run the container image:

```ShellSession
$ podman build -t my-python-app .
$ podman run -it --rm my-python-app
```

To run a single script inside a container, use the following command:

```ShellSession
$ podman run --rm -v "$PWD":/app:Z -w /app registry.suse.com/bci/python:3.6 python3 script.py
```

## Additional tools

The Python container image includes [pip](https://pip.pypa.io/), [wheel](https://wheel.readthedocs.io/), Python Development Headers, and Git.

## Licensing

`SPDX-License-Identifier: MIT`

This documentation and the build recipe are licensed as MIT.
The container itself contains various software components under various open source licenses listed in the associated
Software Bill of Materials (SBOM).

This image is based on [SLE BCI](https://opensource.suse.com/bci/), a stable and redistributable foundation for software innovation. SLE BCI is enterprise-ready, and it comes with an option for support.

See the [SLE BCI EULA](https://www.suse.com/licensing/eula/#bci) for further information.