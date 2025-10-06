"""Common Definitions for the KubeVirt CDI containers."""

import textwrap

from bci_build.container_attributes import Arch
from bci_build.container_attributes import SupportLevel
from bci_build.containercrate import ContainerCrate
from bci_build.os_version import OsVersion
from bci_build.package import DOCKERFILE_RUN
from bci_build.package import ApplicationStackContainer
from bci_build.package import ParseVersion
from bci_build.package import Replacement
from bci_build.package.helpers import generate_from_image_tag
from bci_build.package.helpers import generate_package_version_check
from bci_build.package.versions import format_version
from bci_build.package.versions import get_pkg_version
from bci_build.package.kubevirt import KubeVirtRegistry
from bci_build.registry import SUSERegistry

CDI_EXCLUSIVE_ARCH = [Arch.X86_64]


def _get_cdi_kwargs(
    service: str,
    os_version: OsVersion,
    *,
    user=None,
    custom_end=True,
    custom_service_pkg_name=None,
) -> dict:
    """Generate common kwargs for KubeVirt CDI containers."""

    if user is None:
        user = "1001"
    service_pkg_name = (
        f"containerized-data-importer-{service}"
        if custom_service_pkg_name is None
        else custom_service_pkg_name
    )
    cdi_version = get_pkg_version("containerized-data-importer", os_version)
    cdi_version_re = "%%cdi_ver%%"
    tag_version = format_version(cdi_version, ParseVersion.MINOR)
    return {
        "name": f"cdi-{service}",
        "pretty_name": f"KubeVirt cdi-{service} container",
        "package_name": "cdi-image",
        "license": "Apache-2.0",
        "os_version": os_version,
        "tag_version": tag_version,
        "version": cdi_version_re,
        "replacements_via_service": [
            Replacement(
                cdi_version_re,
                package_name=service_pkg_name,
                parse_version=ParseVersion.PATCH,
            )
        ],
        "is_singleton_image": True,
        "is_latest": False,
        "build_flavor": service,
        "version_in_uid": False,
        "use_build_flavor_in_tag": False,
        "entrypoint_user": user if user != "0" else None,
        "exclusive_arch": CDI_EXCLUSIVE_ARCH,
        "support_level": SupportLevel.L3,
        "_publish_registry": (
            KubeVirtRegistry() if os_version == OsVersion.SL16_0 else None
        ),
        "from_target_image": generate_from_image_tag(os_version, "bci-micro"),
        "build_stage_custom_end": (
            generate_package_version_check(
                service_pkg_name,
                cdi_version,
                ParseVersion.PATCH,
                use_target=True,
            )
            + (
                textwrap.dedent(f"""
            {DOCKERFILE_RUN} useradd -u {user} --create-home -s /bin/bash cdi-{service}
            """)
                if user != "0"
                else ""
            )
        ),
    }


KUBEVIRT_CDI_CONTAINERS = (
    [
        ApplicationStackContainer(
            **_get_cdi_kwargs("apiserver", os_version),
            package_list=sorted(["containerized-data-importer-api", "shadow"]),
            entrypoint=["/usr/bin/virt-cdi-apiserver", "-alsologtostderr"],
        )
        for os_version in (OsVersion.SL16_0, OsVersion.TUMBLEWEED)
    ]
    + [
        ApplicationStackContainer(
            **_get_cdi_kwargs("cloner", os_version),
            package_list=sorted(
                [
                    "containerized-data-importer-cloner",
                    "curl",
                    "tar",
                    "util-linux",
                    "shadow",
                ]
            ),
            entrypoint=["/usr/bin/cloner_startup.sh"],
        )
        for os_version in (OsVersion.SL16_0, OsVersion.TUMBLEWEED)
    ]
    + [
        ApplicationStackContainer(
            **_get_cdi_kwargs("controller", os_version),
            package_list=sorted(["containerized-data-importer-controller", "shadow"]),
            entrypoint=["/usr/bin/virt-cdi-controller", "-alsologtostderr"],
        )
        for os_version in (OsVersion.SL16_0, OsVersion.TUMBLEWEED)
    ]
    + [
        ApplicationStackContainer(
            **_get_cdi_kwargs("importer", os_version),
            package_list=sorted(
                [
                    "containerized-data-importer-importer",
                    "curl",
                    "nbdkit-server",
                    "nbdkit-basic-filters",
                    "nbdkit-curl-plugin",
                    "nbdkit-xz-filter",
                    "qemu-img",
                    "shadow",
                    "tar",
                    "util-linux",
                ]
            ),
            entrypoint=["/usr/bin/virt-cdi-importer", "-alsologtostderr"],
        )
        for os_version in (OsVersion.SL16_0, OsVersion.TUMBLEWEED)
    ]
    + [
        ApplicationStackContainer(
            **_get_cdi_kwargs("operator", os_version),
            package_list=sorted(["containerized-data-importer-operator", "shadow"]),
            entrypoint=["/usr/bin/virt-cdi-operator"],
        )
        for os_version in (OsVersion.SL16_0, OsVersion.TUMBLEWEED)
    ]
    + [
        ApplicationStackContainer(
            **_get_cdi_kwargs("uploadproxy", os_version),
            package_list=sorted(["containerized-data-importer-uploadproxy", "shadow"]),
            entrypoint=["/usr/bin/virt-cdi-uploadproxy", "-alsologtostderr"],
        )
        for os_version in (OsVersion.SL16_0, OsVersion.TUMBLEWEED)
    ]
    + [
        ApplicationStackContainer(
            **_get_cdi_kwargs("uploadserver", os_version),
            package_list=sorted(
                [
                    "containerized-data-importer-uploadserver",
                    "curl",
                    "libnbd",
                    "qemu-img",
                    "shadow",
                    "tar",
                    "util-linux",
                ]
            ),
            entrypoint=["/usr/bin/virt-cdi-uploadserver", "-alsologtostderr"],
        )
        for os_version in (OsVersion.SL16_0, OsVersion.TUMBLEWEED)
    ]
)

CDI_CRATE = ContainerCrate(KUBEVIRT_CDI_CONTAINERS)
