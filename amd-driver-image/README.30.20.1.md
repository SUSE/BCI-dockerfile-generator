# AMD GPU Driver 30.20.1 Container Image

![Support Level](https://img.shields.io/badge/Support_Level-techpreview-blue)[![SLSA](https://img.shields.io/badge/SLSA_(v1.0)-Build_L3-Green)](https://documentation.suse.com/sbp/security/html/SBP-SLSA4/)
[![Provenance: Available](https://img.shields.io/badge/Provenance-Available-Green)](https://documentation.suse.com/container/all/html/Container-guide/index.html#container-verify)

## Description

The AMD GPU Driver container image provides precompiled `amdgpu` kernel
modules and firmware in a containerized environment. This image is based on
SUSE Linux Enterprise Server and includes the `amdgpu`
driver built against the codestream GA kernel, with driver sources and firmware
sourced from [repo.radeon.com/amdgpu](https://repo.radeon.com/amdgpu/).

It is designed for use with the [AMD ROCm GPU Operator](https://github.com/ROCm/gpu-operator).
On SLES nodes, the operator uses this image as a build source:
KMM (Kernel Module Management) pulls the precompiled modules from this image
and relocates them to the target running kernel path using SUSE's stable kABI
guarantee — meaning a single driver image built against the GA kernel works for
any kernel update within the same codestream, without requiring driver
recompilation or a support subscription.

## Usage

To deploy this image, [install the AMD ROCm GPU Operator](https://instinct.docs.amd.com/projects/gpu-operator/en/latest/usage.html#installing-the-gpu-operator) using the [Helm chart](https://instinct.docs.amd.com/projects/gpu-operator/en/latest/installation/kubernetes-helm.html#installing-operator)
and set the driver version in the [DeviceConfig manifest](https://instinct.docs.amd.com/projects/gpu-operator/en/latest/fulldeviceconfig.html#full-deviceconfig):

```yaml
spec:
  driver:
    driverType: container
    # Set to true to enable the operator to install out-of-tree amdgpu kernel module
    enable: true
    # Specify your repository to host driver image (do not include the image tag and delete any existing DeviceConfig)
    image: "<your-registry>/amdgpu-driver"
    # Specify the driver version you would like to be installed that coincides with a ROCm version number
    version: "30.20.1"
```

The operator will automatically select the correct prebuilt image from
the SUSE Registry for the SLES codestream running on your nodes.

## Licensing

`SPDX-License-Identifier: GPL-2.0 WITH Linux-syscall-note`

This documentation and the build recipe are licensed as GPL-2.0 WITH Linux-syscall-note.
The container itself contains various software components under various open source licenses listed in the associated
Software Bill of Materials (SBOM).

This image is a tech preview. Do not use it for production.
Your feedback is welcome.
Please report any issues to the [SUSE Bugzilla](https://bugzilla.suse.com/enter_bug.cgi?product=PUBLIC%20SUSE%20Linux%20Enterprise%20Base%20Container%20Images).
