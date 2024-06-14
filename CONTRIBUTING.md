# Contributing to the BCI-dockerfile-generator

##  Opening an pull request

The BCI-dockerfile-generator documentation has a section on contributing a
new container or modifying an existing container. Please check the chapter
**Adding and modifying containers** for details.

Before creating a pull request, please format your source code with Ruff,
which is installed in the Poetry virtual environment by default:

```bash
poetry run ruff format
# reorder imports:
poetry run ruff check --fix
```

Additionally, run the unit tests and check whether the documentation builds
(additional points if you update it):

```bash
# tests
poetry run pytest -vv
# docs
poetry run sphinx-build -M html source build -W
```


## Reviewing a pull request

The following guidelines are respected by the maintainers on reviewing a Pull Request:

* CI failures are treated seriously. As a general rule changes with failing CI are not being merged.

* A reviewer who has requested a change should be notified when the feedback
has been handled. This can be done by clicking the "re-request review" button
on the particular reviewers handle.

* A pull request is considered mergeable if it has no outstanding change
requests, at least one approval by the maintainers and sufficient time has
passed. Sufficient time means at least one business day, could be two or
three in case there are multiple people deciding to send in PRs.

* For changes that touch areas where there are subject matter experts (e.g.
the documentation team for documentation changes), the reviewer or the author
of the PR takes responsibility that these experts had an opportunity to
provide feedback before merging.

* *Single Review*: The reviewers address the most important issues in the
first review. Minor issues can be commented, for example with a 'NIT:'
prefix. These can be addressed in a followup change or documented for later
in an issue tracker entry. We avoid trickling in further feedback over the
whole review process so that the pull request author understands what the
outstanding action items are upfront.
