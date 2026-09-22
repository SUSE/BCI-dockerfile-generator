"""Ruby Development BCI containers"""

import datetime
from itertools import product
from typing import Literal

from bci_build.container_attributes import SupportLevel
from bci_build.containercrate import ContainerCrate
from bci_build.os_version import CAN_BE_LATEST_OS_VERSION
from bci_build.os_version import OsVersion
from bci_build.package import DevelopmentContainer
from bci_build.package import generate_disk_size_constraints
from bci_build.package.helpers import generate_from_image_tag
from bci_build.replacement import Replacement
from bci_build.util import ParseVersion

_RUBY_SUPPORT_ENDS = {"2.5": None, "3.4": datetime.date(2028, 3, 31)}


def _get_ruby_kwargs(
    ruby_version: Literal["2.5", "3.4", "4.0"],
    os_version: OsVersion,
    build_flavor: str | None = None,
):
    ruby = f"ruby{ruby_version}"
    is_micro = build_flavor == "micro"

    package_list = (
        [
            ruby,
            # force the correct gem2rpm version to avoid system ruby being pulled
            f"{ruby}-rubygem-gem2rpm",
            # provides getopt, which is required by ruby-common, but OBS doesn't resolve that
            "util-linux",
            # additional dependencies supplementing rails
            "timezone",
            "xz",
            # required by config_sh_script section
            "sed",
        ]
        # additional dependencies for nokogiri gem (for rails)
        # nokogiri requires also libxml2 and libyaml
        # but these are already in the image
        + (["libxslt1"] if os_version.is_sle15 else ["libexslt0"])
    )

    if not is_micro:
        package_list += [
            f"{ruby}-devel",
            *os_version.common_devel_packages,
            # additional dependencies to build rails, ffi, sqlite3 gems -->
            "gcc-c++",
            "sqlite3-devel",
            "make",
        ]

        # bundler is part of ruby itself as of Ruby 3.4,
        # it exists as a standalone gem only in Tumbleweed
        package_list += (
            [f"{ruby}-rubygem-bundler"]
            if (ruby_version == "2.5" and os_version.is_sle15)
            or os_version in (OsVersion.SL16_1, OsVersion.TUMBLEWEED)
            else []
        )

    return {
        "name": "ruby",
        "package_name": f"ruby-{ruby_version}-image",
        "pretty_name": (
            f"Ruby {ruby_version} {build_flavor} runtime"
            if is_micro
            else f"Ruby {ruby_version} development"
        ),
        "version": ruby_version,
        "build_flavor": build_flavor,
        "tag_version": ruby_version,
        "is_latest": (
            not is_micro
            and os_version in CAN_BE_LATEST_OS_VERSION
            and (
                (ruby_version == "3.4" and not os_version.is_tumbleweed)
                or (ruby_version == "4.0" and os_version.is_tumbleweed)
            )
        ),
        "from_target_image": (
            generate_from_image_tag(os_version, "bci-micro") if is_micro else None
        ),
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
        "package_list": sorted(package_list),
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


RUBY_2_5_CONTAINERS = [
    DevelopmentContainer(
        **_get_ruby_kwargs("2.5", OsVersion.SP7),
        additional_versions=["2", f"2.5-{OsVersion.SP7.dist_id}"],
        support_level=SupportLevel.L3,
    ),
]

RUBY_3_4_CONTAINERS = [
    DevelopmentContainer(
        **_get_ruby_kwargs("3.4", OsVersion.SP7),
        additional_versions=["3", f"3.4-{OsVersion.SP7.dist_id}"],
        support_level=SupportLevel.L3,
    )
] + [
    DevelopmentContainer(
        **_get_ruby_kwargs("3.4", os_version, flavor),
        support_level=SupportLevel.L3,
    )
    for os_version, flavor in product(
        (OsVersion.SL16_0, OsVersion.SL16_1), ("base", "micro")
    )
]

RUBY_4_0_CONTAINERS = [
    DevelopmentContainer(
        **_get_ruby_kwargs("4.0", os_version, flavor),
        additional_versions=["4"],
    )
    for os_version, flavor in product((OsVersion.TUMBLEWEED,), ("base", "micro"))
]

RUBY_CONTAINERS = RUBY_2_5_CONTAINERS + RUBY_3_4_CONTAINERS + RUBY_4_0_CONTAINERS

RUBY_CRATE = ContainerCrate(RUBY_CONTAINERS)
