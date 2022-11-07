BCI build recipe generator
==========================

This is a simple script that generates the necessary files to build our BCI
containers in the Open Build Service.


Prerequisites
-------------

You will need the following tools:

- Python 3.10 or later
- `poetry <https://python-poetry.org/>`_
- `osc <https://github.com/openSUSE/osc/>`_ installed and configured to reach
  `OBS <https://build.opensuse.org/>`_ by default. If you want to target IBS
  (build.suse.de) directly, then add the alias ``ibs`` for
  `<https://build.suse.de>`_.

To get started, clone this repository and run :command:`poetry install` in its
root directory.


Usage
-----

The main entry point of this project is the :file:`src/bci_build/update.py`
script. It will branch the package on IBS, check it out into a temporary
directory, regenererate the build recipes from the templates and send a
submitrequest back upstream.

For example, to update the nodejs containers, run:

.. code-block:: console

   poetry run ./src/bci_build/update.py --commit-msg "Update according to $reason" --images nodejs-12-sp4 nodejs-14-sp4 nodejs-16-sp4


Or to update all images for a service pack, run:

.. code-block:: console

   poetry run ./src/bci_build/update.py --commit-msg "Update according to $OtherReason" --service-pack 4



If you do not want to interact with OBS at all, then you can also use the
:file:`src/bci_build/package.py` script to just write the files of a single
package into a directory:

.. code-block:: console

   poetry run ./src/bci_build/package.py postgres-12-sp4 ~/tmp/postgres/



Use the dev-container
---------------------

You can use the dockerfile generator via a development container published as
`ghcr.io/suse/bci-dockerfile-generator`:

.. code-block:: console

   podman run --rm ghcr.io/suse/bci-dockerfile-generator:latest ./src/bci_build/update.py --help


Some commands of the dockerfile-generator use :command:`osc` and require access
to a valid :file:`~/.config/osc/oscrc`. You can expose your own to the container
via a volume as follows:

.. code-block:: console

   podman run --rm -v ~/.config/osc/:/root/.config/osc/:Z ghcr.io/suse/bci-dockerfile-generator:latest ./src/bci_build/update.py $additional_args
