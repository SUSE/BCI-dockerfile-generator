# NVIDIA Driver 570.211.01 Container Image
![Support Level](https://img.shields.io/badge/Support_Level-techpreview-blue)[![SLSA](https://img.shields.io/badge/SLSA_(v1.0)-Build_L3-Green)](https://documentation.suse.com/sbp/security/html/SBP-SLSA4/)
[![Provenance: Available](https://img.shields.io/badge/Provenance-Available-Green)](https://documentation.suse.com/container/all/html/Container-guide/index.html#container-verify)

## Description

The NVIDIA Driver container image provides NVIDIA GPU drivers in a
containerized environment. This image is based on
SUSE Linux Enterprise Server and includes both the
open-source and proprietary NVIDIA kernel modules, along with the necessary
user-space tools.

It is specifically designed for use with the NVIDIA GPU Operator or for manual
driver deployment on container hosts. This image includes the NVIDIA driver
570.211.01.

## Usage

The container is intended to be run with high privileges (`--privileged`) and
requires access to several host directories to properly load and manage kernel
modules.


## Licensing

`SPDX-License-Identifier: NVIDIA DEEP LEARNING CONTAINER LICENSE`

This documentation and the build recipe are licensed as NVIDIA DEEP LEARNING CONTAINER LICENSE.
The container itself contains various software components under various open source licenses listed in the associated
Software Bill of Materials (SBOM).

This image is a tech preview. Do not use it for production.
Your feedback is welcome.
Please report any issues to the [SUSE Bugzilla](https://bugzilla.suse.com/enter_bug.cgi?product=PUBLIC%20SUSE%20Linux%20Enterprise%20Base%20Container%20Images).
