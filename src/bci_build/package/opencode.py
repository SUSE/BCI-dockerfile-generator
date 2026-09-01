"""Opencode BCI container"""

import textwrap
from typing import Any

from bci_build.container_attributes import Arch
from bci_build.container_attributes import SupportLevel
from bci_build.containercrate import ContainerCrate
from bci_build.os_version import OsVersion
from bci_build.package import DOCKERFILE_RUN
from bci_build.package import ApplicationStackContainer
from bci_build.package import DevelopmentContainer
from bci_build.package.helpers import generate_from_image_tag
from bci_build.replacement import Replacement
from bci_build.util import ParseVersion


def _common_args() -> dict[str, Any]:
    return {
        "name": "opencode",
        "package_name": "opencode-image",
        "version": (opencode_ver := "%%opencode_version%%"),
        "is_singleton_image": True,
        "use_build_flavor_in_tag": False,
        "no_recommends": False,
        "os_version": OsVersion.TUMBLEWEED,
        "is_latest": True,
        "support_level": SupportLevel.UNSUPPORTED,
        "replacements_via_service": [
            Replacement(
                regex_in_build_description=opencode_ver,
                package_name="opencode",
                parse_version=ParseVersion.PATCH,
            )
        ],
        "custom_end": "WORKDIR /workspace/\n",
        "extra_labels": {
            "run": textwrap.dedent("""\
                podman run --rm -it \\
                --userns=keep-id:uid=1000 \\
                -v \\${HOME}/.cache/opencode:/home/sandbox/.cache/opencode:Z \\
                -v \\${HOME}/.config/opencode:/home/sandbox/.config/opencode:Z \\
                -v \\${HOME}/.local/share/opencode:/home/sandbox/.local/share/opencode:Z \\
                -v \\$PWD:/workspace:Z \\
                \\${IMAGE}"""),
        },
        "entrypoint": ["/usr/bin/opencode"],
        "entrypoint_user": "sandbox",
        "volumes": ["/workspace/"],
        "exclusive_arch": [Arch.X86_64, Arch.AARCH64],
    }


OPENCODE_CONTAINERS = [
    ApplicationStackContainer(
        **_common_args(),
        build_flavor="base",
        pretty_name="Opencode sandbox",
        tag_version="base",
        from_target_image=generate_from_image_tag(OsVersion.TUMBLEWEED, "bci-micro"),
        package_list=[
            "aaa_base",
            "findutils",
            "gawk",
            "grep",
            "less",
            "opencode",
            "sed",
            "xz",
        ],
        build_stage_custom_end=textwrap.dedent(f"""\
            {DOCKERFILE_RUN} useradd -R /target/ -mUK HOME_MODE=0700 -u 1000 sandbox; \\
                cp -r /target/usr/etc/skel/. /target/home/sandbox/; \\
                chroot /target/ chown -R sandbox:sandbox /home/sandbox/; \\
                chroot /target/ install -dm 0700 -o sandbox -g sandbox /workspace/"""),
    ),
    DevelopmentContainer(
        **_common_args(),
        build_flavor="devel",
        pretty_name="Opencode development sandbox",
        tag_version="devel",
        package_list=[
            "findutils",
            "gawk",
            "less",
            "opencode",
        ],
        build_stage_custom_end=textwrap.dedent(f"""\
            {DOCKERFILE_RUN} useradd -u 1000 sandbox; \\
                install -dm 0700 -o sandbox -g sandbox /workspace/"""),
    ),
]

OPENCODE_CRATE = ContainerCrate(OPENCODE_CONTAINERS)
