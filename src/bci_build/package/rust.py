"""Rust language BCI container"""

import datetime
from itertools import product

from bci_build.package import ALL_NONBASE_OS_VERSIONS
from bci_build.package import CAN_BE_LATEST_OS_VERSION
from bci_build.package import DevelopmentContainer
from bci_build.package import Replacement
from bci_build.package import SupportLevel
from bci_build.package import generate_disk_size_constraints

_RUST_GCC_PATH = "/usr/local/bin/gcc"

# release dates are coming from upstream - https://raw.githubusercontent.com/rust-lang/rust/master/RELEASES.md
# we expect a new release every 6 weeks, two releases are supported at any point in time
# and we give us three weeks of buffer, leading to release date + 6 + 6 + 3
_RUST_SUPPORT_ENDS = {
    "1.79": datetime.date(2024, 6, 13) + datetime.timedelta(weeks=6 + 6 + 3),
    "1.78": datetime.date(2024, 5, 2) + datetime.timedelta(weeks=6 + 6 + 3),
    "1.77": datetime.date(2024, 3, 21) + datetime.timedelta(weeks=6 + 6 + 3),
    "1.76": datetime.date(2024, 2, 8) + datetime.timedelta(weeks=6 + 6 + 3),
    "1.75": datetime.date(2023, 12, 28) + datetime.timedelta(weeks=6 + 6 + 3),
}

# ensure that the **latest** rust version is the last one!
_RUST_VERSIONS = ["1.78", "1.79"]

assert (
    len(_RUST_VERSIONS) == 2
), "Only two versions of rust must be supported at the same time"

RUST_CONTAINERS = [
    DevelopmentContainer(
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
        supported_until=_RUST_SUPPORT_ENDS.get(rust_version),
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
RUN ln -sf $(ls /usr/bin/gcc-*|grep -P ".*gcc-[[:digit:]]+") {_RUST_GCC_PATH}
# smoke test that gcc works
RUN gcc --version
RUN ${{CC}} --version
COPY {check_fname} /etc/zypp/systemCheck.d/{check_fname}
""",
    )
    for rust_version, os_version in product(
        _RUST_VERSIONS,
        ALL_NONBASE_OS_VERSIONS,
    )
]
