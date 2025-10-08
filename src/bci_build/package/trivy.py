"""Trivy container image scanning"""

from bci_build.container_attributes import BuildType
from bci_build.container_attributes import PackageType
from bci_build.os_version import CAN_BE_LATEST_OS_VERSION
from bci_build.os_version import OsVersion
from bci_build.package import ApplicationStackContainer
from bci_build.package import Package
from bci_build.package.helpers import generate_from_image_tag
from bci_build.replacement import Replacement
from bci_build.util import ParseVersion

_TRIVY_VER_RE = "%%trivy_version%%"

TRIVY_CONTAINERS = [
    ApplicationStackContainer(
        name="trivy",
        pretty_name="Container Vulnerability Scanner",
        from_image=generate_from_image_tag(os_version, "bci-micro"),
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        version=_TRIVY_VER_RE,
        tag_version="0",
        version_in_uid=False,
        replacements_via_service=[
            Replacement(
                regex_in_build_description=_TRIVY_VER_RE,
                package_name="trivy",
                parse_version=ParseVersion.MINOR,
            )
        ],
        license="Apache-2.0",
        package_list=[
            Package(name, pkg_type=PackageType.BOOTSTRAP)
            for name in (
                "ca-certificates-mozilla",
                "trivy",
            )
        ],
        entrypoint=["/usr/bin/trivy"],
        cmd=["help"],
        build_recipe_type=BuildType.KIWI,
    )
    for os_version in (OsVersion.TUMBLEWEED,)
]
