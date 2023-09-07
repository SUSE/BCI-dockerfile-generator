#!/bin/bash
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: (c) 2022-2023 SUSE LLC

set -euo pipefail

test -f /.kconfig && . /.kconfig
test -f /.profile && . /.profile

echo "Configure image: [$kiwi_iname]..."

#============================================
# Import repositories' keys if rpm is present
#--------------------------------------------
if command -v rpm > /dev/null; then
    suseImportBuildKey
fi

echo "Configure image: [$kiwi_iname]..."

# don't have multiple licenses of the same type
jdupes -1 -L -r /usr/share/licenses

#
zypper --non-interactive rm -u jdupes

# Not needed, but neither rpm nor libzypp handle rpmlib(X-CheckUnifiedSystemdir) yet
# which would avoid it being installed by filesystem package
rpm -e compat-usrmerge-tools

# FIXME: stop hardcoding the url, use some external mechanism once available
zypper -n ar --gpgcheck --enable 'https://updates.suse.com/SUSE/Products/ALP-Dolomite/1.0/$basearch/product/' repo-basalt

#======================================
# Disable recommends
#--------------------------------------
sed -i 's/.*solver.onlyRequires.*/solver.onlyRequires = true/g' /etc/zypp/zypp.conf

#======================================
# Exclude docs installation
#--------------------------------------
sed -i 's/.*rpm.install.excludedocs.*/rpm.install.excludedocs = yes/g' /etc/zypp/zypp.conf

#======================================
# Remove locale files
#--------------------------------------
shopt -s globstar
rm -f /usr/share/locale/**/*.mo

# Remove zypp uuid (bsc#1098535)
rm -f /var/lib/zypp/AnonymousUniqueId

# Remove various log files. While it's possible to just rm -rf /var/log/*, that
# would also remove some package owned directories (not %ghost) and some files
# are actually wanted, like lastlog in the !docker case.
# For those wondering about YaST2 here: Kiwi writes /etc/hosts, so the version
# from the netcfg package ends up as /etc/hosts.rpmnew, which zypper writes a
# letter about to /var/log/YaST2/config_diff_2022_03_06.log. Kiwi fixes this,
# but the log file remains.
rm -rf /var/log/{zypper.log,zypp/history,YaST2}

# Remove the entire zypper cache content (not the dir itself, owned by libzypp)
rm -rf /var/cache/zypp/*

# Assign a fixed architecture in zypp.conf, to use the container's arch even if
# the host arch differs (e.g. docker with --platform doesn't affect uname)
arch=$(rpm -q --qf %{arch} glibc)
if [ "$arch" = "i586" ] || [ "$arch" = "i686" ]; then
	sed -i "s/^# arch =.*\$/arch = i686/" /etc/zypp/zypp.conf
	# Verify that it's applied
	grep -q '^arch =' /etc/zypp/zypp.conf
fi


#=======================================
# Clean up after zypper if it is present
#---------------------------------------
if command -v zypper > /dev/null; then
    zypper -n clean
fi

rm -rf /var/log/zypp

exit 0
