from typing import Literal


SUPPORTED_SLE_VERSIONS = Literal[15]
SUPPORTED_SLE_SERVICE_PACKS = Literal[3, 4]

DEFAULT_SLE_VERSION: SUPPORTED_SLE_VERSIONS = 15
DEFAULT_SLE_SERVICE_PACK: SUPPORTED_SLE_SERVICE_PACKS = 4

LATEST_SLE_VERSION_SP: SUPPORTED_SLE_SERVICE_PACKS = 3

#: All container images with at most this service pack have the release-stage
#: label set to ``released``. Those with a higher service pack have it set to
#: ``beta``.
RELEASED_UNTIL_SLE_VERSION_SP: SUPPORTED_SLE_SERVICE_PACKS = 3
