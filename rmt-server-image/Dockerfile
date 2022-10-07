# SPDX-License-Identifier: MIT
#!BuildTag: suse/rmt-server:%%rmt_version%%
#!BuildTag: suse/rmt-server:latest
#!BuildTag: suse/rmt-server:%%rmt_version%%-%RELEASE%
#!BuildVersion: 15.4
FROM suse/sle15:15.4

MAINTAINER SUSE LLC (https://www.suse.com/)

# Define labels according to https://en.opensuse.org/Building_derived_containers
# labelprefix=com.suse.application.rmt-server
LABEL org.opencontainers.image.title="SLE RMT Server Container Image"
LABEL org.opencontainers.image.description="SUSE RMT Server based on the SLE Base Container Image."
LABEL org.opencontainers.image.version="%%rmt_version%%"
LABEL org.opencontainers.image.url="https://www.suse.com/products/server/"
LABEL org.opencontainers.image.created="%BUILDTIME%"
LABEL org.opencontainers.image.vendor="SUSE LLC"
LABEL org.opensuse.reference="registry.suse.com/suse/rmt-server:%%rmt_version%%-%RELEASE%"
LABEL org.openbuildservice.disturl="%DISTURL%"
LABEL com.suse.supportlevel="techpreview"
LABEL com.suse.eula="sle-bci"
LABEL com.suse.lifecycle-url="https://www.suse.com/lifecycle"
LABEL com.suse.image-type="application"
LABEL com.suse.release-stage="released"
# endlabelprefix

RUN set -euo pipefail; zypper -n in --no-recommends rmt-server catatonit; zypper -n clean; rm -rf /var/log/*
ENV RAILS_ENV="production"
ENV LANG="en"

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["/usr/share/rmt/bin/rails", "server", "-e", "production"]
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN set -euo pipefail; chmod +x /usr/local/bin/entrypoint.sh
