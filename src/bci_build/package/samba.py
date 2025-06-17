"""Samba container definition"""

import textwrap
from pathlib import Path

from bci_build.container_attributes import TCP
from bci_build.container_attributes import SupportLevel
from bci_build.os_version import CAN_BE_LATEST_OS_VERSION
from bci_build.package import DOCKERFILE_RUN
from bci_build.package import ApplicationStackContainer
from bci_build.package import OsVersion
from bci_build.package import ParseVersion
from bci_build.package import Replacement
from bci_build.package.helpers import generate_from_image_tag
from bci_build.package.helpers import generate_package_version_check
from bci_build.package.versions import get_pkg_version

SAMBA_SERVER_CONTAINERS = []
SAMBA_CLIENT_CONTAINERS = []
SAMBA_TOOLBOX_CONTAINERS = []


for os_version in (OsVersion.TUMBLEWEED, OsVersion.SP7):
    samba_version = get_pkg_version("samba", os_version)

    srv = ApplicationStackContainer(
        name="samba-server",
        pretty_name="Samba Server",
        from_target_image=generate_from_image_tag(os_version, "bci-micro"),
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        is_singleton_image=True,
        version="%%samba_version%%",
        version_in_uid=False,
        support_level=SupportLevel.L3,
        tag_version=samba_version,
        build_stage_custom_end=generate_package_version_check(
            "samba", samba_version, use_target=True
        ),
        replacements_via_service=[
            Replacement(
                regex_in_build_description="%%samba_version%%",
                package_name="samba",
                parse_version=ParseVersion.MINOR,
            )
        ],
        license="GPL-3.0-or-later",
        package_list=[
            "catatonit",
            "samba",
            # "ctdb",
            # "timezone",
        ],
        extra_files={
            "docker-entrypoint.sh": (
                Path(__file__).parent / "samba-server" / "entrypoint.sh"
            ).read_bytes(),
            "smbuser.sh": (
                Path(__file__).parent / "samba-server" / "smbuser.sh"
            ).read_bytes(),
            "shadow.sh": (
                Path(__file__).parent / "samba-server" / "shadow.sh"
            ).read_bytes(),
            "smb.conf": (
                Path(__file__).parent / "samba-server" / "smb.conf"
            ).read_bytes(),
        },
        entrypoint=["/usr/local/bin/docker-entrypoint.sh"],
        exposes_ports=[TCP(445)],
        volumes=["/shares", "/var/lib/samba"],
        custom_end=textwrap.dedent(f"""
            COPY smb.conf /etc/samba/

            COPY docker-entrypoint.sh /usr/local/bin/
            {DOCKERFILE_RUN} chmod 755 /usr/local/bin/docker-entrypoint.sh

            COPY smbuser.sh /usr/local/bin/smbuser
            {DOCKERFILE_RUN} chmod 755 /usr/local/bin/smbuser

            COPY shadow.sh /usr/local/bin/useradd
            {DOCKERFILE_RUN} chmod 755 /usr/local/bin/useradd
            COPY shadow.sh /usr/local/bin/usermod
            {DOCKERFILE_RUN} chmod 755 /usr/local/bin/usermod
            COPY shadow.sh /usr/local/bin/userdel
            {DOCKERFILE_RUN} chmod 755 /usr/local/bin/userdel
            COPY shadow.sh /usr/local/bin/passwd
            {DOCKERFILE_RUN} chmod 755 /usr/local/bin/passwd
            COPY shadow.sh /usr/local/bin/groupadd
            {DOCKERFILE_RUN} chmod 755 /usr/local/bin/groupadd
            COPY shadow.sh /usr/local/bin/groupmod
            {DOCKERFILE_RUN} chmod 755 /usr/local/bin/groupmod
            COPY shadow.sh /usr/local/bin/groupdel
            {DOCKERFILE_RUN} chmod 755 /usr/local/bin/groupdel

            HEALTHCHECK --interval=60s --timeout=15s \
                        CMD smbclient -L \\localhost -U % -m SMB3
        """),
    )

    cli = ApplicationStackContainer(
        name="samba-client",
        pretty_name="Samba Client",
        from_target_image=generate_from_image_tag(os_version, "bci-micro"),
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        is_singleton_image=True,
        version="%%samba_version%%",
        version_in_uid=False,
        support_level=SupportLevel.L3,
        tag_version=samba_version,
        build_stage_custom_end=generate_package_version_check(
            "samba-client", samba_version, use_target=True
        ),
        replacements_via_service=[
            Replacement(
                regex_in_build_description="%%samba_version%%",
                package_name="samba-client",
                parse_version=ParseVersion.MINOR,
            )
        ],
        license="GPL-3.0-or-later",
        package_list=[
            "samba-client",
        ],
    )

    toolbox = ApplicationStackContainer(
        name="samba-toolbox",
        pretty_name="Samba Toolbox",
        from_target_image=generate_from_image_tag(os_version, "bci-micro"),
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        is_singleton_image=True,
        version="%%samba_version%%",
        version_in_uid=False,
        support_level=SupportLevel.L3,
        tag_version=samba_version,
        build_stage_custom_end=generate_package_version_check(
            "samba-client", samba_version, use_target=True
        ),
        replacements_via_service=[
            Replacement(
                regex_in_build_description="%%samba_version%%",
                package_name="samba-client",
                parse_version=ParseVersion.MINOR,
            )
        ],
        license="GPL-3.0-or-later",
        package_list=[
            "samba-client",
            "tdb-tools",
        ]
        # FIXME: unavailable on SLES
        + (["samba-test"] if os_version.is_tumbleweed else []),
    )

    SAMBA_SERVER_CONTAINERS.append(srv)
    SAMBA_CLIENT_CONTAINERS.append(cli)
    SAMBA_TOOLBOX_CONTAINERS.append(toolbox)
