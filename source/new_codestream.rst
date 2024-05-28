Creating a new codestream
=========================

To create a new codestream follow these steps:

1. Create a deployment branch. It must have the name
   :py:attr:`~staging.bot.StagingBot.deployment_branch_name` and should contain
   only a :file:`_config` file with the prjconf of the target project (usually
   you can take the prjconf from the previous service pack, if applicable).

2. Create the target project on OBS. This can be achieved via the bot command
   ``setup_obs_project``:

.. code-block:: shell

   $ export OSC_USER=$MY_USER
   $ export OSC_PASSWORD=$MY_PASS
   $ poetry run scratch-build-bot \
         --os-version $CODE_STREAM \
         --branch-name="doesNotMatter" \
         -vvvv setup_obs_project

3. Add the new code stream to the github action files to the ``os_version``
   list:
   :file:`.github/workflows/obs_build.yml`
   :file:`.github/workflows/update-deployment-branches.yml`
   :file:`.github/workflows/update-cr-project.yml`
   :file:`.github/workflows/cleanup-staging.yml`


SLCC specific steps
-------------------

For SLCC we need to build the FTP trees (= repositories) ourselves. For that we
must create the ``000*`` packages in the checked out project:

.. code-block:: shell

   $ cd devel:BCI:SLCC:$stream/

   $ osc mkpac 000product
   A    000product

   $ osc mkpac 000release-packages
   A    000release-packages

   $ osc mkpac 000package-groups
   A    000package-groups


We only have to touch ``000package-groups`` directly, the remaining two are
auto-generated using `pkglistgen
<https://github.com/openSUSE/openSUSE-release-tools/blob/master/docs/pkglistgen.md>`_.


python3 ./pkglistgen.py --verbose -A https://api.opensuse.org update_and_solve -p devel:BCI:SLCC:dynamic-developer -s target
