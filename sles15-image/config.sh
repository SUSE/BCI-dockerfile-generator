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
suseSetupProduct


# don't have duplicate licenses of the same type
jdupes -1 -L -r /usr/share/licenses

zypper --non-interactive rm -u jdupes


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
zypper -n ar --refresh --gpgcheck --priority 100 --enable 'https://updates.suse.com/SUSE/Products/SLE-BCI/$releasever_major-SP$releasever_minor/$basearch/product/' SLE_BCI
zypper -n ar --refresh --gpgcheck --priority 100 --disable 'https://updates.suse.com/SUSE/Products/SLE-BCI/$releasever_major-SP$releasever_minor/$basearch/product_debug/' SLE_BCI_debug
zypper -n ar --refresh --gpgcheck --priority 100 --disable 'https://updates.suse.com/SUSE/Products/SLE-BCI/$releasever_major-SP$releasever_minor/$basearch/product_source/' SLE_BCI_source

#======================================
# Remove zypp uuid (bsc#1098535)
#--------------------------------------
rm -f /var/lib/zypp/AnonymousUniqueId

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
(shopt -s globstar; rm -f /usr/share/locale/**/*.mo)

#=======================================
# Clean up after zypper if it is present
#---------------------------------------
if command -v zypper > /dev/null; then
    zypper -n clean
fi

rm -rf /var/log/{lastlog,tallylog,zypper.log,zypp/history,YaST2}

exit 0
