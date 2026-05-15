#!/usr/bin/env python3
"""Assert that every ``project.dependencies`` entry in pyproject.toml resolves
inside the bundled AppImage's Python.

The AppImage build script (:file:`scripts/build-appimage.sh`) hand-enumerates
the pip packages it installs so that conda-installed binaries (gdal, pyproj,
…) are not clobbered. That is fragile: any future entry added to the
``[project.dependencies]`` list in :file:`pyproject.toml` that is forgotten
in the script will silently fail at first import — that is exactly the
``curl_cffi`` gap that broke the first v0.13.0 tag push.

Usage::

    # After the AppImage has been built, extract it (or mount via FUSE) then:
    python scripts/check-appimage-deps.py <path-to-extracted-appimage>/usr/bin/python

The script exits 1 with a GitHub Actions ``::error::`` annotation listing the
missing distributions; 0 with a success message otherwise.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover - dev convenience on 3.10
    import tomli as tomllib  # type: ignore[no-redef]


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "Usage: check-appimage-deps.py <path-to-appimage-python>", file=sys.stderr
        )
        return 2

    target_python = Path(sys.argv[1])
    if not target_python.is_file():
        print(f"::error::Target Python not found: {target_python}", file=sys.stderr)
        return 2

    project_root = Path(__file__).resolve().parent.parent
    with (project_root / "pyproject.toml").open("rb") as fh:
        deps = tomllib.load(fh)["project"]["dependencies"]

    # Strip version pins, extras, and whitespace → bare distribution name.
    names: list[str] = []
    for spec in deps:
        name = re.split(r"[\[<>=!~ ;]", spec, maxsplit=1)[0].strip()
        if name:
            names.append(name)

    probe = (
        "import importlib.metadata as m, sys\n"
        "missing = []\n"
        "for n in sys.argv[1:]:\n"
        "    try:\n"
        "        m.version(n)\n"
        "    except m.PackageNotFoundError:\n"
        "        missing.append(n)\n"
        "sys.stdout.write('\\n'.join(missing))\n"
    )
    result = subprocess.run(
        [str(target_python), "-c", probe, *names],
        capture_output=True,
        text=True,
        check=True,
    )
    missing = [m for m in result.stdout.splitlines() if m.strip()]

    if missing:
        # GitHub Actions surfaces ``::error::`` lines in the workflow summary.
        print(f"::error::AppImage missing install_requires deps: {missing}")
        return 1

    print(f"All {len(names)} install_requires deps present in AppImage.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
