#!ExclusiveArch: x86_64
# SPDX-License-Identifier: MIT
#!BuildTag: bci/dotnet-runtime:6.0
#!BuildTag: bci/dotnet-runtime:6.0-%RELEASE%
#!BuildTag: bci/dotnet-runtime:6.0.13
#!BuildTag: bci/dotnet-runtime:6.0.13-%RELEASE%
#!BuildVersion: 15.4.6.0
FROM suse/sle15:15.4

MAINTAINER SUSE LLC (https://www.suse.com/)

# Define labels according to https://en.opensuse.org/Building_derived_containers
# labelprefix=com.suse.bci.dotnet.runtime
LABEL org.opencontainers.image.title="SLE BCI .NET 6.0 Runtime Container Image"
LABEL org.opencontainers.image.description="The .NET 6.0 Runtime based on the SLE Base Container Image. The .NET packages contained in this image come from a 3rd-party repository http://packages.microsoft.com. You can find the respective source code in https://github.com/dotnet. SUSE doesn't provide any support or warranties."
LABEL org.opencontainers.image.version="6.0"
LABEL org.opencontainers.image.url="https://www.suse.com/products/server/"
LABEL org.opencontainers.image.created="%BUILDTIME%"
LABEL org.opencontainers.image.vendor="SUSE LLC"
LABEL org.opensuse.reference="registry.suse.com/bci/dotnet-runtime:6.0-%RELEASE%"
LABEL org.openbuildservice.disturl="%DISTURL%"
LABEL com.suse.supportlevel="techpreview"
LABEL com.suse.eula="sle-bci"
LABEL com.suse.lifecycle-url="https://www.suse.com/lifecycle"
LABEL com.suse.image-type="sle-bci"
LABEL com.suse.release-stage="released"
# endlabelprefix




# The MS GPG keys
COPY microsoft.asc /tmp

RUN mkdir -p /tmp/

#!RemoteAssetUrl: https://packages.microsoft.com/sles/15/prod/Packages/d/dotnet-host-6.0.13-x64.rpm
COPY dotnet-host-6.0.13-x64.rpm /tmp/
#!RemoteAssetUrl: https://packages.microsoft.com/sles/15/prod/Packages/d/dotnet-hostfxr-6.0.13-x64.rpm
COPY dotnet-hostfxr-6.0.13-x64.rpm /tmp/
#!RemoteAssetUrl: https://packages.microsoft.com/sles/15/prod/Packages/d/dotnet-runtime-deps-6.0.13-sles.12-x64.rpm
COPY dotnet-runtime-deps-6.0.13-sles.12-x64.rpm /tmp/
#!RemoteAssetUrl: https://packages.microsoft.com/sles/15/prod/Packages/d/dotnet-runtime-6.0.13-x64.rpm
COPY dotnet-runtime-6.0.13-x64.rpm /tmp/

COPY prod.repo /tmp

# Workaround for https://github.com/openSUSE/obs-build/issues/487
RUN zypper --non-interactive install --no-recommends sles-release

# Importing MS GPG keys
RUN rpm --import /tmp/microsoft.asc

RUN zypper --non-interactive install --no-recommends libicu /tmp/*rpm

RUN cp /tmp/prod.repo /etc/zypp/repos.d/microsoft-dotnet-prod.repo

RUN zypper -n addlock dotnet-host

RUN rm -rf /tmp/* && zypper clean && rm -rf /var/log/*
