"""Container definition for the MariaDB database server and client."""

import re
from pathlib import Path

from bci_build.package import ALL_NONBASE_OS_VERSIONS
from bci_build.package import CAN_BE_LATEST_OS_VERSION
from bci_build.package import DOCKERFILE_RUN
from bci_build.package import ApplicationStackContainer
from bci_build.package import BuildType
from bci_build.package import OsVersion
from bci_build.package import ParseVersion
from bci_build.package import Replacement
from bci_build.package import SupportLevel
from bci_build.package import generate_disk_size_constraints
from bci_build.package.helpers import generate_package_version_check
from bci_build.package.versions import get_pkg_version

_MARIADB_GOSU = b"""#!/bin/bash

u=$1
shift

if ! id -u "$u" > /dev/null 2>&1; then
    echo "Invalid user: $u"
    exit 1
fi

exec setpriv --reuid="$u" --regid="$u" --clear-groups -- "$@"
"""

MARIADB_CONTAINERS = []
MARIADB_CLIENT_CONTAINERS = []

for os_version in ALL_NONBASE_OS_VERSIONS:
    mariadb_version = get_pkg_version("mariadb", os_version)

    if os_version in (OsVersion.SLE16_0, OsVersion.TUMBLEWEED):
        prefix = ""
        additional_names = []
    else:
        prefix = "rmt-"
        additional_names = ["mariadb"]

    version_check_lines = generate_package_version_check(
        "mariadb-client", mariadb_version
    )

    docker_entrypoint = (
        Path(__file__).parent / "mariadb" / str(mariadb_version) / "entrypoint.sh"
    ).read_text()
    # Patch up the version number to be the exact x.y.z version that we ship
    # using the replace_using_pkg_version service
    # Although the current version is not checking the patch level, this might
    # change in the future
    _MARIADB_VERSION_REGEX = "%%mariadb_version%%"
    docker_entrypoint = re.sub(
        f'echo -n "{mariadb_version}.*-MariaDB"',
        f'echo -n "{_MARIADB_VERSION_REGEX}-MariaDB"',
        docker_entrypoint,
    )

    _ENTRYPOINT_FNAME = "docker-entrypoint.sh"

    healthcheck = (
        Path(__file__).parent / "mariadb" / str(mariadb_version) / "healthcheck.sh"
    ).read_bytes()

    MARIADB_CONTAINERS.append(
        ApplicationStackContainer(
            name=f"{prefix}mariadb",
            version=mariadb_version,
            additional_names=additional_names,
            os_version=os_version,
            is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
            version_in_uid=False,
            pretty_name="MariaDB Server",
            replacements_via_service=[
                Replacement(
                    regex_in_build_description=_MARIADB_VERSION_REGEX,
                    package_name="mariadb",
                    file_name=_ENTRYPOINT_FNAME,
                    parse_version=ParseVersion.PATCH,
                )
            ],
            package_list=[
                "mariadb",
                "mariadb-tools",
                "gawk",
                "timezone",
                "util-linux",
                "findutils",
            ],
            entrypoint=[_ENTRYPOINT_FNAME],
            extra_files={
                _ENTRYPOINT_FNAME: docker_entrypoint,
                "healthcheck.sh": healthcheck,
                "gosu": _MARIADB_GOSU,
                "_constraints": generate_disk_size_constraints(11),
            },
            support_level=SupportLevel.L3,
            build_recipe_type=BuildType.DOCKER,
            cmd=["mariadbd"],
            volumes=["/var/lib/mysql"],
            exposes_tcp=[3306],
            custom_end=rf"""{version_check_lines}

{DOCKERFILE_RUN} mkdir /docker-entrypoint-initdb.d

# docker-entrypoint from https://github.com/MariaDB/mariadb-docker.git
COPY {_ENTRYPOINT_FNAME} /usr/local/bin/
{DOCKERFILE_RUN} chmod 755 /usr/local/bin/{_ENTRYPOINT_FNAME}
{DOCKERFILE_RUN} ln -s usr/local/bin/{_ENTRYPOINT_FNAME} / # backwards compat

# healthcheck from https://github.com/MariaDB/mariadb-docker.git
COPY healthcheck.sh /usr/local/bin/
{DOCKERFILE_RUN} chmod 755 /usr/local/bin/healthcheck.sh

COPY gosu /usr/local/bin/gosu
{DOCKERFILE_RUN} chmod 755 /usr/local/bin/gosu

{DOCKERFILE_RUN} sed -i -e 's,$(pwgen .*),$(openssl rand -base64 36),' /usr/local/bin/{_ENTRYPOINT_FNAME}

# Ensure all logs goes to stdout
{DOCKERFILE_RUN} sed -i 's/^log/#log/g' /etc/my.cnf

# Disable binding to localhost only, doesn't make sense in a container
{DOCKERFILE_RUN} sed -i -e 's|^\(bind-address.*\)|#\1|g' /etc/my.cnf

{DOCKERFILE_RUN} mkdir /run/mysql
""",
        )
    )

    MARIADB_CLIENT_CONTAINERS.append(
        ApplicationStackContainer(
            name=f"{prefix}mariadb-client",
            os_version=os_version,
            is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
            version_in_uid=False,
            additional_names=[f"{name}-client" for name in additional_names],
            version=mariadb_version,
            pretty_name="MariaDB Client",
            support_level=SupportLevel.L3,
            package_list=["mariadb-client"],
            build_recipe_type=BuildType.DOCKER,
            cmd=["mariadb"],
            custom_end=version_check_lines,
        )
    )
