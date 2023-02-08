import logging

LOGGER = logging.getLogger(__name__)

_handler = logging.StreamHandler()
_handler.setFormatter(logging.Formatter(fmt="%(levelname)s: %(message)s"))

LOGGER.addHandler(_handler)
