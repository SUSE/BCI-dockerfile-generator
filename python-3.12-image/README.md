# Python 3.12 development container image

![Redistributable](https://img.shields.io/badge/Redistributable-Yes-green)![Support Level](https://img.shields.io/badge/Support_Level-techpreview-blue)[![SLSA](https://img.shields.io/badge/SLSA_(v1.0)-Build_L3-Green)](https://documentation.suse.com/sbp/server-linux/html/SBP-SLSA4/)
[![Provenance: Available](https://img.shields.io/badge/Provenance-Available-Green)](https://documentation.suse.com/container/all/html/Container-guide/index.html#container-verify)

## Description

[Python](https://www.python.org/) is an interpreted, interactive, object-oriented, open-source programming language. It incorporates modules, exceptions, dynamic typing, high-level dynamic data types, and classes. It provides interfaces to many system calls, libraries, and various window systems, and it is extensible in C or C++. It is also usable as an extension language for applications that require programmable interfaces.

## Usage

To deploy an application, install dependencies, copy the sources, and configure the application's main script:

```Dockerfile
FROM registry.suse.com/bci/python:3.12

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
$ podman run --rm -v "$PWD":/app:Z -w /app registry.suse.com/bci/python:3.12 python3 script.py
```

## Additional tools

The Python container image includes [pip](https://pip.pypa.io/), [pipx](https://pipx.pypa.io/), Python Development Headers, and Git.

## Licensing

`SPDX-License-Identifier: MIT`

This documentation and the build recipe are licensed as MIT.
The container itself contains various software components under various open source licenses listed in the associated
Software Bill of Materials (SBOM).

This image is a tech preview. Do not use it for production.
Your feedback is welcome.
Please report any issues to the [SUSE Bugzilla](https://bugzilla.suse.com/enter_bug.cgi?product=SUSE%20Linux%20Enterprise%20Base%20Container%20Images).
