import asyncio
import os
import pathlib
import tempfile
from dataclasses import dataclass
from dataclasses import field

import aiofiles.os
from bci_build.logger import LOGGER
from obs_package_update.util import RunCommand

#: environment variable name from which the osc username for the bot is read
OSC_USER_ENVVAR_NAME = "OSC_USER"

#: environment variable from which the password of the bot's user is taken
OSC_PASSWORD_ENVVAR_NAME = "OSC_PASSWORD"


async def ensure_absent(path: str | pathlib.Path) -> None:
    """Removes the file or directory with the given ``path`` if it exists or
    does nothing.

    Directories must be empty to be removed.

    Raises:
        :py:class:`ValueError`: if ``path`` is neither a file nor a directory

    """
    if await aiofiles.os.path.exists(path):
        if await aiofiles.os.path.isfile(path):
            await aiofiles.os.remove(path)
        elif await aiofiles.os.path.isdir(path):
            await aiofiles.os.rmdir(path)
        else:
            raise ValueError(f"{path} is neither a file nor a directory")


@dataclass
class OscRunner:
    #: username of the user that will be used to communicate with OBS.
    osc_username: str

    _osc_conf_file: str = ""

    _xdg_state_home_dir: tempfile.TemporaryDirectory | None = None

    _run_cmd: RunCommand = field(default_factory=lambda: RunCommand(logger=LOGGER))

    async def setup(self) -> None:
        if pw := os.getenv(OSC_PASSWORD_ENVVAR_NAME):
            osc_conf = tempfile.NamedTemporaryFile("w", delete=False)
            osc_conf.write(
                f"""[general]
apiurl = https://api.opensuse.org
[https://api.opensuse.org]
user = {self.osc_username}
pass = {pw}
aliases = obs
"""
            )
            osc_conf.flush()
            self._osc_conf_file = osc_conf.name

            self._xdg_state_home_dir = tempfile.TemporaryDirectory()
            self._run_cmd = RunCommand(
                logger=LOGGER, env={"XDG_STATE_HOME": self._xdg_state_home_dir.name}
            )

    @property
    def _osc(self) -> str:
        """command to invoke osc (may include a CLI flag for the custom config file)"""
        return (
            "osc" if not self._osc_conf_file else f"osc --config={self._osc_conf_file}"
        )

    async def run(self, osc_sub_command: str, **kwargs):
        """Run the provided sub command of osc asynchronously and return the
        result of that command.

        """
        return await self._run_cmd(f"{self._osc} {osc_sub_command}", **kwargs)

    async def teardown(self) -> None:
        if self._osc_conf_file:
            await aiofiles.os.remove(self._osc_conf_file)

            assert self._xdg_state_home_dir is not None

            tasks = []
            for suffix in ("", ".lock"):
                tasks.append(
                    ensure_absent(
                        os.path.join(
                            self._xdg_state_home_dir.name, "osc", f"cookiejar{suffix}"
                        )
                    )
                )
            await asyncio.gather(*tasks)
            await ensure_absent(os.path.join(self._xdg_state_home_dir.name, "osc"))
            self._xdg_state_home_dir.cleanup()
