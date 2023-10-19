"""Helper functions for the package build generation."""
from bci_build.package.bciclasses import OsVersion


def build_tag_prefix(os_version: OsVersion) -> str:
    if os_version == OsVersion.TUMBLEWEED:
        return "opensuse/bci"
    if os_version == OsVersion.BASALT:
        return "alp/bci"
    if os_version == OsVersion.SP3:
        return "suse/ltss/sle15.3"
    return "bci"


def generate_disk_size_constraints(size_gb: int) -> str:
    """Creates the contents of a :file:`_constraints` file for OBS to require
    workers with at least ``size_gb`` GB of disk space.

    """
    return f"""<constraints>
  <hardware>
    <disk>
      <size unit="G">{size_gb}</size>
    </disk>
  </hardware>
</constraints>
"""
