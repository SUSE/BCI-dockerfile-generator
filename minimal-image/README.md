# SLE BCI 15 SP6 Minimal: Base Container image without Zypper
![Redistributable](https://img.shields.io/badge/Redistributable-Yes-green)

## Description
This image comes without Zypper, but it does have the RPM package manager installed.
While RPM can install and remove packages, it lacks support for repositories and automated dependency resolution.
It is therefore intended for creating deployment containers, and then installing the desired
RPM packages inside the containers.

While you can install the required dependencies, you need to download and resolve them manually.
However, this approach is not recommended as it is prone to errors.

## Licensing

`SPDX-License-Identifier: MIT`

This documentation and the build recipe are licensed as MIT.
The container itself contains various software components under various open source licenses listed in the associated
Software Bill of Materials (SBOM).

This image is based on [SLE BCI](https://opensource.suse.com/bci/), a stable and redistributable foundation for software innovation. SLE BCI is enterprise-ready, and it comes with an option for support.

See the [SLE BCI EULA](https://www.suse.com/licensing/eula/#bci) for further information.
