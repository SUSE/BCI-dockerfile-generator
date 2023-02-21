def get_obs_project_url(
    project_name: str, base_url: str = "https://build.opensuse.org/"
) -> str:
    """Returns the url of the project with the given name."""
    base = base_url if base_url[-1] != "/" else base_url[:-1]
    return f"{base}/project/show/{project_name}"
