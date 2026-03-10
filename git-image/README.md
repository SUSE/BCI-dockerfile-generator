# SUSE Linux 16.1 with Git: Git application container
![Support Level](https://img.shields.io/badge/Support_Level-techpreview-blue)
[![SLSA](https://img.shields.io/badge/SLSA_(v0.1)-Level_4-Green)](https://documentation.suse.com/sbp/security/html/SBP-SLSA4/)
[![Provenance: Available](https://img.shields.io/badge/Provenance-Available-Green)](https://documentation.suse.com/container/all/html/Container-guide/index.html#container-verify)


## Description

Git is a distributed version control system that tracks
versions of files. Git is primarily designed for controlling source code in collaborative software development.


## Usage

This container provides the SUSE LLC version of Git.

Example of using Git container:

```ShellSession
$ podman run registry.suse.com/suse/git:2.53 git help
```

As Git requires a repository, the container
does not explicitly set an entrypoint. This way, you can launch the container in
interactive mode to clone a repository and work on it. The `/workspace` directory is declared as a volume to persist changes.

Example with volume mounting for persistence:

```ShellSession
$ podman run -it -v $(pwd):/workspace:Z registry.suse.com/suse/git:2.53 git clone <repository-url>
```

Example running as a non-root user:

```ShellSession
$ podman run -it --user git --userns=keep-id -v $(pwd):/workspace:Z registry.suse.com/suse/git:2.53 git clone <repository-url>
```

Or with your host user ID:

```ShellSession
$ podman run -it --user $(id -u):$(id -g) --userns=keep-id -v $(pwd):/workspace registry.suse.com/suse/git:2.53 git clone <repository-url>
```

## Cloning Private Repositories

To clone private repositories that require SSH authentication, mount your SSH directory into the container:

```ShellSession
$ podman run -it --user $(id -u):$(id -g) --userns=keep-id -v $(pwd):/workspace:Z -v ~/.ssh:/workspace/.ssh:Z registry.suse.com/suse/git:2.53 git clone <private-repository-url>
```

Ensure your SSH private key has the correct permissions (e.g., `chmod 600 ~/.ssh/id_rsa` on the host) and that your SSH configuration is set up properly.

For more use cases and documentation, refer to the
[Git SCM documentation](https://git-scm.com/doc).


## Licensing

`SPDX-License-Identifier: GPL-2.0-only`

This documentation and the build recipe are licensed as GPL-2.0-only.
The container itself contains various software components under various open source licenses listed in the associated
Software Bill of Materials (SBOM).

This image is a tech preview. Do not use it for production.
Your feedback is welcome.
Please report any issues to the [SUSE Bugzilla](https://bugzilla.suse.com/enter_bug.cgi?product=PUBLIC%20SUSE%20Linux%20Enterprise%20Base%20Container%20Images).
