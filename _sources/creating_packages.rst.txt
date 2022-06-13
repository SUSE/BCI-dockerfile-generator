Creating packages on IBS
========================

The `./src/bci_build/update.py` script can automatically submit updates to
existing packages on OBS or IBS, but it will fail to create new ones that have
just been added as code.

If you want to create a new Container Image on OBS, then proceed as follows:

1. Ensure that your Container Image has been created as code (see
   :ref:`adding-and-modifying-container-images`)

2. Create a new project on OBS in which you will create the initial package
   version. Usually the easiest way how to achieve this, is to branch an
   existing package into your home project (we use busybox-image in below example),
   as that will ensure that the repositories have been setup correctly.
   Once you have created it, check it out to your file system:

.. code-block:: console

   $ osc branch devel:BCI:SLE-15-SP4 busybox-image home:$my_user:new_pkg_proj
   $ osc co home:$my_user:new_pkg_proj

3. Create a new package in the checked out project. You **must** give it the
   same name as the parameter
   :py:attr:`~bci_build.package.BaseContainerImage.package_name` in the
   respective Container class, as otherwise the updater script will not work properly:

.. code-block:: console

   $ osc mkpac $new_pkg_name

4. Run the script :command:`./src/bci_build/package.py` as follows:

   .. code-block:: console

      $ poetry run ./src/bci_build/package.py $new_container_nvr-$SP_ID path_to_checkout_of_new_pkg_name

   where ``$new_container_nvr`` is the value of the
   :py:attr:`~bci_build.package.BaseContainerImage.nvr` property of your
   container class (this one is either the
   :py:attr:`~bci_build.package.BaseContainerImage.name` property or
   :py:attr:`~bci_build.package.BaseContainerImage.name` ``-``
   :py:attr:`~bci_build.package.LanguageStackContainer.version`, depending on
   the type of the container) and ``$SP_ID`` the identifier of this service pack
   (e.g. ``sp4`` or ``sp3``). You can find all available containers via
   :command:`poetry ./src/bci_build/package.py --help`.

   ``path_to_checkout_of_new_pkg_name`` is the path where you have checked out
   the *package* ``$new_pkg_name`` to.

5. Add a changelog entry mentioning the Jira ticket requesting this container,
   add all files, commit your changes and send a submit request back to the
   ``devel:BCI`` project:

.. code-block:: console

   $ osc vc -m "Initial version of the ... Container, jsc#BCI-XXX"
   $ osc add *
   $ osc ci -m "Initial version of the ... Container, jsc#BCI-XXX"
   $ osc sr -m "Initial version of the ... Container, jsc#BCI-XXX" devel:BCI:SLE-15-SP4 $new_pkg_name
