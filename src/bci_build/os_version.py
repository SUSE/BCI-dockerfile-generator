"""Abstraction for Operating System Version differences."""

import datetime
import enum


@enum.unique
class OsVersion(enum.Enum):
    """Enumeration of the base operating system versions for BCI."""

    #: SLE 15 Service Pack 7
    SP7 = 7
    #: SLE 15 Service Pack 6
    SP6 = 6
    #: SLE 15 Service Pack 5
    SP5 = 5
    #: SLE 15 Service Pack 4
    SP4 = 4
    #: SLE 15 Service Pack 3
    SP3 = 3
    #: SUSE Linux Framework One
    SLE16_0 = "16.0"
    #: openSUSE Tumbleweed
    TUMBLEWEED = "Tumbleweed"

    @staticmethod
    def parse(val: str):
        try:
            return OsVersion(int(val))
        except ValueError:
            return OsVersion(val)

    def __str__(self) -> str:
        return str(self.value)

    @property
    def pretty_print(self) -> str:
        if self.value in (OsVersion.TUMBLEWEED.value, OsVersion.SLE16_0.value):
            return self.value
        return f"SP{self.value}"

    @property
    def pretty_os_version_no_dash(self) -> str:
        if self.value == OsVersion.TUMBLEWEED.value:
            # TW has no version by itself and the "openSUSE Tumbleweed" is
            # already part of the base identifier
            return ""
        if self.is_slfo:
            return "16"

        return f"15 SP{self.value}"

    @property
    def distribution_base_name(self) -> str:
        if self.is_tumbleweed:
            return "openSUSE Tumbleweed"
        elif self.is_ltss:
            return "SLE LTSS"
        elif self.is_sle15 or self.is_slfo:
            return "SLE"

        raise NotImplementedError(f"Unknown os_version: {self.value}")

    @property
    def full_os_name(self) -> str:
        if self.is_tumbleweed:
            return self.distribution_base_name

        return f"{self.distribution_base_name} {self.pretty_os_version_no_dash}"

    @property
    def deployment_branch_name(self) -> str:
        if self.is_tumbleweed or self.is_slfo:
            return str(self.value)
        if self.is_sle15:
            return f"sle15-sp{self.value}"
        raise NotImplementedError("unhandled version {self.value}")

    @property
    def lifecycle_data_pkg(self) -> list[str]:
        if self.is_sle15:
            return ["lifecycle-data-sle-module-development-tools"]
        return []

    @property
    def common_devel_packages(self) -> list[str]:
        """Returns a list of common development packages that are needed for
        all development containers"""
        r = set(("findutils", "gawk", "git-core", "curl", "procps"))
        if self.is_tumbleweed or self.is_slfo:
            r.add("util-linux")

        return sorted(list(r))

    @property
    def is_sle15(self) -> bool:
        return self.value in (
            OsVersion.SP3.value,
            OsVersion.SP4.value,
            OsVersion.SP5.value,
            OsVersion.SP6.value,
            OsVersion.SP7.value,
        )

    @property
    def is_slfo(self) -> bool:
        return self.value in (OsVersion.SLE16_0.value,)

    @property
    def is_tumbleweed(self) -> bool:
        return self.value == OsVersion.TUMBLEWEED.value

    @property
    def is_ltss(self) -> bool:
        return self in ALL_OS_LTSS_VERSIONS

    @property
    def os_version(self) -> str:
        """Returns the numeric version of :py:class:`OsContainer` (or
        ``latest``).

        """
        if self.is_sle15:
            return f"15.{str(self.value)}"
        if self.value == OsVersion.SLE16_0.value:
            return "16.0"
        # Tumbleweed rolls too fast, just use latest
        return "latest"

    @property
    def has_container_suseconnect(self) -> bool:
        return self.is_sle15 or self.is_slfo

    @property
    def eula_package_names(self) -> tuple[str, ...]:
        if self.is_sle15:
            return ("skelcd-EULA-bci",)
        # TODO: switch to skelcd-EULA-bci when SLES 16 is released
        if self.value == OsVersion.SLE16_0.value:
            return ("skelcd-EULA-SLES",)
        return ()

    @property
    def release_package_names(self) -> tuple[str, ...]:
        if self.value == OsVersion.TUMBLEWEED.value:
            return ("openSUSE-release", "openSUSE-release-appliance-docker")
        if self.value == OsVersion.SLE16_0.value:
            return ("SLES-release",)
        if self.is_ltss:
            return ("sles-ltss-release",)

        assert self.is_sle15
        return ("sles-release",)


#: Operating system versions that have the label ``com.suse.release-stage`` set
#: to ``released``.
RELEASED_OS_VERSIONS: list[OsVersion] = [
    OsVersion.SP3,
    OsVersion.SP4,
    OsVersion.SP5,
    OsVersion.SP6,
    OsVersion.TUMBLEWEED,
]

# For which versions to create Application and Language Containers?
ALL_NONBASE_OS_VERSIONS: list[OsVersion] = [
    OsVersion.SP6,
    OsVersion.SP7,
    OsVersion.TUMBLEWEED,
]

# For which versions to create Base Container Images?
ALL_BASE_OS_VERSIONS: list[OsVersion] = [
    OsVersion.SP6,
    OsVersion.SP7,
    OsVersion.TUMBLEWEED,
    OsVersion.SLE16_0,
]

# List of SPs that are already under LTSS
ALL_OS_LTSS_VERSIONS: list[OsVersion] = [OsVersion.SP3, OsVersion.SP4]

# joint set of BASE and NON_BASE versions
ALL_OS_VERSIONS: set[OsVersion] = {
    v for v in (*ALL_BASE_OS_VERSIONS, *ALL_NONBASE_OS_VERSIONS)
}

CAN_BE_LATEST_OS_VERSION: list[OsVersion] = [
    OsVersion.SP6,
    OsVersion.TUMBLEWEED,
]


# End of General Support Dates
_SUPPORTED_UNTIL_SLE: dict[OsVersion, datetime.date | None] = {
    OsVersion.SP4: datetime.date(2023, 12, 31),
    OsVersion.SP5: datetime.date(2024, 12, 31),
    OsVersion.SP6: datetime.date(2025, 12, 31),
    OsVersion.SP7: datetime.date(2031, 7, 31),
}
