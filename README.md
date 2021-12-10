# BCI Dockerfile generator

This is a very simple script that generates the necessary files to build our BCI
containers in the Open Build Service.


## Prerequisites

You will need the following tools:

- Python 3.6.2 or later
- [`poetry`](https://python-poetry.org/)

To setup everything, clone this repository and run `poetry install` in its root
directory.

## Usage

Checkout the package that you want to update/recreate somewhere onto your
filesystem, e.g. to `~/packages/BCI/python-3.6-image.` and then run:
`poetry run ./bci-dockerfile-generator.py 4 python3.6 ~/packages/BCI/python-3.6-image/`
