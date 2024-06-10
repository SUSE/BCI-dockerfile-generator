# Basalt Project BCI Adaptable Linux Platform Minimal: Base Container image without Zypper
![Redistributable](https://img.shields.io/badge/Redistributable-Yes-green)![Support Level](https://img.shields.io/badge/Support_Level-techpreview-blue)

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

This image is a tech preview. Do not use it for production.
Your feedback is welcome.
Please report any issues to the [SUSE Bugzilla](https://bugzilla.suse.com/enter_bug.cgi?product=SUSE%20Linux%20Enterprise%20Base%20Container%20Images).
