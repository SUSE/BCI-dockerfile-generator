"""This module defines the containers that are used in the BCI."""
import asyncio
from typing import Dict
from typing import List
from typing import Union

from .appcontainers import ALERTMANAGER_CONTAINERS
from .appcontainers import BLACKBOX_EXPORTER_CONTAINERS
from .appcontainers import GIT_CONTAINERS
from .appcontainers import GRAFANA_CONTAINERS
from .appcontainers import HELM_CONTAINERS
from .appcontainers import MARIADB_CLIENT_CONTAINERS
from .appcontainers import MARIADB_CONTAINERS
from .appcontainers import NGINX_CONTAINERS
from .appcontainers import PCP_CONTAINERS
from .appcontainers import POSTGRES_CONTAINERS
from .appcontainers import PROMETHEUS_CONTAINERS
from .appcontainers import REGISTRY_CONTAINERS
from .appcontainers import RMT_CONTAINERS
from .appcontainers import THREE_EIGHT_NINE_DS_CONTAINERS
from .basalt_base import BASALT_BASE
from .basecontainers import BUSYBOX_CONTAINERS
from .basecontainers import FIPS_BASE_CONTAINERS
from .basecontainers import INIT_CONTAINERS
from .basecontainers import KERNEL_MODULE_CONTAINERS
from .basecontainers import MICRO_CONTAINERS
from .basecontainers import MINIMAL_CONTAINERS
from .bciclasses import ApplicationStackContainer
from .bciclasses import BaseContainerImage
from .bciclasses import LanguageStackContainer
from .bciclasses import OsContainer
from .bciclasses import Package
from .bciclasses import Replacement
from .constants import ALL_BASE_OS_VERSIONS
from .constants import ALL_NONBASE_OS_VERSIONS
from .constants import ALL_OS_VERSIONS
from .constants import Arch
from .constants import BuildType
from .constants import CAN_BE_LATEST_OS_VERSION
from .constants import OsVersion
from .golang import GOLANG_CONTAINERS
from .node import NODE_CONTAINERS
from .openjdk import OPENJDK_CONTAINERS
from .php import PHP_CONTAINERS
from .python import PYTHON_3_10_SP4
from .python import PYTHON_3_11_CONTAINERS
from .python import PYTHON_3_6_CONTAINERS
from .python import PYTHON_TW_CONTAINERS
from .ruby import RUBY_CONTAINERS
from .rust import RUST_CONTAINERS
from .utils import generate_disk_size_constraints

ALL_CONTAINER_IMAGE_NAMES: Dict[str, BaseContainerImage] = {
    f"{bci.uid}-{bci.os_version.pretty_print.lower()}": bci
    for bci in (
        BASALT_BASE,
        *PYTHON_3_6_CONTAINERS,
        PYTHON_3_10_SP4,
        *PYTHON_3_11_CONTAINERS,
        *PYTHON_TW_CONTAINERS,
        *THREE_EIGHT_NINE_DS_CONTAINERS,
        *NGINX_CONTAINERS,
        *PCP_CONTAINERS,
        *REGISTRY_CONTAINERS,
        *HELM_CONTAINERS,
        *RMT_CONTAINERS,
        *RUST_CONTAINERS,
        *GIT_CONTAINERS,
        *GOLANG_CONTAINERS,
        *RUBY_CONTAINERS,
        *NODE_CONTAINERS,
        *OPENJDK_CONTAINERS,
        *PHP_CONTAINERS,
        *INIT_CONTAINERS,
        *FIPS_BASE_CONTAINERS,
        *MARIADB_CONTAINERS,
        *MARIADB_CLIENT_CONTAINERS,
        *POSTGRES_CONTAINERS,
        *PROMETHEUS_CONTAINERS,
        *ALERTMANAGER_CONTAINERS,
        *BLACKBOX_EXPORTER_CONTAINERS,
        *GRAFANA_CONTAINERS,
        *MINIMAL_CONTAINERS,
        *MICRO_CONTAINERS,
        *BUSYBOX_CONTAINERS,
        *KERNEL_MODULE_CONTAINERS,
    )
}

SORTED_CONTAINER_IMAGE_NAMES = sorted(
    ALL_CONTAINER_IMAGE_NAMES,
    key=lambda bci: str(ALL_CONTAINER_IMAGE_NAMES[bci].os_version),
)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        "Write the contents of a package directly to the filesystem"
    )

    parser.add_argument(
        "image",
        type=str,
        nargs=1,
        choices=SORTED_CONTAINER_IMAGE_NAMES,
        help="The BCI container image, which package contents should be written to the disk",
    )
    parser.add_argument(
        "destination",
        type=str,
        nargs=1,
        help="destination folder to which the files should be written",
    )

    args = parser.parse_args()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        ALL_CONTAINER_IMAGE_NAMES[args.image[0]].write_files_to_folder(
            args.destination[0]
        )
    )
