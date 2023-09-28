# SPDX-License-Identifier: MIT
#!BuildTag: bci/golang:oldstable-openssl
#!BuildTag: bci/golang:oldstable-openssl-%RELEASE%
#!BuildTag: bci/golang:1.19-openssl
#!BuildTag: bci/golang:1.19-openssl-%RELEASE%
#!BuildName: bci-golang-oldstable-openssl
#!BuildVersion: 15.5
FROM suse/sle15:15.5

MAINTAINER SUSE LLC (https://www.suse.com/)

# Define labels according to https://en.opensuse.org/Building_derived_containers
# labelprefix=com.suse.bci.golang
LABEL org.opencontainers.image.title="SLE BCI Golang 1.19-openssl"
LABEL org.opencontainers.image.description="Golang 1.19-openssl container based on the SLE Base Container Image."
LABEL org.opencontainers.image.version="1.19-openssl"
LABEL org.opencontainers.image.url="https://www.suse.com/products/server/"
LABEL org.opencontainers.image.created="%BUILDTIME%"
LABEL org.opencontainers.image.vendor="SUSE LLC"
LABEL org.opencontainers.image.source="%SOURCEURL%"
LABEL org.opensuse.reference="registry.suse.com/bci/golang:1.19-openssl-%RELEASE%"
LABEL org.openbuildservice.disturl="%DISTURL%"
LABEL com.suse.supportlevel="l3"
LABEL com.suse.eula="sle-bci"
LABEL com.suse.lifecycle-url="https://www.suse.com/lifecycle#suse-linux-enterprise-server-15"
LABEL com.suse.image-type="sle-bci"
LABEL com.suse.release-stage="released"
# endlabelprefix

RUN set -euo pipefail; zypper -n in --no-recommends go1.19-openssl go1.19-openssl-doc make git-core lifecycle-data-sle-module-development-tools; zypper -n clean; rm -rf /var/log/*
ENV GOLANG_VERSION="%%golang_version%%"
ENV GOPATH="/go"
ENV PATH="/go/bin:/usr/local/go/bin:/root/go/bin/:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"


# only available on go's tsan_arch architectures
#!ArchExclusiveLine x86_64 aarch64 s390x ppc64le
RUN set -euo pipefail; if zypper -n install go1.19-openssl-race; then zypper -n clean; rm -rf /var/log/*; fi
