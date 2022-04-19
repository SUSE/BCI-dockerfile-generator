"""This module contains general purpose utility functions"""
from asyncio import create_subprocess_shell
import asyncio
from logging import Logger
from typing import Optional


async def run_cmd(
    cmd: str, logger: Optional[Logger] = None, cwd: Optional[str] = None
) -> str:
    """Runs the shell command ``cmd`` asynchronously and returns its standard
    output.

    """
    if logger:
        logger.debug("Running command %s", cmd)
    p = await create_subprocess_shell(
        cmd,
        stderr=asyncio.subprocess.STDOUT,
        stdout=asyncio.subprocess.PIPE,
        cwd=cwd,
    )
    retcode = await p.wait()
    stdout, _ = await p.communicate()
    if retcode != 0:
        raise RuntimeError(
            f"Command {cmd} failed (exit code {retcode}) with: {stdout.decode()}"
        )
    return stdout.decode()
