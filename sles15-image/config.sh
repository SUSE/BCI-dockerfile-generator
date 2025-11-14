#!/bin/bash
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: (c) 2022-2025 SUSE LLC

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
zypper -n ar --refresh --gpgcheck --priority 100 --enable 'https://public-dl.suse.com/SUSE/Products/SLE-BCI/$releasever_major-SP$releasever_minor/$basearch/product/' SLE_BCI
zypper -n ar --refresh --gpgcheck --priority 100 --disable 'https://public-dl.suse.com/SUSE/Products/SLE-BCI/$releasever_major-SP$releasever_minor/$basearch/product_debug/' SLE_BCI_debug
zypper -n ar --refresh --gpgcheck --priority 100 --disable 'https://public-dl.suse.com/SUSE/Products/SLE-BCI/$releasever_major-SP$releasever_minor/$basearch/product_source/' SLE_BCI_source

#======================================
# Avoid blkid waiting on udev (bsc#1247914)
#--------------------------------------
sed -i -e 's/^EVALUATE=.*/EVALUATE=scan/g' /etc/blkid.conf

#======================================
# Remove locale files
#--------------------------------------
(shopt -s globstar; rm -f /usr/share/locale/**/*.mo)

exit 0
