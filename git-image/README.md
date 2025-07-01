# SLE 16 with Git: Git application container
![Support Level](https://img.shields.io/badge/Support_Level-techpreview-blue)
[![SLSA](https://img.shields.io/badge/SLSA_(v0.1)-Level_4-Green)](https://documentation.suse.com/sbp/server-linux/html/SBP-SLSA4/)
[![Provenance: Available](https://img.shields.io/badge/Provenance-Available-Green)](https://documentation.suse.com/container/all/html/Container-guide/index.html#container-verify)


## Description

Git is a distributed version control system that tracks
versions of files. Git is primarily designed for controlling source code in collaborative software development.


## Usage

This container provides the SUSE LLC version of Git.

Example of using Git container:

```ShellSession
$ podman run registry.suse.com/suse/git:2.46 git help
```

As Git requires a repository, the container
does not explicitly set an entrypoint. This way, you can launch the container in
interactive mode to clone a repository and work on it. To avoid losing all your changes when exiting the container, use a persistent volume mount on launch.

For more use cases and documentation, refer to the
[Git SCM documentation](https://git-scm.com/doc).


## Licensing

`SPDX-License-Identifier: GPL-2.0-only`

This documentation and the build recipe are licensed as GPL-2.0-only.
The container itself contains various software components under various open source licenses listed in the associated
Software Bill of Materials (SBOM).

This image is a tech preview. Do not use it for production.
Your feedback is welcome.
Please report any issues to the [SUSE Bugzilla](https://bugzilla.suse.com/enter_bug.cgi?product=SUSE%20Linux%20Enterprise%20Base%20Container%20Images).
