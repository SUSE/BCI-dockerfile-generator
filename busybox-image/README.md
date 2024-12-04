# SLE LTSS BCI 15 SP5 BusyBox: the smallest and GPLv3-free image

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

This image is based on [SUSE Linux Enterprise Server](https://www.suse.com/products/server/), a reliable,
secure, and scalable server operating system built to power mission-critical workloads in physical and virtual environments.