"""Common Definitions for the SUSE containers."""

import textwrap

from bci_build.container_attributes import Arch
from bci_build.container_attributes import SupportLevel
from bci_build.os_version import OsVersion
from bci_build.package import DOCKERFILE_RUN
from bci_build.package import ApplicationStackContainer
from bci_build.package import ParseVersion
from bci_build.package import Replacement
from bci_build.package.helpers import generate_from_image_tag
from bci_build.package.helpers import generate_package_version_check
from bci_build.package.versions import get_pkg_version
from bci_build.registry import SUSERegistry

KUBEVIRT_EXCLUSIVE_ARCH = [Arch.X86_64]

VERSION_SUFFIXES = {"1.5.2": "r1"}


class KubeVirtRegistry(SUSERegistry):
    """Registry for KubeVirt containers."""

    @staticmethod
    def registry_prefix(*, is_application: bool) -> str:
        if not is_application:
            raise RuntimeError("KubeVirt containers must be Application Containers")
        return "suse/sles/16.0"


def _get_kubevirt_kwargs(
    service: str, os_version: OsVersion, *, user=None, custom_end=True
) -> dict:
    """Generate common kwargs for KubeVirt containers."""

    if user is None:
        user = "1001"
    kubevirt_version = get_pkg_version("kubevirt", os_version)
    tag_version = kubevirt_version
    if tag_version not in VERSION_SUFFIXES:
        raise ValueError(f"Unknown KubeVirt version: {tag_version}")
    tag_version += f"{VERSION_SUFFIXES[tag_version]}"
    return {
        "name": f"virt-{service}",
        "pretty_name": f"KubeVirt virt-{service} container",
        "license": "Apache-2.0",
        "os_version": os_version,
        "tag_version": tag_version,
        "version": (kubevirt_re := f"%%kubevirt_virt_{service}_ver%%"),
        "replacements_via_service": [
            Replacement(
                kubevirt_re,
                package_name=f"kubevirt-virt-{service}",
                parse_version=ParseVersion.PATCH,
            )
        ],
        "is_singleton_image": True,
        "is_latest": False,
        "version_in_uid": False,
        "entrypoint_user": user if user != "0" else None,
        "exclusive_arch": KUBEVIRT_EXCLUSIVE_ARCH,
        "support_level": SupportLevel.CUSTOM_BUILD_ARG,
        "_publish_registry": (
            KubeVirtRegistry() if os_version == OsVersion.SL16_0 else None
        ),
        "from_target_image": generate_from_image_tag(os_version, "bci-micro"),
        "build_stage_custom_end": (
            generate_package_version_check(
                f"kubevirt-virt-{service}",
                kubevirt_version,
                ParseVersion.PATCH,
                use_target=True,
            )
            + (
                textwrap.dedent(f"""
            {DOCKERFILE_RUN} useradd -u {user} --create-home -s /bin/bash virt-{service}
            """)
                if user == "1001"
                else ""
            )
        ),
    } | (
        {
            "custom_end": textwrap.dedent(f"""
            COPY --from=builder /etc/passwd /etc/passwd
            COPY --from=builder /etc/group /etc/group
            COPY --from=builder /home/virt-{service} /home/virt-{service}
            """),
        }
        if custom_end
        else {}
    )


KUBEVIRT_CONTAINERS = (
    [
        ApplicationStackContainer(
            **_get_kubevirt_kwargs("api", os_version),
            package_list=sorted(["kubevirt-virt-api", "shadow"]),
            entrypoint=["/usr/bin/virt-api"],
        )
        for os_version in (OsVersion.SL16_0, OsVersion.TUMBLEWEED)
    ]
    + [
        ApplicationStackContainer(
            **_get_kubevirt_kwargs("controller", os_version),
            package_list=sorted(["kubevirt-virt-controller", "shadow"]),
            entrypoint=["/usr/bin/virt-controller"],
        )
        for os_version in (OsVersion.SL16_0, OsVersion.TUMBLEWEED)
    ]
    + [
        ApplicationStackContainer(
            **_get_kubevirt_kwargs("exportproxy", os_version),
            package_list=sorted(["kubevirt-virt-exportproxy", "shadow"]),
            entrypoint=["/usr/bin/virt-exportproxy"],
        )
        for os_version in (OsVersion.SL16_0, OsVersion.TUMBLEWEED)
    ]
    + [
        ApplicationStackContainer(
            **_get_kubevirt_kwargs("exportserver", os_version, user="107"),
            package_list=sorted(
                ["kubevirt-virt-exportserver", "system-user-qemu", "tar"]
            ),
            entrypoint=["/usr/bin/virt-exportserver"],
        )
        for os_version in (OsVersion.SL16_0, OsVersion.TUMBLEWEED)
    ]
    + [
        ApplicationStackContainer(
            **_get_kubevirt_kwargs("handler", os_version, user="0"),
            package_list=sorted(
                [
                    "kubevirt-virt-handler",
                    "curl",
                    "iproute2",
                    "kubevirt-container-disk",
                    "nftables",
                    "qemu-img",
                    "system-user-qemu",
                    "tar",
                    "util-linux-systemd",
                ]
            ),
            entrypoint=["/usr/bin/virt-handler"],
        )
        for os_version in (OsVersion.SL16_0, OsVersion.TUMBLEWEED)
    ]
    + [
        ApplicationStackContainer(
            **_get_kubevirt_kwargs("launcher", os_version),
            package_list=sorted(["kubevirt-virt-launcher", "shadow"]),
            entrypoint=["/usr/bin/virt-launcher-monitor"],
        )
        for os_version in (OsVersion.SL16_0, OsVersion.TUMBLEWEED)
    ]
    + [
        ApplicationStackContainer(
            **_get_kubevirt_kwargs("operator", os_version),
            package_list=sorted(["kubevirt-virt-operator", "shadow"]),
            entrypoint=["/usr/bin/virt-operator"],
        )
        for os_version in (OsVersion.SL16_0, OsVersion.TUMBLEWEED)
    ]
    + [
        ApplicationStackContainer(
            **_get_kubevirt_kwargs("operator", os_version),
            package_list=sorted(["kubevirt-virt-operator", "shadow"]),
            entrypoint=["/usr/bin/virt-operator"],
        )
        for os_version in (OsVersion.SL16_0, OsVersion.TUMBLEWEED)
    ]
    + [
        ApplicationStackContainer(
            **_get_kubevirt_kwargs("operator", os_version),
            package_list=sorted(["kubevirt-virt-operator", "shadow"]),
            entrypoint=["/usr/bin/virt-operator"],
        )
        for os_version in (OsVersion.SL16_0, OsVersion.TUMBLEWEED)
    ]
    + [
        ApplicationStackContainer(
            **_get_kubevirt_kwargs("pr-helper", os_version, user="0", custom_end=False),
            package_list=sorted(["kubevirt-pr-helper-conf", "qemu-pr-helper"]),
            entrypoint=["/usr/bin/qemu-pr-helper"],
            custom_end=f"{DOCKERFILE_RUN} cp -f /usr/share/kube-virt/pr-helper/multipath.conf /etc/",
        )
        for os_version in (OsVersion.SL16_0, OsVersion.TUMBLEWEED)
    ]
)
