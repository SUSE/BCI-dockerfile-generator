# SLE BCI 15 SP6 BusyBox: the smallest and GPLv3-free image
![Redistributable](https://img.shields.io/badge/Redistributable-Yes-green)
[![SLSA](https://img.shields.io/badge/SLSA_(v0.1)-Level_4-Green)](https://documentation.suse.com/sbp/server-linux/html/SBP-SLSA4/)
[![Provenance: Available](https://img.shields.io/badge/Provenance-Available-Green)](https://documentation.suse.com/container/all/html/Container-guide/index.html#container-verify)

## Description
This image comes with the most basic tools provided by the BusyBox project.
The image contains no GPLv3 licensed software. When using the image, keep in mind that
there are differences between the BusyBox tools and the GNU Coreutils.
This means that scripts written for a system that uses GNU Coreutils may require
modification to work with BusyBox. If you need a SLES compatible image with the GNU Coreutils,
consider using the corresponding Micro image instead.

## Licensing

`SPDX-License-Identifier: MIT`

This documentation and the build recipe are licensed as MIT.
The container itself contains various software components under various open source licenses listed in the associated
Software Bill of Materials (SBOM).

This image is based on [SLE BCI](https://opensource.suse.com/bci/), a stable and redistributable foundation for software innovation. SLE BCI is enterprise-ready, and it comes with an option for support.

See the [SLE BCI EULA](https://www.suse.com/licensing/eula/#bci) for further information.