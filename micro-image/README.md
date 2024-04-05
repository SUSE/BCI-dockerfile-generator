# SLE BCI-Micro: Suitable for deploying static binaries

This image is similar to SLE BCI-Minimal but without the RPM package manager.
The primary use case for the image is deploying static binaries produced
externally or during multi-stage builds. As there is no straightforward
way to install additional dependencies inside the container image,
we recommend deploying a project using the SLE BCI-Minimal image only
when the final build artifact bundles all dependencies and has no
external runtime requirements (like Python or Ruby).

## Licensing
`SPDX-License-Identifier: MIT`

The build recipe and this documentation is licensed as MIT.
The container itself contains various software components under various open source licenses listed in the associated
Software Bill of Materials (SBOM).

This image is a tech preview. Do not use it for production.
Your feedback is welcome.
Please report any issues to the [SUSE Bugzilla](https://bugzilla.suse.com/enter_bug.cgi?product=SUSE%20Linux%20Enterprise%20Base%20Container%20Images).
