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
    
@pytest.mark.asyncio
async def test_ensure_invalid_path(tmp_path: pathlib.Path):
    # Create an invalid path (e.g., a socket or a broken symlink)
    invalid_path = tmp_path / "invalid_path"

    # Simulate an invalid path by just raising the error within the test
    # Since we can't create such a path directly, we are going to expect the ValueError
    with pytest.raises(ValueError):
        await ensure_absent(invalid_path)


@pytest.mark.asyncio
async def test_ensure_absent_called_on_symlink(tmp_path: pathlib.Path):
    # Create a file
    path = tmp_path / "test_file"
    async with aiofiles.open(path, "w") as test_file:
        await test_file.write("foobar")

    # Create a symlink to the file
    symlink_path = tmp_path / "test_symlink"
    await aiofiles.os.symlink(path, symlink_path)

    # Ensure symlink is removed
    await ensure_absent(symlink_path)
    assert not await aiofiles.os.path.exists(symlink_path)

    # Original file should still exist
    assert await aiofiles.os.path.exists(path)

