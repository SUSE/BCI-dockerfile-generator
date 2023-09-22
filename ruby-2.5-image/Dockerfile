# SPDX-License-Identifier: MIT
#!BuildTag: bci/ruby:2.5
#!BuildTag: bci/ruby:2.5-%RELEASE%
#!BuildTag: bci/ruby:2
#!BuildTag: bci/ruby:2-%RELEASE%
#!BuildName: bci-ruby-2.5
#!BuildVersion: 15.6.2.5
FROM suse/sle15:15.6

MAINTAINER SUSE LLC (https://www.suse.com/)

# Define labels according to https://en.opensuse.org/Building_derived_containers
# labelprefix=com.suse.bci.ruby
LABEL org.opencontainers.image.title="SLE BCI Ruby 2.5"
LABEL org.opencontainers.image.description="Ruby 2.5 container based on the SLE Base Container Image."
LABEL org.opencontainers.image.version="2.5"
LABEL org.opencontainers.image.url="https://www.suse.com/products/server/"
LABEL org.opencontainers.image.created="%BUILDTIME%"
LABEL org.opencontainers.image.vendor="SUSE LLC"
LABEL org.opencontainers.image.source="%SOURCEURL%"
LABEL org.opensuse.reference="registry.suse.com/bci/ruby:2.5-%RELEASE%"
LABEL org.openbuildservice.disturl="%DISTURL%"
LABEL com.suse.supportlevel="l3"
LABEL com.suse.eula="sle-bci"
LABEL com.suse.lifecycle-url="https://www.suse.com/lifecycle#suse-linux-enterprise-server-15"
LABEL com.suse.image-type="sle-bci"
LABEL com.suse.release-stage="beta"
# endlabelprefix

RUN set -euo pipefail; zypper -n in --no-recommends ruby2.5 ruby2.5-rubygem-bundler ruby2.5-devel util-linux curl git-core gcc-c++ sqlite3-devel make awk timezone; zypper -n clean; rm -rf /var/log/*
ENV LANG="C.UTF-8"
ENV RUBY_VERSION="%%rb_ver%%"
ENV RUBY_MAJOR="%%rb_maj%%"

RUN set -euo pipefail; sed -i 's/--format-executable/--no-format-executable/' /etc/gemrc
