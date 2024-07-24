"""test registry for outdated/unexpected floating tags"""

from datetime import datetime, UTC, timedelta
import requests


def check_repositories(repositories: str) -> None:
    with requests.session() as session:
        for repository in repositories:
            print(f"Checking {repository}")
            regtoken: str = requests.get(
                "https://scc.suse.com/api/registry/authorize",
                params={
                    "scope": f"repository:{repository}:pull",
                    "service": "SUSE Linux Docker Registry",
                },
            ).json()["token"]
            session.headers.update(
                {
                    "Authorization": f"Bearer {regtoken}",
                    "Accept": "application/vnd.docker.distribution.manifest.v2+json,"
                    "application/vnd.docker.distribution.manifest.list.v2+json",
                }
            )
            response = session.get(
                f"https://registry.suse.com/v2/{repository}/manifests/latest"
            )
            response.raise_for_status()
            for manifest in response.json()["manifests"]:
                manifest_response: requests.Response = session.get(
                    f"https://registry.suse.com/v2/{repository}/manifests/{manifest['digest']}"
                )
                manifest_response.raise_for_status()
                config_digest: str = manifest_response.json()["config"]["digest"]
                config_response: requests.Response = session.get(
                    f"https://registry.suse.com/v2/{repository}/blobs/{config_digest}"
                )
                config_response.raise_for_status()
                config = config_response.json()["config"]

                if "Labels" in config:
                    for label in config["Labels"]:
                        if label.endswith(".created"):
                            parsed_datetime = datetime.fromisoformat(
                                config["Labels"][label]
                            )
                            if datetime.now(UTC) - parsed_datetime > timedelta(days=14):
                                print(label, parsed_datetime)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        "check registry content for outdated/unexpected floating tags"
    )

    parser.add_argument(
        "repository",
        type=str,
        nargs="+",
        help="The BCI container image to check for",
    )

    args = parser.parse_args()

    check_repositories(args.repository)
