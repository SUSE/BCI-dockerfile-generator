import pathlib
import os
import aiofiles.os
import pytest

from staging.util import ensure_absent


@pytest.mark.asyncio
async def test_ensure_file_absent(tmp_path: pathlib.Path):
    path = tmp_path / "test_file"
    async with aiofiles.open(path, "w") as test_file:
        await test_file.write("foobar")

    await ensure_absent(path)
    assert not await aiofiles.os.path.exists(path)


@pytest.mark.asyncio
async def test_ensure_non_existent_file_absent(tmp_path: pathlib.Path):
    path = tmp_path / "test_file"
    assert not await aiofiles.os.path.exists(path)

    await ensure_absent(path)


@pytest.mark.asyncio
async def test_ensure_directory_absent(tmp_path: pathlib.Path):
    path = tmp_path / "test_dir"
    await aiofiles.os.mkdir(path)

    await ensure_absent(path)
    assert not await aiofiles.os.path.exists(path)


@pytest.mark.asyncio
async def test_ensure_absent_on_directory_without_write_permissions(
    tmp_path: pathlib.Path,
):
    # Create a directory
    path = tmp_path / "test_dir"
    await aiofiles.os.mkdir(path)

    # Change permissions to remove write access (read and execute only)
    os.chmod(path, 0o500)

    # Try to remove the directory - should raise a PermissionError or OSError
    with pytest.raises((PermissionError, OSError)):
        await ensure_absent(path)

    # Clean up by restoring write permissions to allow removal after test
    os.chmod(path, 0o700)
    await ensure_absent(path)

    # Ensure the directory was successfully cleaned up
    assert not await aiofiles.os.path.exists(path)
