import pytest
from staging.build_result import Arch
from staging.build_result import is_build_failed
from staging.build_result import PackageBuildResult
from staging.build_result import PackageStatusCode
from staging.build_result import render_as_markdown
from staging.build_result import RepositoryBuildResult


def test_from_resultlist():
    obs_api_reply = """<resultlist state="10c966b3d96474d1d59d0ba6d4d5b61a">
  <result project="home:defolos:BCI:Staging:SLE-15-SP3:sle15-sp3-NBdNL" repository="images" arch="x86_64" code="building" state="building" dirty="true">
    <status package="golang-1.18" code="building">
      <details>building on old-cirrus2:14</details>
    </status>
    <status package="init" code="finished">
      <details>succeeded</details>
    </status>
    <status package="openjdk-11-devel" code="finished">
      <details>succeeded</details>
    </status>
    <status package="python-3.9" code="finished">
      <details>succeeded</details>
    </status>
    <status package="micro" code="scheduled"/>
  </result>
  <result project="home:defolos:BCI:Staging:SLE-15-SP3:sle15-sp3-NBdNL" repository="images" arch="aarch64" code="building" state="building">
    <status package="openjdk-11" code="succeeded"/>
    <status package="openjdk-11-devel" code="building">
      <details>building on obs-arm-10:29</details>
    </status>
    <status package="python-3.6" code="succeeded"/>
    <status package="python-3.9" code="signing"/>
  </result>
  <result project="home:defolos:BCI:Staging:SLE-15-SP3:sle15-sp3-NBdNL" repository="containerfile" arch="x86_64" code="published" state="published" dirty="true">
    <status package="openjdk-11" code="excluded"/>
    <status package="openjdk-11-devel" code="excluded"/>
  </result>
  <result project="home:defolos:BCI:Staging:SLE-15-SP3:sle15-sp3-NBdNL" repository="containerfile" arch="aarch64" code="published" state="published">
  </result>
</resultlist>

"""
    assert RepositoryBuildResult.from_resultlist(obs_api_reply) == [
        RepositoryBuildResult(
            project="home:defolos:BCI:Staging:SLE-15-SP3:sle15-sp3-NBdNL",
            repository="images",
            arch=Arch.X86_64,
            code="building",
            state="building",
            dirty=True,
            packages=[
                PackageBuildResult(
                    name="golang-1.18",
                    code=PackageStatusCode.BUILDING,
                    detail_message="building on old-cirrus2:14",
                ),
                PackageBuildResult(
                    name="init",
                    code=PackageStatusCode.FINISHED,
                    detail_message="succeeded",
                ),
                PackageBuildResult(
                    name="openjdk-11-devel",
                    code=PackageStatusCode.FINISHED,
                    detail_message="succeeded",
                ),
                PackageBuildResult(
                    name="python-3.9",
                    code=PackageStatusCode.FINISHED,
                    detail_message="succeeded",
                ),
                PackageBuildResult(name="micro", code=PackageStatusCode.SCHEDULED),
            ],
        ),
        RepositoryBuildResult(
            project="home:defolos:BCI:Staging:SLE-15-SP3:sle15-sp3-NBdNL",
            repository="images",
            arch=Arch.AARCH64,
            code="building",
            state="building",
            packages=[
                PackageBuildResult(name="openjdk-11", code=PackageStatusCode.SUCCEEDED),
                PackageBuildResult(
                    name="openjdk-11-devel",
                    code=PackageStatusCode.BUILDING,
                    detail_message="building on obs-arm-10:29",
                ),
                PackageBuildResult(
                    name="python-3.6",
                    code=PackageStatusCode.SUCCEEDED,
                ),
                PackageBuildResult(
                    name="python-3.9",
                    code=PackageStatusCode.SIGNING,
                ),
            ],
        ),
        RepositoryBuildResult(
            project="home:defolos:BCI:Staging:SLE-15-SP3:sle15-sp3-NBdNL",
            repository="containerfile",
            arch=Arch.X86_64,
            code="published",
            state="published",
            dirty=True,
            packages=[
                PackageBuildResult(name="openjdk-11", code=PackageStatusCode.EXCLUDED),
                PackageBuildResult(
                    name="openjdk-11-devel",
                    code=PackageStatusCode.EXCLUDED,
                ),
            ],
        ),
        RepositoryBuildResult(
            project="home:defolos:BCI:Staging:SLE-15-SP3:sle15-sp3-NBdNL",
            repository="containerfile",
            arch=Arch.AARCH64,
            code="published",
            state="published",
        ),
    ]


def test_is_build_failed_dirty_repo():
    with pytest.raises(ValueError) as val_err_ctx:
        is_build_failed(
            [
                RepositoryBuildResult(
                    project="home:defolos:BCI:Staging:SLE-15-SP3:sle15-sp3-NBdNL",
                    repository="containerfile",
                    arch=Arch.AARCH64,
                    code="published",
                    state="published",
                    dirty=True,
                )
            ]
        )

    assert "must not be dirty" in str(val_err_ctx)


@pytest.mark.parametrize(
    "build_res,is_failed",
    [
        (
            [
                RepositoryBuildResult(
                    project="home:defolos:BCI:Staging:SLE-15-SP3:sle15-sp3-NBdNL",
                    repository="containerfile",
                    arch=Arch.AARCH64,
                    code="published",
                    state="published",
                    packages=[
                        PackageBuildResult(
                            name="init", code=PackageStatusCode.UNRESOLVABLE
                        )
                    ],
                )
            ],
            True,
        ),
        (
            [
                RepositoryBuildResult(
                    project="home:defolos:BCI:Staging:SLE-15-SP3:sle15-sp3-NBdNL",
                    repository="containerfile",
                    arch=Arch.AARCH64,
                    code="published",
                    state="published",
                    packages=[
                        PackageBuildResult(name="init", code=PackageStatusCode.FAILED)
                    ],
                )
            ],
            True,
        ),
        (
            [
                RepositoryBuildResult(
                    project="home:defolos:BCI:Staging:SLE-15-SP3:sle15-sp3-NBdNL",
                    repository="containerfile",
                    arch=Arch.AARCH64,
                    code="published",
                    state="published",
                    packages=[
                        PackageBuildResult(
                            name="init", code=PackageStatusCode.SUCCEEDED
                        ),
                        PackageBuildResult(
                            name="micro", code=PackageStatusCode.EXCLUDED
                        ),
                    ],
                )
            ],
            False,
        ),
    ],
)
def test_is_build_failed(build_res: list[RepositoryBuildResult], is_failed: bool):
    assert is_build_failed(build_res) == is_failed


@pytest.mark.parametrize(
    "build_res,table_markdown",
    [
        (
            [
                RepositoryBuildResult(
                    project="home:defolos:BCI:Staging:SLE-15-SP3:sle15-sp3-NBdNL",
                    repository="containerfile",
                    arch=Arch.AARCH64,
                    code="published",
                    state="published",
                    packages=[
                        PackageBuildResult(
                            name="init", code=PackageStatusCode.SUCCEEDED
                        ),
                        PackageBuildResult(
                            name="micro", code=PackageStatusCode.EXCLUDED
                        ),
                    ],
                )
            ],
            """
Build succeeded ✅
Repository `containerfile` in [home:defolos:BCI:Staging:SLE-15-SP3:sle15-sp3-NBdNL](https://build.opensuse.org/project/show/home:defolos:BCI:Staging:SLE-15-SP3:sle15-sp3-NBdNL) for `aarch64`: current state: published
Build results:
package name | status | build log
-------------|--------|----------
init | ✅ succeeded | [live log](https://build.opensuse.org/package/live_build_log/home:defolos:BCI:Staging:SLE-15-SP3:sle15-sp3-NBdNL/init/containerfile/aarch64)
micro | ⛔ excluded | [live log](https://build.opensuse.org/package/live_build_log/home:defolos:BCI:Staging:SLE-15-SP3:sle15-sp3-NBdNL/micro/containerfile/aarch64)


Build succeeded ✅
""",
        ),
        (
            [
                RepositoryBuildResult(
                    project="home:defolos:BCI:Staging:SLE-15-SP3:sle15-sp3-NBdNL",
                    repository="containerfile",
                    arch=Arch.AARCH64,
                    code="published",
                    state="building",
                    dirty=True,
                    packages=[
                        PackageBuildResult(name="init", code=PackageStatusCode.FAILED),
                        PackageBuildResult(
                            name="micro",
                            code=PackageStatusCode.UNRESOLVABLE,
                            detail_message="Nothing provides gcc",
                        ),
                    ],
                )
            ],
            """
Still building 🛻
Repository `containerfile` in [home:defolos:BCI:Staging:SLE-15-SP3:sle15-sp3-NBdNL](https://build.opensuse.org/project/show/home:defolos:BCI:Staging:SLE-15-SP3:sle15-sp3-NBdNL) for `aarch64`: current state: building (repository is **dirty**)
Build results:
package name | status | detail | build log
-------------|--------|--------|----------
init | ❌ failed | | [live log](https://build.opensuse.org/package/live_build_log/home:defolos:BCI:Staging:SLE-15-SP3:sle15-sp3-NBdNL/init/containerfile/aarch64)
micro | 🚫 unresolvable | Nothing provides gcc | [live log](https://build.opensuse.org/package/live_build_log/home:defolos:BCI:Staging:SLE-15-SP3:sle15-sp3-NBdNL/micro/containerfile/aarch64)


Still building 🛻
""",
        ),
        (
            [
                RepositoryBuildResult(
                    project="home:defolos:BCI:Staging:SLE-15-SP3:sle15-sp3-NBdNL",
                    repository="containerfile",
                    arch=Arch.AARCH64,
                    code="published",
                    state="published",
                    packages=[
                        PackageBuildResult(name="init", code=PackageStatusCode.FAILED),
                        PackageBuildResult(
                            name="micro",
                            code=PackageStatusCode.UNRESOLVABLE,
                            detail_message="Nothing provides rust",
                        ),
                    ],
                )
            ],
            """
Build failed ❌
Repository `containerfile` in [home:defolos:BCI:Staging:SLE-15-SP3:sle15-sp3-NBdNL](https://build.opensuse.org/project/show/home:defolos:BCI:Staging:SLE-15-SP3:sle15-sp3-NBdNL) for `aarch64`: current state: published
Build results:
package name | status | detail | build log
-------------|--------|--------|----------
init | ❌ failed | | [live log](https://build.opensuse.org/package/live_build_log/home:defolos:BCI:Staging:SLE-15-SP3:sle15-sp3-NBdNL/init/containerfile/aarch64)
micro | 🚫 unresolvable | Nothing provides rust | [live log](https://build.opensuse.org/package/live_build_log/home:defolos:BCI:Staging:SLE-15-SP3:sle15-sp3-NBdNL/micro/containerfile/aarch64)


Build failed ❌
""",
        ),
    ],
)
def test_render_as_markdown(
    build_res: list[RepositoryBuildResult], table_markdown: str
):
    assert render_as_markdown(build_res) == table_markdown
