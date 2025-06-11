"""The base container image is the base image with zypper included."""

from dataclasses import dataclass
from pathlib import Path

from jinja2 import Template

from bci_build.container_attributes import Arch
from bci_build.container_attributes import BuildType
from bci_build.container_attributes import PackageType
from bci_build.container_attributes import SupportLevel
from bci_build.os_version import CAN_BE_LATEST_BASE_OS_VERSION
from bci_build.os_version import _SUPPORTED_UNTIL_SLE
from bci_build.os_version import OsVersion
from bci_build.package import OsContainer
from bci_build.package import Package


def _get_base_config_sh_script(os_version: OsVersion) -> str:
    return Template(
        r"""
echo "Configure image: [$kiwi_iname]..."

#======================================
# Setup baseproduct link
#--------------------------------------
suseSetupProduct

# don't have duplicate licenses of the same type
jdupes -1 -L -r /usr/share/licenses

{% if os_version.is_tumbleweed -%}
#======================================
# Add repos from control.xml
#--------------------------------------
add-yast-repos
zypper --non-interactive rm -u live-add-yast-repos jdupes
{% else -%}
zypper --non-interactive rm -u jdupes
{% endif %}

# Not needed, but neither rpm nor libzypp handle rpmlib(X-CheckUnifiedSystemdir) yet
# which would avoid it being installed by filesystem package
rpm -q compat-usrmerge-tools && rpm -e compat-usrmerge-tools

#======================================
# Disable recommends
#--------------------------------------
sed -i 's/.*solver.onlyRequires.*/solver.onlyRequires = true/g' /etc/zypp/zypp.conf

#======================================
# Exclude docs installation
#--------------------------------------
sed -i 's/.*rpm.install.excludedocs.*/rpm.install.excludedocs = yes/g' /etc/zypp/zypp.conf

#======================================
# Configure SLE BCI repositories
#--------------------------------------
{% if os_version.is_sle15 and not os_version.is_ltss -%}
zypper -n ar --refresh --gpgcheck --priority 100 --enable 'https://public-dl.suse.com/SUSE/Products/SLE-BCI/$releasever_major-SP$releasever_minor/$basearch/product/' SLE_BCI
zypper -n ar --refresh --gpgcheck --priority 100 --disable 'https://public-dl.suse.com/SUSE/Products/SLE-BCI/$releasever_major-SP$releasever_minor/$basearch/product_debug/' SLE_BCI_debug
zypper -n ar --refresh --gpgcheck --priority 100 --disable 'https://public-dl.suse.com/SUSE/Products/SLE-BCI/$releasever_major-SP$releasever_minor/$basearch/product_source/' SLE_BCI_source
{%- elif os_version.is_sl16 and not os_version.is_ltss -%}
zypper -n ar --refresh --gpgcheck --priority 100 --enable 'https://public-dl.suse.com/SUSE/Products/SLE-BCI/$releasever_major.$releasever_minor/$basearch/product/' SLE_BCI
zypper -n ar --refresh --gpgcheck --priority 100 --disable 'https://public-dl.suse.com/SUSE/Products/SLE-BCI/$releasever_major.$releasever_minor/$basearch/product_debug/' SLE_BCI_debug
zypper -n ar --refresh --gpgcheck --priority 100 --disable 'https://public-dl.suse.com/SUSE/Products/SLE-BCI/$releasever_major.$releasever_minor/$basearch/product_source/' SLE_BCI_source
{%- endif %}

#======================================
# Remove zypp uuid (bsc#1098535)
#--------------------------------------
rm -f /var/lib/zypp/AnonymousUniqueId

# Remove the entire zypper cache content (not the dir itself, owned by libzypp)
rm -rf /var/cache/zypp/*

{% if os_version.is_tumbleweed -%}
# Assign a fixed architecture in zypp.conf, to use the container's arch even if
# the host arch differs (e.g. docker with --platform doesn't affect uname)
arch=$(rpm -q --qf %{arch} glibc)
if [ "$arch" = "i586" ] || [ "$arch" = "i686" ]; then
    sed -i "s/^# arch =.*\$/arch = i686/" /etc/zypp/zypp.conf
    # Verify that it's applied
    grep -q '^arch =' /etc/zypp/zypp.conf
fi
{%- endif -%}

#==========================================
# Hack! The go container management tools can't handle sparse files:
# https://github.com/golang/go/issues/13548
# If lastlog doesn't exist, useradd doesn't attempt to reserve space,
# also in derived containers.
#------------------------------------------
rm -f /var/log/lastlog

#======================================
# Remove locale files
#--------------------------------------
(shopt -s globstar; rm -f /usr/share/locale/**/*.mo)
"""
    ).render(os_version=os_version)


@dataclass
class Sles15Image(OsContainer):
    @property
    def build_tags(self) -> list[str]:
        tags: list[str] = []
        if self.os_version.is_sle15:
            tags.extend(
                ("suse/sle15:%OS_VERSION_ID_SP%", f"suse/sle15:{self.image_ref_name}")
            )
        tags += super().build_tags
        return tags

    @property
    def uid(self) -> str:
        return "sles15"


def _get_base_kwargs(os_version: OsVersion) -> dict:
    package_name: str = "base-image"
    if os_version.is_ltss:
        package_name = "sles15-ltss-image"
    elif os_version.is_sle15:
        package_name = "sles15-image"

    return {
        "name": "base",
        "pretty_name": "%OS_VERSION_NO_DASH% Base",
        "package_name": package_name,
        "custom_description": "Image for containers based on %OS_PRETTY_NAME%.",
        "logo_url": "https://opensource.suse.com/bci/SLE_BCI_logomark_green.svg",
        "build_recipe_type": BuildType.KIWI,
        "from_image": None,
        "os_version": os_version,
        "support_level": SupportLevel.L3,
        "supported_until": _SUPPORTED_UNTIL_SLE.get(os_version),
        # we need to exclude i586 and other ports arches from building base images
        "exclusive_arch": [Arch.AARCH64, Arch.X86_64, Arch.PPC64LE, Arch.S390X],
        "kiwi_ignore_packages": ["rpm"] if os_version.is_sle15 else [],
        "is_latest": os_version in CAN_BE_LATEST_BASE_OS_VERSION,
        "extra_files": {
            "LICENSE": (Path(__file__).parent / "base" / "LICENSE").read_text(),
        },
        "package_list": [
            Package(name=pkg_name, pkg_type=PackageType.IMAGE)
            for pkg_name in sorted(
                [
                    "bash",
                    "ca-certificates-mozilla",
                    "container-suseconnect",
                    "coreutils",
                    "curl",
                    "gzip",
                    "netcfg",
                    "openssl-3",
                    "tar",
                    "timezone",
                    # for run.oci.keep_original_groups=1 (see bsc#1212118)
                    "user(nobody)",
                    *os_version.eula_package_names,
                ]
                + (
                    [
                        "sle-module-basesystem-release",
                        "sle-module-server-applications-release",
                        "sle-module-python3-release",
                    ]
                    if os_version.is_sle15
                    else []
                )
                + (
                    ["openSUSE-build-key"]
                    if os_version.is_tumbleweed
                    else ["suse-build-key"]
                )
            )
        ]
        + [
            Package(name=pkg_name, pkg_type=PackageType.BOOTSTRAP)
            for pkg_name in sorted(
                [
                    "aaa_base",
                    "cracklib-dict-small",
                    "filesystem",
                    "jdupes",
                    "shadow",
                    "zypper",
                ]
                + (
                    ["libcurl-mini4", "libopenssl-3-fips-provider"]
                    if os_version.is_sl16
                    else []
                )
                + (
                    ["kubic-locale-archive", "rpm-ndb", "patterns-base-fips"]
                    if os_version.is_sle15
                    else ["glibc-locale-base"]
                )
                + (
                    ["patterns-base-minimal_base"]
                    if os_version not in (OsVersion.SP5,)
                    else []
                )
                + [*os_version.release_package_names]
            )
        ]
        + (
            [
                Package(name=pkg_name, pkg_type=PackageType.DELETE)
                for pkg_name in sorted(("chkstat", "permissions", "permissions-config"))
            ]
            if not os_version.is_sle15
            else []
        ),
        "config_sh_script": _get_base_config_sh_script(os_version),
        "_min_release_counter": 40,
    }


# TODO merge in tumbleweed changes and switch to ALL_BASE_OS_VERSIONS
BASE_CONTAINERS = [
    Sles15Image(**_get_base_kwargs(os_ver)) for os_ver in (OsVersion.SP6, OsVersion.SP7)
] + [
    OsContainer(**_get_base_kwargs(os_version=os_ver))
    for os_ver in (OsVersion.SLE16_0,)
]
