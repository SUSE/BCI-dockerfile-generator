"""The base container image is the base image with zypper included."""

from dataclasses import dataclass
from pathlib import Path

from jinja2 import Template

from bci_build.container_attributes import Arch
from bci_build.container_attributes import BuildType
from bci_build.container_attributes import ImageType
from bci_build.container_attributes import PackageType
from bci_build.container_attributes import SupportLevel
from bci_build.os_version import CAN_BE_LATEST_BASE_OS_VERSION
from bci_build.os_version import CAN_BE_SAC_VERSION
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
{%- endif %}

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

{% if os_version.is_sle15 and not os_version.is_ltss -%}
#======================================
# Configure SLE BCI repositories
#--------------------------------------
zypper -n ar --refresh --gpgcheck --priority 100 --enable 'https://public-dl.suse.com/SUSE/Products/SLE-BCI/$releasever_major-SP$releasever_minor/$basearch/product/' SLE_BCI
zypper -n ar --refresh --gpgcheck --priority 100 --disable 'https://public-dl.suse.com/SUSE/Products/SLE-BCI/$releasever_major-SP$releasever_minor/$basearch/product_debug/' SLE_BCI_debug
zypper -n ar --refresh --gpgcheck --priority 100 --disable 'https://public-dl.suse.com/SUSE/Products/SLE-BCI/$releasever_major-SP$releasever_minor/$basearch/product_source/' SLE_BCI_source
{%- elif os_version.is_sl16 and not os_version.is_ltss -%}
#======================================
# Configure SLE BCI repositories
#--------------------------------------
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

# drop timestamp
tail -n +2 /var/lib/zypp/AutoInstalled > /var/lib/zypp/AutoInstalled.new && mv /var/lib/zypp/AutoInstalled.new /var/lib/zypp/AutoInstalled

# drop useless device/inode specific cache file (see https://github.com/docker-library/official-images/issues/16044)
rm -vf /var/cache/ldconfig/aux-cache

# remove backup of /etc/{shadow,group,passwd} and lock file
rm -vf /etc/{shadow-,group-,passwd-,.pwd.lock}

# drop pid and lock files
rm -vrf /run/*
rm -vf /usr/lib/sysimage/rpm/.rpm.lock

# set the day of last password change to empty
sed -i 's/^\([^:]*:[^:]*:\)[^:]*\(:.*\)$/\1\2/' /etc/shadow

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

{% if os_version.is_sle15 and not os_version.is_ltss -%}
#======================================
# Avoid blkid waiting on udev (bsc#1247914)
#--------------------------------------
sed -i -e 's/^EVALUATE=.*/EVALUATE=scan/g' /etc/blkid.conf

{% endif -%}
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
        if self.os_version.is_ltss:
            tags.extend(
                (
                    f"suse/ltss/sle%OS_VERSION_ID_SP%/sle15:{self.image_ref_name}",
                    "suse/ltss/sle%OS_VERSION_ID_SP%/sle15:%OS_VERSION_ID_SP%",
                    "suse/ltss/sle%OS_VERSION_ID_SP%/sle15:latest",
                    f"suse/ltss/sle%OS_VERSION_ID_SP%/bci-base:{self.image_ref_name}",
                    "suse/ltss/sle%OS_VERSION_ID_SP%/bci-base:%OS_VERSION_ID_SP%",
                )
            )
        elif self.os_version.is_sle15:
            tags.extend(
                ("suse/sle15:%OS_VERSION_ID_SP%", f"suse/sle15:{self.image_ref_name}")
            )
            if self.os_version in CAN_BE_LATEST_BASE_OS_VERSION:
                tags.append("suse/sle15:latest")
            tags += super().build_tags
        return tags

    @property
    def image_type(self) -> ImageType:
        if self.os_version.is_ltss:
            return ImageType.LTSS
        return super().image_type

    @property
    def uid(self) -> str:
        return "sles15-ltss" if self.os_version.is_ltss else "sles15"

    @property
    def eula(self) -> str:
        if self.os_version.is_ltss:
            return "sle-eula"
        return super().eula

    @property
    def registry_prefix(self) -> str:
        if self.os_version.is_ltss:
            if self.os_version == OsVersion.SP3:
                return "suse/ltss/sle15.3"
            if self.os_version == OsVersion.SP4:
                return "suse/ltss/sle15.4"
            if self.os_version == OsVersion.SP5:
                return "suse/ltss/sle15.5"
        return super().registry_prefix


def _get_base_kwargs(os_version: OsVersion) -> dict:
    package_name: str = "base-image"
    if os_version.is_ltss:
        package_name = "sles15-ltss-image"
    elif os_version.is_sle15:
        package_name = "sles15-image"

    return {
        "name": "base",
        "pretty_name": ("Base" if os_version.is_ltss else "%OS_VERSION_NO_DASH% Base"),
        "package_name": package_name,
        "custom_description": "Image for containers based on %OS_PRETTY_NAME%.",
        "logo_url": (
            None
            if os_version.is_ltss
            else "https://opensource.suse.com/bci/SLE_BCI_logomark_green.svg"
        ),
        "build_recipe_type": BuildType.KIWI,
        "from_image": None,
        "os_version": os_version,
        "support_level": SupportLevel.L3,
        "supported_until": (
            _SUPPORTED_UNTIL_SLE.get(os_version) if not os_version.is_ltss else None
        ),
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
                    "patterns-base-minimal_base",
                    "tar",
                    "timezone",
                    *os_version.eula_package_names,
                ]
                # for run.oci.keep_original_groups=1 (see bsc#1212118)
                + (["user(nobody)"] if not os_version.is_ltss else [])
                + (
                    [
                        "sle-module-basesystem-release",
                        "sle-module-server-applications-release",
                        "sle-module-python3-release",
                    ]
                    if os_version.is_sle15 and not os_version.is_ltss
                    else []
                )
                + (
                    ["openSUSE-build-key"]
                    if os_version.is_tumbleweed
                    else ["suse-build-key"]
                )
                + (
                    ["procps"]
                    if os_version in (OsVersion.SP3, OsVersion.SP4, OsVersion.SP5)
                    else []
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
        "post_build_checks_containers": os_version in CAN_BE_SAC_VERSION,
    }


# TODO merge in tumbleweed changes and switch to ALL_BASE_OS_VERSIONS
BASE_CONTAINERS = [
    Sles15Image(**_get_base_kwargs(os_ver))
    for os_ver in (
        OsVersion.SP3,
        OsVersion.SP4,
        OsVersion.SP5,
        OsVersion.SP6,
        OsVersion.SP7,
    )
] + [
    OsContainer(**_get_base_kwargs(os_version=os_ver))
    for os_ver in (OsVersion.SL16_0, OsVersion.SL16_1)
]
