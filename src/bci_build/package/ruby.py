"""Ruby Development BCI containers"""

import datetime
from typing import Literal

from bci_build.container_attributes import SupportLevel
from bci_build.os_version import CAN_BE_LATEST_OS_VERSION
from bci_build.os_version import OsVersion
from bci_build.package import DevelopmentContainer
from bci_build.package import generate_disk_size_constraints
from bci_build.replacement import Replacement
from bci_build.util import ParseVersion

_RUBY_SUPPORT_ENDS = {"2.5": None, "3.4": datetime.date(2028, 3, 31)}


def _get_ruby_kwargs(ruby_version: Literal["2.5", "3.4"], os_version: OsVersion):
    ruby = f"ruby{ruby_version}"
    ruby_major = ruby_version.split(".")[0]

    return {
        "name": "ruby",
        "package_name": f"ruby-{ruby_version}-image",
        "pretty_name": f"Ruby {ruby_version}",
        "version": ruby_version,
        "additional_versions": [ruby_major],
        "is_latest": ruby_version == "3.4" and os_version in CAN_BE_LATEST_OS_VERSION,
        "os_version": os_version,
        "supported_until": (
            _RUBY_SUPPORT_ENDS.get(ruby_version) if os_version.is_sle15 else None
        ),
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
        "package_list": [ruby]
        # bundler is part of ruby itself as of Ruby 3.4,
        # it exists as a standalone gem only in Tumbleweed
        + (
            []
            if ruby_version == "3.4" and os_version.is_sle15
            else [f"{ruby}-rubygem-bundler"]
        )
        + [
            f"{ruby}-devel",
            # force the correct gem2rpm version to avoid system ruby being pulled
            f"{ruby}-rubygem-gem2rpm",
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
        "config_sh_script": (
            # workaround for https://bugzilla.suse.com/show_bug.cgi?id=1237324
            (
                """update-alternatives --set rake /usr/bin/rake.ruby.ruby3.4; \\
    update-alternatives --set rdoc /usr/bin/rdoc.ruby.ruby3.4; \\
    update-alternatives --set ri /usr/bin/ri.ruby.ruby3.4; \\
    ln -s /usr/bin/ruby.ruby3.4 /usr/local/bin/ruby; \\
    ln -s /usr/bin/gem.ruby3.4 /usr/local/bin/gem; \\
"""
            )
            if ruby_version == "3.4" and os_version.is_sle15
            else ""
        )
        # as we only ship one ruby version, we want to make sure that binaries belonging
        # to our gems get installed as `bin` and not as `bin.ruby$ruby_version`
        + "sed -i 's/--format-executable/--no-format-executable/' /etc/gemrc",
    }


RUBY_CONTAINERS = [
    DevelopmentContainer(
        **_get_ruby_kwargs("2.5", OsVersion.SP7),
        support_level=SupportLevel.L3,
    ),
    DevelopmentContainer(
        **_get_ruby_kwargs("3.4", OsVersion.SP7),
        support_level=SupportLevel.L3,
    ),
    DevelopmentContainer(
        **_get_ruby_kwargs("3.4", OsVersion.SL16_0),
        support_level=SupportLevel.L3,
    ),
    DevelopmentContainer(
        **_get_ruby_kwargs("3.4", OsVersion.SL16_1),
        support_level=SupportLevel.L3,
    ),
    DevelopmentContainer(**_get_ruby_kwargs("3.4", OsVersion.TUMBLEWEED)),
]
