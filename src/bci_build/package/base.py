""" The base container image is the base image with zypper included."""

import textwrap

from bci_build.package import ALL_BASE_OS_VERSIONS
from bci_build.package import OsVersion
from bci_build.package import OsContainer
from bci_build.package import BuildType
from bci_build.package import SupportLevel
from bci_build.package import Package
from bci_build.package import PackageType
from bci_build.package import CAN_BE_LATEST_OS_VERSION

def _get_base_config_sh_script(os_version: OsVersion) -> str:
    return textwrap.dedent(
        r"""
echo "Configure image: [$kiwi_iname]..."

#======================================
# Setup baseproduct link
#--------------------------------------
suseSetupProduct

#======================================
# Import repositories' keys
#--------------------------------------
suseImportBuildKey


# don't have duplicate licenses of the same type
jdupes -1 -L -r /usr/share/licenses

zypper --non-interactive rm -u jdupes

# Not needed, but neither rpm nor libzypp handle rpmlib(X-CheckUnifiedSystemdir) yet
# which would avoid it being installed by filesystem package
rpm -e compat-usrmerge-tools

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
zypper -n ar --refresh --gpgcheck --priority 100 --enable 'https://updates.suse.com/SUSE/Products/SLE-BCI/$releasever_major-SP$releasever_minor/$basearch/product/' SLE_BCI
zypper -n ar --refresh --gpgcheck --priority 100 --disable 'https://updates.suse.com/SUSE/Products/SLE-BCI/$releasever_major-SP$releasever_minor/$basearch/product_debug/' SLE_BCI_debug
zypper -n ar --refresh --gpgcheck --priority 100 --disable 'https://updates.suse.com/SUSE/Products/SLE-BCI/$releasever_major-SP$releasever_minor/$basearch/product_source/' SLE_BCI_source

#======================================
# Remove locale files
#--------------------------------------
shopt -s globstar
rm -f /usr/share/locale/**/*.mo

#======================================
# Remove zypp uuid (bsc#1098535)
#--------------------------------------
rm -f /var/lib/zypp/AnonymousUniqueId

# Remove various log files. Although possible to just rm -rf /var/log/*, that
# would also remove some package owned directories (not %ghost) and some files
# are actually wanted, like lastlog in the !docker case.
# For those wondering about YaST2 here: Kiwi writes /etc/hosts, so the version
# from the netcfg package ends up as /etc/hosts.rpmnew, which zypper writes a
# letter about to /var/log/YaST2/config_diff_2022_03_06.log. Kiwi fixes this,
# but the log file remains.
rm -rf /var/log/{zypper.log,zypp/history,YaST2}

# Remove the entire zypper cache content (not the dir itself, owned by libzypp)
rm -rf /var/cache/zypp/*

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
find /usr/share/locale -name '*.mo' -delete

exit 0
"""
    )


BASE_CONTAINERS = [
    OsContainer(
        name="base",
        pretty_name="Base Container Image",
        package_name="sles15-image" if os_ver.is_sle15 else "base-image",
        logo_url="https://opensource.suse.com/bci/SLE_BCI_logomark_green.svg",
        build_recipe_type=BuildType.KIWI,
        from_image=None,
        os_version=os_ver,
        support_level=SupportLevel.L3,
        is_latest=os_ver in CAN_BE_LATEST_OS_VERSION,
        package_list=[
            Package(name=pkg_name, pkg_type=PackageType.IMAGE)
            for pkg_name in (
                "bash",
                "ca-certificates-mozilla",
                "ca-certificates",
                "container-suseconnect",
                "coreutils",
                "curl",
                "findutils",
                "glibc-locale-base",
                "gzip",
                "lsb-release",
                "netcfg",
                "openssl",
                "skelcd-EULA-bci",
                "sle-module-basesystem-release",
                "sle-module-server-applications-release",
                "sle-module-python3-release",
                "suse-build-key",
                "tar",
                "timezone",
            )
        ]
        + [
            Package(name=pkg_name, pkg_type=PackageType.BOOTSTRAP)
            for pkg_name in (
                "aaa_base",
                "cracklib-dict-small",
                "filesystem",
                "jdupes",
                "kubic-locale-archive",
                "patterns-base-fips",
                "patterns-base-minimal_base",
                "rpm-ndb",
                "shadow",
                "sles-release",
                "zypper",
            )
        ],
        config_sh_script=_get_base_config_sh_script(os_ver),
    )
    for os_ver in ALL_BASE_OS_VERSIONS
]
