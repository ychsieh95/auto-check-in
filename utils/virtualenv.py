"""Runtime helpers for commands launched with a virtualenv interpreter."""

import os
import sys
from collections.abc import MutableMapping
from pathlib import Path


def activate_current_virtualenv(
    *,
    executable: str | None = None,
    prefix: str | None = None,
    base_prefix: str | None = None,
    environ: MutableMapping[str, str] | None = None,
) -> bool:
    """Expose the active interpreter's virtualenv to child processes.

    Calling ``.venv/bin/python`` selects the right Python environment but,
    unlike sourcing ``.venv/bin/activate``, it doesn't export ``VIRTUAL_ENV``
    or put the environment's executable directory first on ``PATH``.  Mirror
    those non-interactive parts of activation so direct and scheduled launches
    behave consistently.
    """
    executable = executable or sys.executable
    prefix = prefix or sys.prefix
    base_prefix = base_prefix or sys.base_prefix
    environ = environ if environ is not None else os.environ

    if prefix == base_prefix:
        return False

    bin_dir = str(Path(executable).parent)
    path_parts = [part for part in environ.get("PATH", "").split(os.pathsep) if part]
    path_parts = [part for part in path_parts if part != bin_dir]

    environ["VIRTUAL_ENV"] = prefix
    environ["PATH"] = os.pathsep.join([bin_dir, *path_parts])
    return True
