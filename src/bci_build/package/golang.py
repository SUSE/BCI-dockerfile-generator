"""Go language BCI containers"""
import textwrap
from itertools import product
from typing import List
from typing import Literal

from bci_build.package import Replacement
from bci_build.package.bciclasses import LanguageStackContainer

from .constants import CAN_BE_LATEST_OS_VERSION
from .constants import DOCKERFILE_RUN
from .constants import OsVersion
from .constants import SupportLevel
from .utils import generate_disk_size_constraints


_GO_VER_T = Literal["1.20", "1.21", "1.22"]
_GOLANG_VERSIONS: List[_GO_VER_T] = ["1.20", "1.21"]
_GOLANG_OPENSSL_VERSIONS: List[_GO_VER_T] = ["1.19", "1.20"]
_GOLANG_TW_VERSIONS = _GOLANG_VERSIONS  # + ["1.21"]
_GOLANG_VARIANT_T = Literal["", "-openssl"]

assert len(_GOLANG_VERSIONS) == 2, "Only two golang versions must be supported"


def _get_golang_kwargs(
    ver: _GO_VER_T, variant: _GOLANG_VARIANT_T, os_version: OsVersion
):
    golang_version_regex = "%%golang_version%%"

    if variant == "":
        is_stable = ver == _GOLANG_VERSIONS[-1]
    elif variant == "-openssl":
        is_stable = ver == _GOLANG_OPENSSL_VERSIONS[-1]

    stability_tag = f"oldstable{variant}"
    if (
        _GOLANG_TW_VERSIONS[-1] != _GOLANG_VERSIONS[-1]
        and ver == _GOLANG_TW_VERSIONS[-1]
    ):
        stability_tag = f"unstable{variant}"
    if is_stable:
        stability_tag = f"stable{variant}"

    go = f"go{ver}{variant}"
    go_packages = (
        f"{go}",
        f"{go}-doc",
    )
    return {
        "os_version": os_version,
        "package_name": f"golang-{stability_tag}-image",
        "pretty_name": f"Go {ver}{variant} development",
        "name": "golang",
        "stability_tag": stability_tag,
        "is_latest": (is_stable and (os_version in CAN_BE_LATEST_OS_VERSION)),
        "version": f"{ver}{variant}",
        "env": {
            "GOLANG_VERSION": golang_version_regex,
            "GOPATH": "/go",
            "PATH": "/go/bin:/usr/local/go/bin:/root/go/bin/:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        },
        "replacements_via_service": [
            Replacement(
                regex_in_build_description=golang_version_regex, package_name=go
            )
        ],
        "custom_end": textwrap.dedent(
            f"""
            # only available on go's tsan_arch architectures
            #!ArchExclusiveLine x86_64 aarch64 s390x ppc64le
            {DOCKERFILE_RUN} if zypper -n install {go}-race; then zypper -n clean; rm -rf /var/log/*; fi
            """
        ),
        "package_list": [*go_packages, "make", "git-core"]
        + os_version.lifecycle_data_pkg,
        "extra_files": {
            # the go binaries are huge and will ftbfs on workers with a root partition with 4GB
            "_constraints": generate_disk_size_constraints(8)
        },
    }


GOLANG_CONTAINERS = (
    [
        LanguageStackContainer(
            **_get_golang_kwargs(ver, govariant, sle15sp),
            support_level=SupportLevel.L3,
        )
        for ver, govariant, sle15sp in product(
            _GOLANG_VERSIONS, ("",), (OsVersion.SP5, OsVersion.SP6)
        )
    ]
    + [
        LanguageStackContainer(
            **_get_golang_kwargs(ver, govariant, sle15sp),
            support_level=SupportLevel.L3,
        )
        for ver, govariant, sle15sp in product(
            _GOLANG_OPENSSL_VERSIONS, ("-openssl",), (OsVersion.SP5, OsVersion.SP6)
        )
    ]
    + [
        LanguageStackContainer(**_get_golang_kwargs(ver, "", OsVersion.TUMBLEWEED))
        for ver in _GOLANG_VERSIONS + _GOLANG_TW_VERSIONS
    ]
)
