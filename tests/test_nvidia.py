from unittest.mock import patch

import pytest

from bci_build.container_attributes import Arch
from bci_build.package.nvidia import NVIDIA_CONTAINERS
from bci_build.package.nvidia import _get_driver_branch
from bci_build.repomdparser import RpmPackage


def test_nvidia_dkms_presence():
    """Verify that dkms is present in the third party package list for all driver branches >= 575."""
    for container in NVIDIA_CONTAINERS:
        branch = _get_driver_branch(container.version)
        dkms_pkgs = [p for p in container.third_party_package_list if p.name == "dkms"]
        if branch >= 575:
            assert len(dkms_pkgs) == 1, (
                f"Expected dkms package for branch {branch} in container {container.name}"
            )
        else:
            assert len(dkms_pkgs) == 0, (
                f"Did not expect dkms package for branch {branch} in container {container.name}"
            )


@pytest.mark.parametrize(
    "driver_version,expected_closed",
    [
        ("595.71.05", "nvidia-driver-G07"),
        ("575.57.04", "nvidia-driver-G06"),
    ],
)
@patch("bci_build.package.nvidia.CUSTOM_END_TEMPLATE")
def test_nvidia_kmp_exclusion(mock_template, driver_version, expected_closed):
    """Verify that SLES KMP packages are excluded from the closed driver builder layer."""
    # Find a container with a matching driver branch
    branch = _get_driver_branch(driver_version)
    container = next(
        c for c in NVIDIA_CONTAINERS if _get_driver_branch(c.version) == branch
    )

    # Mock fetch_rpm_packages to return the closed driver package
    dummy_rpm = RpmPackage(
        name=expected_closed,
        arch="x86_64",
        evr=("", driver_version, "1.1"),
        filename=f"{expected_closed}-{driver_version}-1.1.x86_64.rpm",
        url=f"http://dummy/{expected_closed}-{driver_version}-1.1.x86_64.rpm",
    )

    # G06 uses dkms, G07 uses kmp
    is_g07 = branch >= 595
    kmp_rpm = RpmPackage(
        name="nvidia-open-driver-G07-signed-cuda-kmp-default",
        arch="x86_64",
        evr=("", f"{driver_version}_k6.4.0", "1.1"),
        filename=f"{expected_closed}-kmp-default-{driver_version}_k6.4.0-1.1.x86_64.rpm",
        url=f"http://dummy/{expected_closed}-kmp-default-{driver_version}_k6.4.0-1.1.x86_64.rpm",
    )

    with (
        patch.object(
            container, "fetch_rpm_packages", return_value=[dummy_rpm]
        ) as mock_fetch,
        patch(
            "bci_build.package.nvidia._get_nvidia_kmp_rpms",
            return_value=[kmp_rpm] if is_g07 else [],
        ) as mock_kmp,
        patch(
            "bci_build.package.nvidia._get_kernel_ga_rpms", return_value=[]
        ) as mock_kernel,
        patch.object(container, "prepare_extra_files"),
    ):
        # We also need to mock super(DevelopmentContainer, container).prepare_template()
        # so it doesn't try to build the whole Dockerfile which requires other side-effects.
        with patch("bci_build.package.DevelopmentContainer.prepare_template"):
            container.prepare_template()

            # Ensure expected mocks were called
            mock_fetch.assert_called_once()
            # G07 calls _get_nvidia_kmp_rpms twice (in _get_built_kernel_version and prepare_template)
            # G06 calls it once (only in prepare_template, since _get_built_kernel_version returns early)
            assert mock_kmp.call_count == 2 if is_g07 else 1
            mock_kernel.assert_called_once_with(
                container.os_version,
                container.kernel_variant,
                container.exclusive_arch,
                built_kernel="6.4.0" if is_g07 else None,
            )

            # Get the args passed to render
            mock_template.render.assert_called_once()
            render_kwargs = mock_template.render.call_args[1]

            get_closed_packages_for_arch = render_kwargs["get_closed_packages_for_arch"]
            get_open_packages_for_arch = render_kwargs["get_open_packages_for_arch"]

            # Evaluate get_closed_packages_for_arch on x86_64
            closed_packages = get_closed_packages_for_arch(Arch.X86_64)
            closed_pkg_names = [p.name for p in closed_packages]

            # The closed driver list should contain the expected closed driver
            assert expected_closed in closed_pkg_names

            # For G07, KMP packages should be excluded from closed
            if is_g07:
                assert (
                    "nvidia-open-driver-G07-signed-cuda-kmp-default"
                    not in closed_pkg_names
                )

            # Evaluate get_open_packages_for_arch on x86_64
            open_packages = get_open_packages_for_arch(Arch.X86_64)
            open_pkg_names = [p.name for p in open_packages]

            # For G07, closed driver should not be in open packages
            if is_g07:
                assert "nvidia-driver-G07" not in open_pkg_names

            # Evaluate get_justdb_packages_for_arch on x86_64
            get_justdb_packages_for_arch = render_kwargs["get_justdb_packages_for_arch"]
            justdb_packages = get_justdb_packages_for_arch(Arch.X86_64)
            justdb_pkg_names = [p.name for p in justdb_packages]

            # Closed driver should be registered via justdb
            assert expected_closed in justdb_pkg_names

            # For G07, KMP packages should also be registered via justdb
            if is_g07:
                assert (
                    "nvidia-open-driver-G07-signed-cuda-kmp-default" in justdb_pkg_names
                )


def test_get_nvidia_kmp_rpms():
    """Verify that _get_nvidia_kmp_rpms successfully returns RpmPackage objects without errors for SL16_0 and SP7."""
    from bci_build.os_version import OsVersion
    from bci_build.package.nvidia import _get_nvidia_kmp_rpms

    # Test SL16_0
    rpms_16 = _get_nvidia_kmp_rpms(
        "595.71.05", OsVersion.SL16_0, "default", [Arch.X86_64]
    )
    assert len(rpms_16) == 1
    assert rpms_16[0].name == "nvidia-open-driver-G07-signed-cuda-kmp-default"

    # Test SP7
    rpms_15 = _get_nvidia_kmp_rpms("595.71.05", OsVersion.SP7, "default", [Arch.X86_64])
    assert len(rpms_15) == 1
    assert rpms_15[0].name == "nvidia-open-driver-G07-signed-cuda-kmp-default"


def test_get_built_kernel_version():
    """Verify that _get_built_kernel_version returns correct kernel version or raises error appropriately."""
    from bci_build.os_version import OsVersion
    from bci_build.package.nvidia import _get_built_kernel_version

    # For an older driver branch < 595, it should return None
    assert (
        _get_built_kernel_version("550.163.01", OsVersion.SP7, "default", [Arch.X86_64])
        is None
    )

    # For a valid 595 driver, it should return the parsed kernel version
    # SP7: 595.71.05_k6.4.0_150700.53.40 -> kernel is 6.4.0-150700.53.40
    assert (
        _get_built_kernel_version("595.71.05", OsVersion.SP7, "default", [Arch.X86_64])
        == "6.4.0-150700.53.40"
    )

    # For an unsupported version, it should raise a ValueError
    with pytest.raises(ValueError):
        _get_built_kernel_version("595.99.99", OsVersion.SP7, "default", [Arch.X86_64])


def test_get_kernel_ga_rpms_sl16_0():
    """Verify that _get_kernel_ga_rpms correctly maps different kernel versions under SL16_0."""
    from bci_build.os_version import OsVersion
    from bci_build.package.nvidia import _get_kernel_ga_rpms

    # Test mapped built_kernel
    rpms_mapped = _get_kernel_ga_rpms(
        OsVersion.SL16_0, "default", [Arch.X86_64], built_kernel="6.12.0-160000.29"
    )
    assert len(rpms_mapped) > 0
    # Every returned RpmPackage should have the mapped patchinfo subdirectory in its URL
    expected_patchinfo = "patchinfo.20260501095726722273.187004354831441"
    for r in rpms_mapped:
        assert expected_patchinfo in r.url

    # Test unmapped built_kernel raises ValueError
    with pytest.raises(ValueError, match="Kernel patchinfo not found for built_kernel"):
        _get_kernel_ga_rpms(
            OsVersion.SL16_0, "default", [Arch.X86_64], built_kernel="6.12.0-160000.99"
        )

    # Test built_kernel=None uses the baseline patchinfo.ga
    rpms_ga = _get_kernel_ga_rpms(
        OsVersion.SL16_0, "default", [Arch.X86_64], built_kernel=None
    )
    assert len(rpms_ga) > 0
    for r in rpms_ga:
        assert "patchinfo.ga" in r.url
