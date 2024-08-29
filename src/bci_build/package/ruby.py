"""Ruby Development BCI containers"""

from typing import Literal

from bci_build.package import CAN_BE_LATEST_OS_VERSION
from bci_build.package import DevelopmentContainer
from bci_build.package import OsVersion
from bci_build.package import ParseVersion
from bci_build.package import Replacement
from bci_build.package import SupportLevel
from bci_build.package import generate_disk_size_constraints


def _get_ruby_kwargs(ruby_version: Literal["2.5", "3.3"], os_version: OsVersion):
    ruby = f"ruby{ruby_version}"
    ruby_major = ruby_version.split(".")[0]

    return {
        "name": "ruby",
        "package_name": f"ruby-{ruby_version}-image",
        "pretty_name": f"Ruby {ruby_version}",
        "version": ruby_version,
        "additional_versions": [ruby_major],
        "is_latest": os_version in CAN_BE_LATEST_OS_VERSION,
        "os_version": os_version,
        "env": {
            # upstream does this
            "LANG": "C.UTF-8",
            "RUBY_VERSION": "%%rb_ver%%",
            "RUBY_MAJOR": "%%rb_maj%%",
        },
        "replacements_via_service": [
            Replacement(regex_in_build_description="%%rb_ver%%", package_name=ruby),
            Replacement(
                regex_in_build_description="%%rb_maj%%",
                package_name=ruby,
                parse_version=ParseVersion.MINOR,
            ),
        ],
        "package_list": [
            ruby,
            f"{ruby}-rubygem-bundler",
            f"{ruby}-devel",
            # provides getopt, which is required by ruby-common, but OBS doesn't resolve that
            "util-linux",
            # additional dependencies to build rails, ffi, sqlite3 gems -->
            "gcc-c++",
            "sqlite3-devel",
            "make",
            # additional dependencies supplementing rails
            "timezone",
        ]
        + os_version.common_devel_packages,
        "extra_files": {
            # avoid ftbfs on workers with a root partition with 4GB
            "_constraints": generate_disk_size_constraints(6)
        },
        # as we only ship one ruby version, we want to make sure that binaries belonging
        # to our gems get installed as `bin` and not as `bin.ruby$ruby_version`
        "config_sh_script": "sed -i 's/--format-executable/--no-format-executable/' /etc/gemrc",
    }


RUBY_CONTAINERS = [
    DevelopmentContainer(
        **_get_ruby_kwargs("2.5", OsVersion.SP6),
        support_level=SupportLevel.L3,
    ),
    DevelopmentContainer(
        **_get_ruby_kwargs("2.5", OsVersion.SP7),
        support_level=SupportLevel.L3,
    ),
    DevelopmentContainer(**_get_ruby_kwargs("3.3", OsVersion.TUMBLEWEED)),
]
