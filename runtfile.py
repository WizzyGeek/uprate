UVRUN = [
    "uv",
    "run",
    "--isolated"
]
PY = lambda ver: [f"--python={ver}"]
PYTEST = ["pytest"]
VERSIONS = [310, 311, 312, 313, 314]

TARGETS = {
    **{f"test{i}": (UVRUN + PY(i) + PYTEST) for i in VERSIONS},
    "testnew": ("test313", "test314"),
    "all": ("test310", "test311", "test312", "test313")
}

import os
env = dict(os.environ)

env["UV_PYTHON_DOWNLOADS"]="automatic"