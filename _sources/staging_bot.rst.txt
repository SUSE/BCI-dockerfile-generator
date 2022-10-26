Staging Bot
===========

Pull requests to the project are tested using a bot running via github
actions. It writes all build recipes for the images to a branch and creates a
staging project on https://build.opensuse.org/ under the user ``defolos``
(private account of `Dan Čermák <https://github.com/dcermak>`_). The bot will
then write a comment in the pull request for each OS version that had changes
with the branch name and the staging project URL and wait for the builds in the
staging project to finish. Once they have finished, it will update the comment
with the build results and either pass or fail the CI job depending on how the
containers built on OBS. The bot will delete the previously created staging
project and branches on each new push or when the PR is closed/merged.

For further details, see :py:class:`~staging.bot.StagingBot` or refer to the
script :command:`scratch-build-bot.py`.
