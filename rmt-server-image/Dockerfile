# SPDX-License-Identifier: MIT
#!BuildTag: opensuse/rmt-server:%%rmt_version%%
#!BuildTag: opensuse/rmt-server:latest
#!BuildTag: opensuse/rmt-server:%%rmt_version%%-%RELEASE%

FROM opensuse/tumbleweed:latest

MAINTAINER openSUSE (https://www.opensuse.org/)

# Define labels according to https://en.opensuse.org/Building_derived_containers
# labelprefix=org.opensuse.application.rmt-server
LABEL org.opencontainers.image.title="openSUSE Tumbleweed RMT Server Container Image"
LABEL org.opencontainers.image.description="SUSE RMT Server based on the SLE Base Container Image."
LABEL org.opencontainers.image.version="%%rmt_version%%"
LABEL org.opencontainers.image.url="https://www.opensuse.org"
LABEL org.opencontainers.image.created="%BUILDTIME%"
LABEL org.opencontainers.image.vendor="openSUSE Project"
LABEL org.opensuse.reference="registry.opensuse.org/opensuse/rmt-server:%%rmt_version%%-%RELEASE%"
LABEL org.openbuildservice.disturl="%DISTURL%"

LABEL com.suse.release-stage="released"
# endlabelprefix

RUN set -euo pipefail; zypper -n in --no-recommends rmt-server catatonit; zypper -n clean; rm -rf /var/log/*
ENV RAILS_ENV="production"
ENV LANG="en"

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["/usr/share/rmt/bin/rails", "server", "-e", "production"]
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN set -euo pipefail; chmod +x /usr/local/bin/entrypoint.sh
