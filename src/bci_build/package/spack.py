"""HPC container for Spack package manager."""

from bci_build.package import CAN_BE_LATEST_OS_VERSION
from bci_build.package import DOCKERFILE_RUN
from bci_build.package import _SUPPORTED_UNTIL_SLE
from bci_build.package import Arch
from bci_build.package import DevelopmentContainer
from bci_build.package import OsVersion
from bci_build.package import Replacement
from bci_build.package import SupportLevel
from bci_build.package import generate_disk_size_constraints
from bci_build.package.helpers import generate_package_version_check
from bci_build.package.versions import get_pkg_version

SPACK_CONTAINERS = [
    DevelopmentContainer(
        name="spack",
        package_name="spack-image",
        pretty_name="Spack development",
        custom_description="Spack is a flexible package manager for supercomputers, {based_on_container}.",
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        logo_url="https://spack.io/assets/images/spack-logo-white.svg",
        version=(spack_pkg_version := get_pkg_version("spack", os_version)),
        version_in_uid=False,
        additional_versions=["%%spack_minor%%"],
        replacements_via_service=[
            Replacement(
                regex_in_build_description="%%spack_minor%%",
                package_name="spack",
                parse_version="minor",
            ),
        ],
        package_list=[
            "spack",
            "bison",
            "cmake-full",
            "flex",
            "libtool",
            "makeinfo",
            "patchelf",
            "lsb-release",
            "zstd",
            "libzip-devel",
            "libcurl-devel",
            "libopenssl-devel",
            "ncurses-devel",
            "tack",
            "xz-devel",
        ],
        no_recommends=False,
        entrypoint=["/bin/bash", "/usr/share/spack/docker/entrypoint.bash"],
        cmd=["interactive-shell"],
        env={
            "SPACK_ROOT": "/usr",
            "CURRENTLY_BUILDING_DOCKER_IMAGE": "1",
            "container": "docker",
        },
        extra_files={
            "_constraints": generate_disk_size_constraints(10),
        },
        # HPC module only exists for those two arches (bsc#1224130)
        exclusive_arch=[Arch.AARCH64, Arch.X86_64],
        support_level=SupportLevel.L3,
        supported_until=_SUPPORTED_UNTIL_SLE[OsVersion.SP6],
        custom_end=rf"""
{DOCKERFILE_RUN} ln -s $SPACK_ROOT/share/spack/docker/entrypoint.bash \
       /usr/local/bin/docker-shell \
    && ln -s $SPACK_ROOT/share/spack/docker/entrypoint.bash \
       /usr/local/bin/interactive-shell \
    && ln -s $SPACK_ROOT/share/spack/docker/entrypoint.bash \
       /usr/local/bin/spack-env \
    && echo 'source $SPACK_ROOT/share/spack/spack-completion.bash' > /root/.bashrc
{DOCKERFILE_RUN} mkdir -p /root/.spack \
    && cp $SPACK_ROOT/share/spack/docker/modules.yaml \
       /root/.spack/modules.yaml \
    && rm -rf /root/*.* /run/nologin

{generate_package_version_check('spack', spack_pkg_version, 'patch')}

WORKDIR /root
SHELL ["docker-shell"]
""",
    )
    for os_version in [OsVersion.SP6, OsVersion.TUMBLEWEED]
]
