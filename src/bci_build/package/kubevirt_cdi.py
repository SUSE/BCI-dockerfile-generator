"""Common Definitions for the KubeVirt CDI containers."""

import textwrap

from bci_build.container_attributes import Arch
from bci_build.container_attributes import SupportLevel
from bci_build.containercrate import ContainerCrate
from bci_build.os_version import CAN_BE_LATEST_OS_VERSION
from bci_build.os_version import OsVersion
from bci_build.package import DOCKERFILE_RUN
from bci_build.package import ApplicationStackContainer
from bci_build.package.helpers import generate_from_image_tag
from bci_build.package.helpers import generate_package_version_check
from bci_build.package.kubevirt import KubeVirtRegistrySL160
from bci_build.package.kubevirt import KubeVirtRegistrySL161
from bci_build.package.versions import format_version
from bci_build.package.versions import get_pkg_version
from bci_build.replacement import Replacement
from bci_build.util import ParseVersion

CDI_EXCLUSIVE_ARCH = [Arch.AARCH64, Arch.X86_64]
_CDI_VERSIONS = (
    ("1.65", OsVersion.SL16_0),
    ("1.65", OsVersion.SL16_1),
    ("1.65", OsVersion.TUMBLEWEED),
    ("1.66", OsVersion.TUMBLEWEED),
)


def _cdi_pkg(cdi_version: str) -> str:
    """Get the CDI package name for a given CDI version."""
    return f"containerized-data-importer{cdi_version}"


def _cdi_meta_pkg(cdi_version: str) -> str:
    """Get the CDI meta package name for a given CDI version."""
    return f"obs-service-cdi{cdi_version}_containers_meta"


def _get_cdi_kwargs(
    service: str,
    cdi_version: str,
    os_version: OsVersion,
    *,
    user=None,
    package_list=None,
) -> dict:
    """Generate common kwargs for KubeVirt CDI containers."""

    if user is None:
        user = "1001"
    service_pkg_name = _cdi_meta_pkg(cdi_version)
    if package_list is None:
        package_list = []
    package_list.append(service_pkg_name)
    package_list.sort()

    cdi_pkg_version = get_pkg_version(_cdi_pkg(cdi_version), os_version)
    cdi_version_re = "%%cdi_ver%%"
    tag_version = format_version(cdi_pkg_version, ParseVersion.MINOR)
    return {
        "name": f"cdi-{service}",
        "pretty_name": f"KubeVirt cdi-{service}",
        "package_name": f"cdi-{cdi_version}-image",
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
        "is_latest": (
            os_version in CAN_BE_LATEST_OS_VERSION and os_version.is_tumbleweed
        ),
        "build_flavor": service,
        "version_in_uid": True,
        "package_list": package_list,
        "use_build_flavor_in_tag": False,
        "entrypoint_user": user if user != "0" else None,
        "exclusive_arch": CDI_EXCLUSIVE_ARCH,
        "support_level": SupportLevel.L3,
        "_publish_registry": (
            KubeVirtRegistrySL160()
            if os_version == OsVersion.SL16_0
            else KubeVirtRegistrySL161()
            if os_version == OsVersion.SL16_1
            else None
        ),
        "from_target_image": generate_from_image_tag(os_version, "bci-micro"),
        "build_stage_custom_end": (f"{DOCKERFILE_RUN} rm -f /etc/blkid.conf\n")
        + (
            generate_package_version_check(
                service_pkg_name, tag_version, use_target=True
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
            **_get_cdi_kwargs(
                "apiserver",
                cdi_version,
                os_version,
                package_list=[f"{_cdi_pkg(cdi_version)}-api", "shadow"],
            ),
            entrypoint=["/usr/bin/virt-cdi-apiserver", "-alsologtostderr"],
        )
        for cdi_version, os_version in _CDI_VERSIONS
    ]
    + [
        ApplicationStackContainer(
            **_get_cdi_kwargs(
                "cloner",
                cdi_version,
                os_version,
                package_list=[
                    f"{_cdi_pkg(cdi_version)}-cloner",
                    "curl",
                    "tar",
                    "util-linux",
                    "shadow",
                ],
            ),
            entrypoint=["/usr/bin/cloner_startup.sh"],
        )
        for cdi_version, os_version in _CDI_VERSIONS
    ]
    + [
        ApplicationStackContainer(
            **_get_cdi_kwargs(
                "controller",
                cdi_version,
                os_version,
                package_list=[f"{_cdi_pkg(cdi_version)}-controller", "shadow"],
            ),
            entrypoint=["/usr/bin/virt-cdi-controller", "-alsologtostderr"],
        )
        for cdi_version, os_version in _CDI_VERSIONS
    ]
    + [
        ApplicationStackContainer(
            **_get_cdi_kwargs(
                "importer",
                cdi_version,
                os_version,
                package_list=[
                    f"{_cdi_pkg(cdi_version)}-importer",
                    "curl",
                    "nbdkit-server",
                    "nbdkit-basic-filters",
                    "nbdkit-curl-plugin",
                    "nbdkit-xz-filter",
                    "qemu-img",
                    "shadow",
                    "tar",
                    "util-linux",
                ],
            ),
            entrypoint=["/usr/bin/virt-cdi-importer", "-alsologtostderr"],
        )
        for cdi_version, os_version in _CDI_VERSIONS
    ]
    + [
        ApplicationStackContainer(
            **_get_cdi_kwargs(
                "operator",
                cdi_version,
                os_version,
                package_list=[f"{_cdi_pkg(cdi_version)}-operator", "shadow"],
            ),
            entrypoint=["/usr/bin/virt-cdi-operator"],
        )
        for cdi_version, os_version in _CDI_VERSIONS
    ]
    + [
        ApplicationStackContainer(
            **_get_cdi_kwargs(
                "uploadproxy",
                cdi_version,
                os_version,
                package_list=[f"{_cdi_pkg(cdi_version)}-uploadproxy", "shadow"],
            ),
            entrypoint=["/usr/bin/virt-cdi-uploadproxy", "-alsologtostderr"],
        )
        for cdi_version, os_version in _CDI_VERSIONS
    ]
    + [
        ApplicationStackContainer(
            **_get_cdi_kwargs(
                "uploadserver",
                cdi_version,
                os_version,
                package_list=[
                    f"{_cdi_pkg(cdi_version)}-uploadserver",
                    "curl",
                    "libnbd",
                    "qemu-img",
                    "shadow",
                    "tar",
                    "util-linux",
                ],
            ),
            entrypoint=["/usr/bin/virt-cdi-uploadserver", "-alsologtostderr"],
        )
        for cdi_version, os_version in _CDI_VERSIONS
    ]
)

CDI_CRATE = ContainerCrate(KUBEVIRT_CDI_CONTAINERS)
