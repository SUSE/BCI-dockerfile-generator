#!/bin/bash
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: (c) 2022-2024 SUSE LLC

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

#======================================
# Setup baseproduct link
#--------------------------------------
suseImportBuildKey


# don't have duplicate licenses of the same type
jdupes -1 -L -r /usr/share/licenses

#======================================
# Add repos from control.xml
#--------------------------------------
add-yast-repos
zypper --non-interactive rm -u live-add-yast-repos jdupes


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
# Remove zypp uuid (bsc#1098535)
#--------------------------------------
rm -f /var/lib/zypp/AnonymousUniqueId

# Remove the entire zypper cache content (not the dir itself, owned by libzypp)
rm -rf /var/cache/zypp/*

# Assign a fixed architecture in zypp.conf, to use the container's arch even if
# the host arch differs (e.g. docker with --platform doesn't affect uname)
arch=$(rpm -q --qf %{arch} glibc)
if [ "$arch" = "i586" ] || [ "$arch" = "i686" ]; then
    sed -i "s/^# arch =.*\$/arch = i686/" /etc/zypp/zypp.conf
    # Verify that it's applied
    grep -q '^arch =' /etc/zypp/zypp.conf
fi#==========================================
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

#=======================================
# Clean up after zypper if it is present
#---------------------------------------
if command -v zypper > /dev/null; then
    zypper -n clean
fi

rm -rf /var/log/{lastlog,tallylog,zypper.log,zypp/history,YaST2}

exit 0
