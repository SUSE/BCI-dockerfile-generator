#!/bin/sh
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: (c) 2022-2025 SUSE LLC

set -euo pipefail

#======================================
# Image Cleanup
#--------------------------------------
if command -v zypper > /dev/null; then
    zypper -n clean -a
    # drop timestamp
    tail -n +2 /var/lib/zypp/AutoInstalled > /var/lib/zypp/AutoInstalled.new && mv /var/lib/zypp/AutoInstalled.new /var/lib/zypp/AutoInstalled
else
    # it does not make sense in a zypper-free image
    rm -vrf /var/lib/zypp/AutoInstalled
    rm -vrf /usr/lib/sysimage/rpm/Index.db
fi

# set the day of last password change to empty
# prefer sed if available
if command -v sed > /dev/null; then
    sed -i 's/^\([^:]*:[^:]*:\)[^:]*\(:.*\)$/\1\2/' /etc/shadow
else
    while IFS=: read -r username password last_change min_age max_age warn inactive expire reserved; do
        echo "$username:$password::$min_age:$max_age:$warn:$inactive:$expire:$reserved" >> /etc/shadow.new
    done < /etc/shadow
    mv /etc/shadow.new /etc/shadow
    chmod 640 /etc/shadow
fi

# remove logs and temporary files
rm -vrf /var/log/alternatives.log
rm -vrf /var/log/lastlog
rm -vrf /var/log/tallylog
rm -vrf /var/log/zypper.log
rm -vrf /var/log/zypp/history
rm -vrf /var/log/YaST2
rm -vrf /var/lib/zypp/AnonymousUniqueId
rm -vrf /var/cache/zypp/*
rm -vrf /run/*
rm -vrf /etc/shadow-
rm -vrf /etc/group-
rm -vrf /etc/passwd-
rm -vrf /etc/.pwd.lock
rm -vrf /usr/lib/sysimage/rpm/.rpm.lock
rm -vrf /var/cache/ldconfig/aux-cache


exit 0
