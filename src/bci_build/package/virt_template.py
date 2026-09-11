"""Container definitions for virt-template, the KubeVirt VM templates add-on.

virt-operator deploys the virt-template apiserver and controller (Template
feature gate) from images it derives from its own registry, so every KubeVirt
minor needs the virt-template minor it pins published next to it. The
containers are parameterised by a build variant like the KubeVirt ones: the
OS base plus the versioned RPM/image package pair.
"""

import textwrap
from typing import NamedTuple

from bci_build.container_attributes import Arch
from bci_build.container_attributes import SupportLevel
from bci_build.containercrate import ContainerCrate
from bci_build.os_version import CAN_BE_LATEST_OS_VERSION
from bci_build.os_version import OsVersion
from bci_build.package import DOCKERFILE_RUN
from bci_build.package import ApplicationStackContainer
from bci_build.package.helpers import generate_from_image_tag
from bci_build.package.helpers import generate_package_version_check
from bci_build.package.versions import format_version
from bci_build.package.versions import get_pkg_version
from bci_build.replacement import Replacement
from bci_build.util import ParseVersion

VIRT_TEMPLATE_EXCLUSIVE_ARCH = [Arch.AARCH64, Arch.X86_64]

# upstream's images run as this uid (distroless "nonroot"); the deployments
# virt-operator creates only ask for runAsNonRoot, so any non-root user works,
# but keep the number for parity.
_VIRT_TEMPLATE_UID = "65532"

# where upstream's images place the binaries; the deployments virt-operator
# creates use these as the container command
_UPSTREAM_BINARY = {"apiserver": "/apiserver", "controller": "/manager"}


class VirtTemplateVariant(NamedTuple):
    os_version: OsVersion
    pkg: str  # RPM prefix, e.g. "virt-template0.2"
    image: str  # OBS image package, e.g. "virt-template-0.2-image"
    # only ONE minor per registry may claim :latest; older minors set False
    latest: bool = True


_VIRT_TEMPLATE_VARIANTS = (
    VirtTemplateVariant(
        OsVersion.TUMBLEWEED, "virt-template0.2", "virt-template-0.2-image"
    ),
)


def _get_virt_template_kwargs(service: str, variant: VirtTemplateVariant) -> dict:
    """Generate common kwargs for the virt-template containers."""
    service_pkg_name = f"{variant.pkg}-{service}"
    version = get_pkg_version(variant.pkg, variant.os_version)
    version_re = "%%virt_template_ver%%"
    return {
        "name": f"virt-template-{service}",
        "pretty_name": f"KubeVirt virt-template {service}",
        "package_name": variant.image,
        "license": "Apache-2.0",
        "os_version": variant.os_version,
        "tag_version": format_version(version, ParseVersion.MINOR),
        "version": version_re,
        "replacements_via_service": [
            Replacement(
                version_re,
                package_name=variant.pkg,
                parse_version=ParseVersion.PATCH,
            )
        ],
        "is_singleton_image": True,
        "is_latest": (
            variant.latest
            and variant.os_version in CAN_BE_LATEST_OS_VERSION
            and variant.os_version.is_tumbleweed
        ),
        "build_flavor": service,
        "version_in_uid": True,
        "use_build_flavor_in_tag": False,
        "entrypoint_user": _VIRT_TEMPLATE_UID,
        "exclusive_arch": VIRT_TEMPLATE_EXCLUSIVE_ARCH,
        "support_level": SupportLevel.L3,
        "from_target_image": generate_from_image_tag(variant.os_version, "bci-micro"),
        "package_list": sorted([service_pkg_name, "shadow"]),
        "entrypoint": [f"/usr/bin/virt-template-{service}"],
        "build_stage_custom_end": (
            generate_package_version_check(service_pkg_name, version, use_target=True)
            + textwrap.dedent(f"""
            {DOCKERFILE_RUN} useradd -u {_VIRT_TEMPLATE_UID} --create-home -s /bin/bash virt-template
            """)
        ),
        "custom_end": textwrap.dedent(f"""
            COPY --from=builder /etc/passwd /etc/passwd
            COPY --from=builder /etc/group /etc/group
            COPY --from=builder /home/virt-template /home/virt-template
            # the manifest virt-operator ships starts the container with
            # upstream's distroless path ({_UPSTREAM_BINARY[service]}); keep it valid
            {DOCKERFILE_RUN} ln -s /usr/bin/virt-template-{service} {_UPSTREAM_BINARY[service]}
            """),
    }


VIRT_TEMPLATE_CONTAINERS = [
    ApplicationStackContainer(**_get_virt_template_kwargs(service, variant))
    for variant in _VIRT_TEMPLATE_VARIANTS
    for service in ("apiserver", "controller")
]

VIRT_TEMPLATE_CRATE = ContainerCrate(VIRT_TEMPLATE_CONTAINERS)
