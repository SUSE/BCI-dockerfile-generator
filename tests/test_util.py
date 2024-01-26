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
