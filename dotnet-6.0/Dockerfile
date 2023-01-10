#!ExclusiveArch: x86_64
# SPDX-License-Identifier: MIT
#!BuildTag: bci/dotnet-sdk:6.0
#!BuildTag: bci/dotnet-sdk:6.0-%RELEASE%
#!BuildTag: bci/dotnet-sdk:6.0.12
#!BuildTag: bci/dotnet-sdk:6.0.12-%RELEASE%
#!BuildVersion: 15.4.6.0
FROM suse/sle15:15.4

MAINTAINER SUSE LLC (https://www.suse.com/)

# Define labels according to https://en.opensuse.org/Building_derived_containers
# labelprefix=com.suse.bci.dotnet.sdk
LABEL org.opencontainers.image.title="SLE BCI .Net 6.0 SDK Container Image"
LABEL org.opencontainers.image.description="The .Net 6.0 SDK based on the SLE Base Container Image. The .NET packages contained in this image come from a 3rd-party repository http://packages.microsoft.com. You can find the respective source code in https://github.com/dotnet. SUSE doesn't provide any support or warranties."
LABEL org.opencontainers.image.version="6.0"
LABEL org.opencontainers.image.url="https://www.suse.com/products/server/"
LABEL org.opencontainers.image.created="%BUILDTIME%"
LABEL org.opencontainers.image.vendor="SUSE LLC"
LABEL org.opensuse.reference="registry.suse.com/bci/dotnet-sdk:6.0-%RELEASE%"
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

RUN mkdir -p /tmp/x86_64

#!RemoteAssetUrl: https://packages.microsoft.com/sles/15/prod/dotnet-host-6.0.13-x64.rpm
COPY dotnet-host-6.0.13-x64.rpm /tmp/x86_64
#!RemoteAssetUrl: https://packages.microsoft.com/sles/15/prod/netstandard-targeting-pack-2.1.0-x64.rpm
COPY netstandard-targeting-pack-2.1.0-x64.rpm /tmp/x86_64
#!RemoteAssetUrl: https://packages.microsoft.com/sles/15/prod/dotnet-targeting-pack-6.0.13-x64.rpm
COPY dotnet-targeting-pack-6.0.13-x64.rpm /tmp/x86_64
#!RemoteAssetUrl: https://packages.microsoft.com/sles/15/prod/dotnet-hostfxr-6.0.13-x64.rpm
COPY dotnet-hostfxr-6.0.13-x64.rpm /tmp/x86_64
#!RemoteAssetUrl: https://packages.microsoft.com/sles/15/prod/dotnet-runtime-deps-6.0.13-sles.12-x64.rpm
COPY dotnet-runtime-deps-6.0.13-sles.12-x64.rpm /tmp/x86_64
#!RemoteAssetUrl: https://packages.microsoft.com/sles/15/prod/dotnet-runtime-6.0.12-x64.rpm
COPY dotnet-runtime-6.0.12-x64.rpm /tmp/x86_64
#!RemoteAssetUrl: https://packages.microsoft.com/sles/15/prod/dotnet-apphost-pack-6.0.13-x64.rpm
COPY dotnet-apphost-pack-6.0.13-x64.rpm /tmp/x86_64
#!RemoteAssetUrl: https://packages.microsoft.com/sles/15/prod/aspnetcore-targeting-pack-6.0.13-x64.rpm
COPY aspnetcore-targeting-pack-6.0.13-x64.rpm /tmp/x86_64
#!RemoteAssetUrl: https://packages.microsoft.com/sles/15/prod/aspnetcore-runtime-6.0.12-x64.rpm
COPY aspnetcore-runtime-6.0.12-x64.rpm /tmp/x86_64
#!RemoteAssetUrl: https://packages.microsoft.com/sles/15/prod/dotnet-sdk-6.0.404-x64.rpm
COPY dotnet-sdk-6.0.404-x64.rpm /tmp/x86_64

COPY prod.repo /tmp

# Workaround for https://github.com/openSUSE/obs-build/issues/487
RUN zypper --non-interactive install --no-recommends sles-release

# Importing MS GPG keys
RUN rpm --import /tmp/microsoft.asc

# Use the package for ICU offered by SLES

#!ArchExclusiveLine x86_64
RUN if [ $(uname -m) = "x86_64" ]; then zypper --non-interactive install --no-recommends libicu69; fi


RUN zypper --non-interactive install --no-recommends /tmp/$(uname -m)/*rpm

RUN cp /tmp/prod.repo /etc/zypp/repos.d/microsoft-dotnet-prod.repo

RUN zypper -n addlock dotnet-host

RUN rm -rf /tmp/* && zypper clean && rm -rf /var/log/*
