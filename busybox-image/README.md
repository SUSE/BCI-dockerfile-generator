# SLE BCI Framework One BusyBox: the smallest and GPLv3-free image
![Redistributable](https://img.shields.io/badge/Redistributable-Yes-green)![Support Level](https://img.shields.io/badge/Support_Level-techpreview-blue)
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

This image is a tech preview. Do not use it for production.
Your feedback is welcome.
Please report any issues to the [SUSE Bugzilla](https://bugzilla.suse.com/enter_bug.cgi?product=SUSE%20Linux%20Enterprise%20Base%20Container%20Images).
