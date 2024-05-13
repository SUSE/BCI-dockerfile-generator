BCI build recipe generator
==========================

This repository contains the scripts to generate the build recipes (Dockerfiles
or `kiwi <https://github.com/OSInside/kiwi>`_ build descriptions) to build the
BCI development project in the `Open Build Service
<https://build.opensuse.org/project/subprojects/devel:BCI>`_.

Find the latest fully rendered documentation `here
<https://opensource.suse.com/BCI-dockerfile-generator/>`_.


Prerequisites
-------------

You will need the following tools:

- Python 3.10 or later
- `poetry <https://python-poetry.org/>`_
- `osc <https://github.com/openSUSE/osc/>`_ installed and configured to reach
  `OBS <https://build.opensuse.org/>`_ by default.
- ``python-dnf`` installed via your system's package manager (if you want to
  touch the .Net images)

To get started, clone this repository and run :command:`poetry install` in its
root directory.


Overview
--------

This repository contains two major components:

1. templating logic to autogenerate the :file:`Dockerfile` and kiwi build
   descriptions for SLE BCI (see :py:mod:`bci_build`) including an updater for
   our .Net images (see :py:mod:`dotnet`).

2. Github automation to render the templates into separate branches and
   synchronize them to the Open Build Service (see :py:mod:`staging`).


Contributing
------------

To contribute a new container or modify an existing one, please check the
chapter :ref:`adding-and-modifying-container-images`.

Before submitting your changes, please format your source code with `ruff
<https://docs.astral.sh/ruff/>`_:

.. code-block:: bash

   poetry run ruff format
   # reorder imports:
   poetry run ruff check --fix

Additionally, run the unit tests and check whether the documentation builds
(additional points if you update it):

.. code-block:: bash

   # tests
   poetry run pytest -vv
   # docs
   poetry run sphinx-build -M html source build -W


Documentation - READMEs
^^^^^^^^^^^^^^^^^^^^^^^

We are using Jinja2 templates to create Markdown formatted :file:`README.md`
files of each container.

To create a new :file:`README.md`, create a new file in the location
:file:`src/bci_build/package/$name/README.md.j2` where ``$name`` is the
container image name
(:py:attr:`~bci_build.package.BaseContainerImage.name`). Add a markdown
formatted README that explains the specifics of using this container
images. Focus on anything container specific, like volumes, the behavior of the
entrypoint and differences to the package in SLES/SLFO/Tumbleweed. If there is
upstream/downstream documentation, refer to it if applicable.

There are additionally the following helper templates, to enhance the READMEs:

- ``licensing_and_eula.j2``: Adds a standard licencing & EULA footer. **MUST**
  be included at the bottom of every README.

- ``badges.j2``: Adds a Redistributable & optional supportlevel badge. **MUST**
  be included at the top of every README.

- ``access_protected_images.j2``: Explains how to access an image behind the
  paywall. It only needs to be added at the bottom of paywalled images.


You can include the helpers via the following directive:

.. code-block::

   {% include 'licensing_and_eula.j2' %}


The :file:`README.md.j2` template is rendered with the respective
:py:class:`~bci_build.package.BaseContainerImage` being passed as the parameter
``image`` to the templating engine. This allows you to use all properties of the
:py:class:`~bci_build.package.BaseContainerImage` in the README, e.g. the image
title (:py:attr:`~bci_build.package.BaseContainerImage.title`) or the reference
(:py:attr:`~bci_build.package.BaseContainerImage.pretty_reference`).


Entrypoints
-----------

The projects currently provides two entry points. The first is the package build
description "dumper" called ``package``. It writes the build description of a
single container image into a specified directory:

.. code-block:: bash

   poetry run package postgres-12-sp4 ~/tmp/postgres/

The first argument is the name of the container image, this is the concatenation
of the image name (:py:attr:`~bci_build.package.BaseContainerImage.name`) and
the operating system version
(:py:attr:`~bci_build.package.BaseContainerImage.os_version`).


The second entry point is the github automation bot, which is not intended for
end user usage. You can find some details in the chapter :ref:`staging-bot`.
