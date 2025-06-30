"""Container definition for the MariaDB database server and client."""

import re
from pathlib import Path

from bci_build.container_attributes import TCP
from bci_build.container_attributes import Arch
from bci_build.container_attributes import BuildType
from bci_build.container_attributes import SupportLevel
from bci_build.os_version import CAN_BE_LATEST_OS_VERSION
from bci_build.os_version import OsVersion
from bci_build.package import DOCKERFILE_RUN
from bci_build.package import ApplicationStackContainer
from bci_build.package import ParseVersion
from bci_build.package import Replacement
from bci_build.package import generate_disk_size_constraints
from bci_build.package.helpers import generate_from_image_tag
from bci_build.package.helpers import generate_package_version_check
from bci_build.package.versions import get_pkg_version

_MARIADB_IDEXEC = b"""#!/bin/bash

u=$1
shift

if ! id -u "$u" > /dev/null 2>&1; then
    echo "Invalid user: $u"
    exit 1
fi

exec setpriv --pdeathsig=keep --reuid="$u" --regid="$u" --clear-groups -- "$@"
"""

MARIADB_CONTAINERS = []
MARIADB_CLIENT_CONTAINERS = []

for os_version in (
    OsVersion.SP6,
    OsVersion.SP7,
    OsVersion.SL16_0,
    OsVersion.TUMBLEWEED,
):
    mariadb_version = get_pkg_version("mariadb", os_version)

    pkg_prefix = ""
    if os_version.is_sle15:
        pkg_prefix = "rmt-"

    docker_entrypoint = (
        Path(__file__).parent / "mariadb" / str(mariadb_version) / "entrypoint.sh"
    ).read_text()
    # Patch up the version number to be the exact x.y.z version that we ship
    # using the replace_using_pkg_version service
    # Although the current version is not checking the patch level, this might
    # change in the future
    _MARIADB_VERSION_PLACEHOLDER = "%%mariadb_version%%"
    docker_entrypoint = re.sub(
        f'echo -n "{mariadb_version}.*-MariaDB"',
        f'echo -n "{_MARIADB_VERSION_PLACEHOLDER}-MariaDB"',
        docker_entrypoint,
    )

    _ENTRYPOINT_FNAME = "docker-entrypoint.sh"

    healthcheck = (
        Path(__file__).parent / "mariadb" / str(mariadb_version) / "healthcheck.sh"
    ).read_bytes()

    MARIADB_CONTAINERS.append(
        ApplicationStackContainer(
            name="mariadb",
            package_name=f"{pkg_prefix}mariadb-image",
            version=_MARIADB_VERSION_PLACEHOLDER,
            tag_version=mariadb_version,
            exclusive_arch=[Arch.AARCH64, Arch.PPC64LE, Arch.S390X, Arch.X86_64],
            os_version=os_version,
            is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
            version_in_uid=False,
            pretty_name="MariaDB Server",
            from_target_image=generate_from_image_tag(os_version, "bci-micro"),
            build_stage_custom_end=generate_package_version_check(
                "mariadb", mariadb_version, use_target=True
            ),
            replacements_via_service=[
                Replacement(
                    regex_in_build_description=_MARIADB_VERSION_PLACEHOLDER,
                    package_name="mariadb",
                    file_name=_ENTRYPOINT_FNAME,
                    parse_version=ParseVersion.PATCH,
                ),
                Replacement(
                    regex_in_build_description=_MARIADB_VERSION_PLACEHOLDER,
                    package_name="mariadb",
                ),
            ],
            package_list=[
                "coreutils",
                "findutils",
                "gawk",
                "mariadb",
                "mariadb-tools",
                "openssl",
                "sed",
                "timezone",
                "util-linux",
                "zstd",
            ],
            entrypoint=[_ENTRYPOINT_FNAME],
            license="GPL-2.0-only",
            extra_files={
                _ENTRYPOINT_FNAME: docker_entrypoint,
                "LICENSE": (
                    Path(__file__).parent / "mariadb" / str(mariadb_version) / "LICENSE"
                ).read_bytes(),
                "healthcheck.sh": healthcheck,
                "idexec": _MARIADB_IDEXEC,
                "_constraints": generate_disk_size_constraints(11),
            },
            support_level=SupportLevel.L3,
            build_recipe_type=BuildType.DOCKER,
            cmd=["mariadbd"],
            volumes=["/var/lib/mysql"],
            exposes_ports=[TCP(3306)],
            custom_end=rf"""{DOCKERFILE_RUN} mkdir /docker-entrypoint-initdb.d

# docker-entrypoint from https://github.com/MariaDB/mariadb-docker.git
COPY {_ENTRYPOINT_FNAME} /usr/local/bin/
{DOCKERFILE_RUN} chmod 755 /usr/local/bin/{_ENTRYPOINT_FNAME}
{DOCKERFILE_RUN} ln -s usr/local/bin/{_ENTRYPOINT_FNAME} / # backwards compat

# healthcheck from https://github.com/MariaDB/mariadb-docker.git
COPY healthcheck.sh /usr/local/bin/
{DOCKERFILE_RUN} chmod 755 /usr/local/bin/healthcheck.sh

COPY idexec /usr/local/bin/idexec
{DOCKERFILE_RUN} chmod 755 /usr/local/bin/idexec

# replace gosu calls with idexec
{DOCKERFILE_RUN} sed -i 's/exec gosu /exec idexec /g' /usr/local/bin/{_ENTRYPOINT_FNAME}
{DOCKERFILE_RUN} sed -i 's/exec gosu /exec idexec /g' /usr/local/bin/healthcheck.sh

{DOCKERFILE_RUN} sed -i -e 's,$(pwgen .*),$(openssl rand -base64 36),' /usr/local/bin/{_ENTRYPOINT_FNAME}

# Ensure all logs goes to stdout
{DOCKERFILE_RUN} sed -i 's/^log/#log/g' /etc/my.cnf

# Disable binding to localhost only, doesn't make sense in a container
{DOCKERFILE_RUN} sed -i -e 's|^\(bind-address.*\)|#\1|g' /etc/my.cnf

{DOCKERFILE_RUN} install -d -m 0755 -o mysql -g mysql /run/mysql
{DOCKERFILE_RUN} install -d -m 0700 -o mysql -g root /var/lib/mysql
""",
        )
    )

    MARIADB_CLIENT_CONTAINERS.append(
        ApplicationStackContainer(
            name="mariadb-client",
            package_name=f"{pkg_prefix}mariadb-client-image",
            exclusive_arch=[Arch.AARCH64, Arch.PPC64LE, Arch.S390X, Arch.X86_64],
            os_version=os_version,
            is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
            version_in_uid=False,
            version=_MARIADB_VERSION_PLACEHOLDER,
            from_target_image=generate_from_image_tag(os_version, "bci-micro"),
            build_stage_custom_end=generate_package_version_check(
                "mariadb-client", mariadb_version, use_target=True
            ),
            tag_version=mariadb_version,
            pretty_name="MariaDB Client",
            support_level=SupportLevel.L3,
            package_list=["mariadb-client"],
            build_recipe_type=BuildType.DOCKER,
            cmd=["mariadb"],
            replacements_via_service=[
                Replacement(
                    regex_in_build_description=_MARIADB_VERSION_PLACEHOLDER,
                    package_name="mariadb-client",
                ),
            ],
        )
    )
