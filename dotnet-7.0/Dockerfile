#!ExclusiveArch: x86_64
# SPDX-License-Identifier: MIT
#!BuildTag: bci/dotnet-sdk:7.0
#!BuildTag: bci/dotnet-sdk:7.0-%RELEASE%
#!BuildTag: bci/dotnet-sdk:7.0.3
#!BuildTag: bci/dotnet-sdk:7.0.3-%RELEASE%
#!BuildTag: bci/dotnet-sdk:latest
#!BuildVersion: 15.4.7.0
FROM suse/sle15:15.4

MAINTAINER SUSE LLC (https://www.suse.com/)

# Define labels according to https://en.opensuse.org/Building_derived_containers
# labelprefix=com.suse.bci.dotnet.sdk
LABEL org.opencontainers.image.title="SLE BCI .Net 7.0 SDK Container Image"
LABEL org.opencontainers.image.description="The .Net 7.0 SDK based on the SLE Base Container Image. The .NET packages contained in this image come from a 3rd-party repository http://packages.microsoft.com. You can find the respective source code in https://github.com/dotnet. SUSE doesn't provide any support or warranties."
LABEL org.opencontainers.image.version="7.0"
LABEL org.opencontainers.image.url="https://www.suse.com/products/server/"
LABEL org.opencontainers.image.created="%BUILDTIME%"
LABEL org.opencontainers.image.vendor="SUSE LLC"
LABEL org.opensuse.reference="registry.suse.com/bci/dotnet-sdk:7.0-%RELEASE%"
LABEL org.openbuildservice.disturl="%DISTURL%"
LABEL com.suse.supportlevel="techpreview"
LABEL com.suse.eula="sle-bci"
LABEL com.suse.lifecycle-url="https://www.suse.com/lifecycle"
LABEL com.suse.image-type="sle-bci"
LABEL com.suse.release-stage="released"
# endlabelprefix


# telemetry opt out: https://docs.microsoft.com/en-us/dotnet/core/tools/telemetry#how-to-opt-out
ENV DOTNET_CLI_TELEMETRY_OPTOUT=1

# The MS GPG keys
COPY microsoft.asc /tmp

RUN mkdir -p /tmp/

#!RemoteAssetUrl: https://packages.microsoft.com/sles/15/prod/dotnet-host-7.0.3-x64.rpm
COPY dotnet-host-7.0.3-x64.rpm /tmp/
#!RemoteAssetUrl: https://packages.microsoft.com/sles/15/prod/netstandard-targeting-pack-2.1.0-x64.rpm
COPY netstandard-targeting-pack-2.1.0-x64.rpm /tmp/
#!RemoteAssetUrl: https://packages.microsoft.com/sles/15/prod/dotnet-targeting-pack-7.0.3-x64.rpm
COPY dotnet-targeting-pack-7.0.3-x64.rpm /tmp/
#!RemoteAssetUrl: https://packages.microsoft.com/sles/15/prod/dotnet-hostfxr-7.0.3-x64.rpm
COPY dotnet-hostfxr-7.0.3-x64.rpm /tmp/
#!RemoteAssetUrl: https://packages.microsoft.com/sles/15/prod/dotnet-runtime-deps-7.0.3-sles.12-x64.rpm
COPY dotnet-runtime-deps-7.0.3-sles.12-x64.rpm /tmp/
#!RemoteAssetUrl: https://packages.microsoft.com/sles/15/prod/dotnet-runtime-7.0.3-x64.rpm
COPY dotnet-runtime-7.0.3-x64.rpm /tmp/
#!RemoteAssetUrl: https://packages.microsoft.com/sles/15/prod/dotnet-apphost-pack-7.0.3-x64.rpm
COPY dotnet-apphost-pack-7.0.3-x64.rpm /tmp/
#!RemoteAssetUrl: https://packages.microsoft.com/sles/15/prod/aspnetcore-targeting-pack-7.0.3-x64.rpm
COPY aspnetcore-targeting-pack-7.0.3-x64.rpm /tmp/
#!RemoteAssetUrl: https://packages.microsoft.com/sles/15/prod/aspnetcore-runtime-7.0.3-x64.rpm
COPY aspnetcore-runtime-7.0.3-x64.rpm /tmp/
#!RemoteAssetUrl: https://packages.microsoft.com/sles/15/prod/dotnet-sdk-7.0.201-x64.rpm
COPY dotnet-sdk-7.0.201-x64.rpm /tmp/

COPY prod.repo /tmp

# Workaround for https://github.com/openSUSE/obs-build/issues/487
RUN zypper --non-interactive install --no-recommends sles-release

# Importing MS GPG keys
RUN rpm --import /tmp/microsoft.asc

RUN zypper --non-interactive install --no-recommends libicu /tmp/*rpm

RUN cp /tmp/prod.repo /etc/zypp/repos.d/microsoft-dotnet-prod.repo

RUN zypper -n addlock dotnet-host

RUN rm -rf /tmp/* && zypper clean && rm -rf /var/log/*
