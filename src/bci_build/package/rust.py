"""Rust language BCI container"""
import datetime
from itertools import product

from bci_build.package import ALL_NONBASE_OS_VERSIONS
from bci_build.package import CAN_BE_LATEST_OS_VERSION
from bci_build.package import generate_disk_size_constraints
from bci_build.package import LanguageStackContainer
from bci_build.package import Replacement
from bci_build.package import SupportLevel

_RUST_GCC_PATH = "/usr/local/bin/gcc"

# release dates are coming from upstream - https://raw.githubusercontent.com/rust-lang/rust/master/RELEASES.md
# we expect a new release every 6 weeks, two releases are supported at any point in time
# and we give us one week of buffer, leading to release date + 6 + 6 + 1
_RUST_SUPPORT_ENDS = {
    "1.74": datetime.date(2023, 11, 16) + datetime.timedelta(weeks=6 + 6 + 1),
    "1.73": datetime.date(2023, 10, 5) + datetime.timedelta(weeks=6 + 6 + 1),
    "1.72": datetime.date(2023, 8, 24) + datetime.timedelta(weeks=6 + 6 + 1),
    "1.71": datetime.date(2023, 7, 13) + datetime.timedelta(weeks=6 + 6 + 1),
}

# ensure that the **latest** rust version is the last one!
_RUST_VERSIONS = ["1.73", "1.74"]

assert (
    len(_RUST_VERSIONS) == 2
), "Only two versions of rust must be supported at the same time"

RUST_CONTAINERS = [
    LanguageStackContainer(
        name="rust",
        stability_tag=(
            stability_tag := (
                "stable" if (rust_version == _RUST_VERSIONS[-1]) else "oldstable"
            )
        ),
        package_name=f"rust-{stability_tag}-image",
        os_version=os_version,
        support_level=SupportLevel.L3,
        is_latest=(
            rust_version == _RUST_VERSIONS[-1]
            and os_version in CAN_BE_LATEST_OS_VERSION
        ),
        supported_until=_RUST_SUPPORT_ENDS.get(rust_version, None),
        pretty_name=f"Rust {rust_version}",
        package_list=[
            f"rust{rust_version}",
            f"cargo{rust_version}",
        ]
        + os_version.lifecycle_data_pkg,
        version=rust_version,
        env={
            "RUST_VERSION": "%%RUST_VERSION%%",
            "CARGO_VERSION": "%%CARGO_VERSION%%",
            "CC": _RUST_GCC_PATH,
        },
        extra_files={
            # prevent ftbfs on workers with a root partition with 4GB
            "_constraints": generate_disk_size_constraints(6)
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
RUN ln -sf $(ls /usr/bin/gcc-*|grep -P ".*gcc-[[:digit:]]+") {_RUST_GCC_PATH}
# smoke test that gcc works
RUN gcc --version
RUN ${{CC}} --version
""",
    )
    for rust_version, os_version in product(
        _RUST_VERSIONS,
        ALL_NONBASE_OS_VERSIONS,
    )
]
