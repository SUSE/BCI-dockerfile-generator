"""Rust language BCI container"""

import datetime
from itertools import product

import packaging.version

from bci_build.container_attributes import SupportLevel
from bci_build.os_version import ALL_NONBASE_OS_VERSIONS
from bci_build.os_version import CAN_BE_LATEST_OS_VERSION
from bci_build.os_version import OsVersion
from bci_build.package import DevelopmentContainer
from bci_build.package import Replacement
from bci_build.package import generate_disk_size_constraints

_RUST_GCC_PATH = "/usr/local/bin/gcc"

# release dates are coming from upstream - https://raw.githubusercontent.com/rust-lang/rust/master/RELEASES.md
# we expect a new release every 6 weeks, two releases are supported at any point in time
# and we give us three weeks of buffer, leading to release date + 6 + 6 + 3
_RUST_SUPPORT_OVERLAP: datetime.timedelta = datetime.timedelta(weeks=6 + 6 + 3)
_RUST_SUPPORT_ENDS = {
    "1.90": datetime.date(2025, 9, 18) + _RUST_SUPPORT_OVERLAP,
    "1.89": datetime.date(2025, 8, 7) + _RUST_SUPPORT_OVERLAP,
    "1.88": datetime.date(2025, 6, 26) + _RUST_SUPPORT_OVERLAP,
    "1.87": datetime.date(2025, 5, 15) + _RUST_SUPPORT_OVERLAP,
    "1.86": datetime.date(2025, 4, 3) + _RUST_SUPPORT_OVERLAP,
    "1.85": datetime.date(2025, 2, 20) + _RUST_SUPPORT_OVERLAP,
    "1.84": datetime.date(2025, 1, 9) + _RUST_SUPPORT_OVERLAP,
    "1.83": datetime.date(2024, 11, 28) + _RUST_SUPPORT_OVERLAP,
    "1.82": datetime.date(2024, 10, 17) + _RUST_SUPPORT_OVERLAP,
    "1.81": datetime.date(2024, 9, 5) + _RUST_SUPPORT_OVERLAP,
    "1.80": datetime.date(2024, 7, 25) + _RUST_SUPPORT_OVERLAP,
    "1.79": datetime.date(2024, 6, 13) + _RUST_SUPPORT_OVERLAP,
    "1.78": datetime.date(2024, 5, 2) + _RUST_SUPPORT_OVERLAP,
    "1.77": datetime.date(2024, 3, 21) + _RUST_SUPPORT_OVERLAP,
    "1.76": datetime.date(2024, 2, 8) + _RUST_SUPPORT_OVERLAP,
    "1.75": datetime.date(2023, 12, 28) + _RUST_SUPPORT_OVERLAP,
}

# ensure that the **latest** rust version is the last one!
_RUST_VERSIONS: list[str] = ["1.88", "1.89"]

_RUST_SL16_VERSIONS: list[str] = ["1.87", "1.88"]

_RUST_TW_VERSIONS: list[str] = ["1.88", "1.90"]


def _rust_is_stable_version(os_version: OsVersion, rust_version: str) -> bool:
    """Return the latest stable rust version"""
    if os_version in (OsVersion.TUMBLEWEED,):
        return _RUST_TW_VERSIONS[-1] == rust_version
    if os_version in (OsVersion.SL16_0,):
        return _RUST_SL16_VERSIONS[-1] == rust_version

    return _RUST_VERSIONS[-1] == rust_version


assert len(_RUST_VERSIONS) == 2, (
    "Only two versions of rust must be supported at the same time"
)

assert packaging.version.parse(_RUST_VERSIONS[0]) < packaging.version.parse(
    _RUST_VERSIONS[1]
), "Newest rust version must be listed as last"

RUST_CONTAINERS = [
    DevelopmentContainer(
        name="rust",
        stability_tag=(
            stability_tag := (
                "stable"
                if _rust_is_stable_version(os_version, rust_version)
                else "oldstable"
            )
        ),
        package_name=f"rust-{stability_tag}-image",
        os_version=os_version,
        support_level=SupportLevel.L3,
        is_latest=(
            _rust_is_stable_version(os_version, rust_version)
            and os_version in CAN_BE_LATEST_OS_VERSION
        ),
        supported_until=_RUST_SUPPORT_ENDS.get(rust_version),
        pretty_name=f"Rust {rust_version}",
        package_list=[
            f"rust{rust_version}",
            f"cargo{rust_version}",
        ]
        + os_version.lifecycle_data_pkg,
        version="%%RUST_VERSION%%",
        tag_version=rust_version,
        env={
            "RUST_VERSION": "%%RUST_VERSION%%",
            "CARGO_VERSION": "%%CARGO_VERSION%%",
            "CC": _RUST_GCC_PATH,
        },
        extra_files={
            # prevent ftbfs on workers with a root partition with 4GB
            "_constraints": generate_disk_size_constraints(6),
            (
                check_fname := "rust-and-cargo-pin.check"
            ): f"""requires:cargo{rust_version}
requires:rust{rust_version}
""",
        },
        replacements_via_service=[
            Replacement(
                regex_in_build_description="%%RUST_VERSION%%",
                package_name=f"rust{rust_version}",
            ),
            Replacement(
                regex_in_build_description="%%CARGO_VERSION%%",
                package_name=f"cargo{rust_version}",
            ),
        ],
        custom_end=f"""# workaround for gcc only existing as /usr/bin/gcc-N
RUN ln -sf $(ls /usr/bin/gcc-* | grep -P ".*gcc-[[:digit:]]+") {_RUST_GCC_PATH}
# smoke test that gcc works
RUN gcc --version
RUN ${{CC}} --version
COPY {check_fname} /etc/zypp/systemCheck.d/{check_fname}
""",
    )
    for rust_version, os_version in (
        *product(
            _RUST_VERSIONS,
            set(ALL_NONBASE_OS_VERSIONS)
            - set([OsVersion.TUMBLEWEED, OsVersion.SL16_0]),
        ),
        *product(_RUST_TW_VERSIONS, [OsVersion.TUMBLEWEED]),
        *product(_RUST_SL16_VERSIONS, [OsVersion.SL16_0]),
    )
]
