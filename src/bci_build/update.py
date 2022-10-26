#!/usr/bin/env python3
import asyncio
from dataclasses import dataclass, field
import logging
from typing import List, Literal, Optional

from bci_build.package import (
    ALL_CONTAINER_IMAGE_NAMES,
    ALL_OS_VERSIONS,
    SORTED_CONTAINER_IMAGE_NAMES,
    BaseContainerImage,
    OsVersion,
)
from obs_package_update import Updater, Package


LOGGER = logging.getLogger(__name__)

OBS_TARGET_T = Literal["obs", "ibs"]


@dataclass
class BciUpdater(Updater):
    bci: BaseContainerImage = field(default=None)

    async def add_files(self, destination: str) -> List[str]:
        return await self.bci.write_files_to_folder(destination)


def get_bci_project_name(
    os_version: OsVersion, build_service_target: OBS_TARGET_T = "obs"
) -> str:
    prj_suffix = (
        os_version
        if os_version == OsVersion.TUMBLEWEED
        else "SLE-15-SP" + str(os_version)
    )
    if build_service_target == "obs":
        return f"devel:BCI:{prj_suffix}"
    else:
        if os_version == OsVersion.TUMBLEWEED:
            raise ValueError("A container image for Tumbleweed is not mirrored to IBS")
        return f"SUSE:{prj_suffix}:Update:BCI"


async def update_package(
    bci: BaseContainerImage,
    commit_msg: str,
    target_prj: Optional[str] = None,
    cleanup_on_error: bool = False,
    submit_package: bool = True,
    cleanup_on_no_change: bool = True,
    build_service_target: Literal["obs", "ibs"] = "obs",
) -> None:
    """Update the package of this BCI image on OBS or IBS (which one is chosen
    depends on the parameter ``build_service_target``, with the default being
    OBS):

    1. if ``target_pkg`` is ``None``, branch the image package, optionally
       into the supplied ``target_prj``
    2. checkout the branched package or ``target_pkg``
    3. render the build recipe files from the ``bci`` Container Image
    4. update the changelog, commit the changes and create a submitrequest
       (the SR is only created when ``submit_package`` is ``True``) if any
       changes were made.

    If ``cleanup_on_error`` is ``True``, then perform a :command:`osc
    rdelete` of the branched package or ``target_pkg`` if an error occurred
    during the update.

    """
    assert build_service_target in (
        "obs",
        "ibs",
    ), f"got an invalid {build_service_target=}, expected 'obs' or 'ibs'"

    src_prj = get_bci_project_name(bci, build_service_target)

    updater = BciUpdater(bci=bci, logger=LOGGER)

    if build_service_target == "obs":
        updater.api_url = "https://api.opensuse.org"
    else:
        if bci.os_version == OsVersion.TUMBLEWEED:
            raise ValueError("A container image for Tumbleweed is not mirrored to IBS")
        updater.api_url = "https://api.suse.de"

    source_package = Package(project=src_prj, package=bci.package_name)
    await updater.update_package(
        source_package=source_package,
        commit_msg=commit_msg,
        target_project=target_prj,
        cleanup_on_error=cleanup_on_error,
        submit_package=submit_package,
        cleanup_on_no_change=cleanup_on_no_change,
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        "Update the SLE BCI image description on OBS or IBS"
    )

    parser.add_argument(
        "--images",
        type=str,
        nargs="*",
        choices=SORTED_CONTAINER_IMAGE_NAMES,
        help="The BCI container image that should be updated. This option is mutually exclusive with --service-pack.",
    )
    parser.add_argument(
        "--service-pack",
        type=str,
        choices=[str(v) for v in ALL_OS_VERSIONS],
        nargs=1,
        help="Do not update a single image, instead update all images of a single service pack. This option is mutually exclusive with supplying image names.",
    )
    parser.add_argument(
        "--commit-msg",
        type=str,
        nargs=1,
        default=[None],
        help="Required commit message that will be added to the changelog, as the commit message and for the submit request.",
    )

    parser.add_argument(
        "--cleanup-on-error",
        action="store_true",
        help="Delete the branched or target package if an error occurred during the update process",
    )
    parser.add_argument(
        "--no-cleanup-on-no-change",
        action="store_true",
        help="Don't remove the branched package when nothing changed",
    )
    parser.add_argument(
        "--no-sr",
        action="store_true",
        help="Don't send a submitrequest after the package has been updated",
    )
    parser.add_argument(
        "--target-prj",
        type=str,
        nargs="?",
        default=None,
        help="Don't branch into the default project, use the supplied one instead.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        help="Set the verbosity of the logger to stderr",
    )
    parser.add_argument(
        "--build-service-target",
        type=str,
        nargs=1,
        default=["obs"],
        choices=["obs", "ibs"],
        help="Specify whether the updater should target obs (build.opensuse.org) or ibs (build.suse.de)",
    )

    args = parser.parse_args()

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(fmt="%(levelname)s: %(message)s"))
    LOGGER.addHandler(handler)

    if args.images and args.service_pack:
        raise ValueError(
            "Cannot set the service pack and specific images at the same time"
        )

    commit_msg = args.commit_msg[0]
    if commit_msg is None:
        raise ValueError("A commit message must be provided")

    if args.verbose > 0:
        LOGGER.setLevel((3 - min(args.verbose, 2)) * 10)
    else:
        LOGGER.setLevel("ERROR")

    if not args.images and not args.service_pack:
        raise ValueError(
            "No images supplied and no service pack set, nothing to update"
        )

    loop = asyncio.get_event_loop()
    images: List[str] = (
        args.images
        if args.images
        else [
            k
            for k, v in ALL_CONTAINER_IMAGE_NAMES.items()
            if str(v.os_version) == args.service_pack[0]
        ]
    )

    for img in images:
        loop.run_until_complete(
            update_package(
                ALL_CONTAINER_IMAGE_NAMES[img],
                commit_msg=commit_msg,
                target_prj=args.target_prj,
                cleanup_on_error=args.cleanup_on_error,
                submit_package=not args.no_sr,
                cleanup_on_no_change=not args.no_cleanup_on_no_change,
                build_service_target=args.build_service_target[0],
            )
        )
