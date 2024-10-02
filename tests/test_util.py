import pathlib

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
async def test_ensure_file_absent_when_open_for_reading(tmp_path: pathlib.Path):
    path = tmp_path / "test_file"
    async with aiofiles.open(path, "w") as test_file:
        await test_file.write("foobar")

    # Open the file for reading
    async with aiofiles.open(path, "r"):
        pass  # Simply open and close the file

    # Ensure the file is removed
    await ensure_absent(path)
    assert not await aiofiles.os.path.exists(path)


@pytest.mark.asyncio
async def test_ensure_non_empty_directory_absent(tmp_path: pathlib.Path):
    # Create a directory
    path = tmp_path / "test_dir"
    await aiofiles.os.mkdir(path)

    # Create a file inside the directory
    file_in_dir = path / "file_inside"
    async with aiofiles.open(file_in_dir, "w") as f:
        await f.write("This is a test file inside the directory")

    # Try to remove the non-empty directory
    with pytest.raises(OSError):
        await ensure_absent(path)

    # The directory should still exist since it was not removed
    assert await aiofiles.os.path.exists(path)
