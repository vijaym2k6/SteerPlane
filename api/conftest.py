"""Pytest bootstrap for the API test suite.

The API tests import the application as ``api.app.*`` (e.g. ``from api.app.config
import settings``). That only resolves if the repository root — the parent of
this ``api/`` directory — is on ``sys.path``. CI runs ``pytest`` from inside
``api/``, so without this shim the imports fail with
``ModuleNotFoundError: No module named 'api'`` and the suite silently collects
nothing. Inserting the repo root here makes the tests pass whether they are run
from the repo root (``pytest api/tests``) or from inside ``api/`` (``pytest tests``).
"""

import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
