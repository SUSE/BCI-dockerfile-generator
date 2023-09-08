# SPDX-License-Identifier: MIT
#!BuildTag: bci/rust:stable
#!BuildTag: bci/rust:stable-1.%RELEASE%
#!BuildTag: bci/rust:1.71
#!BuildTag: bci/rust:1.71-1.%RELEASE%
#!BuildTag: bci/rust:latest
#!BuildVersion: 15.5.1.71.1
FROM suse/sle15:15.5

MAINTAINER SUSE LLC (https://www.suse.com/)

# Define labels according to https://en.opensuse.org/Building_derived_containers
# labelprefix=com.suse.bci.rust
LABEL org.opencontainers.image.title="SLE BCI Rust 1.71"
LABEL org.opencontainers.image.description="Rust 1.71 container based on the SLE Base Container Image."
LABEL org.opencontainers.image.version="1.71"
LABEL org.opencontainers.image.url="https://www.suse.com/products/server/"
LABEL org.opencontainers.image.created="%BUILDTIME%"
LABEL org.opencontainers.image.vendor="SUSE LLC"
LABEL org.opencontainers.image.source="%SOURCEURL%"
LABEL org.opensuse.reference="registry.suse.com/bci/rust:1.71-1.%RELEASE%"
LABEL org.openbuildservice.disturl="%DISTURL%"
LABEL com.suse.supportlevel="l3"
LABEL com.suse.eula="sle-bci"
LABEL com.suse.lifecycle-url="https://www.suse.com/lifecycle#suse-linux-enterprise-server-15"
LABEL com.suse.image-type="sle-bci"
LABEL com.suse.release-stage="released"
# endlabelprefix

RUN set -euo pipefail; zypper -n in --no-recommends rust1.71 cargo1.71; zypper -n clean; rm -rf /var/log/*
ENV RUST_VERSION="%%RUST_VERSION%%"
ENV CARGO_VERSION="%%CARGO_VERSION%%"
ENV CC="/usr/local/bin/gcc"

# workaround for gcc only existing as /usr/bin/gcc-N
RUN ln -sf $(ls /usr/bin/gcc-*|grep -P ".*gcc-[[:digit:]]+") /usr/local/bin/gcc
# smoke test that gcc works
RUN gcc --version
RUN ${CC} --version
