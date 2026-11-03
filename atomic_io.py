"""Write a file so another process can never read it half-written (temp file in the same folder, fsync, rename).

Same pattern as propkit.atomic, kept here so main.py, the printer service and the web workers need no propkit import.
Standard library only.
"""
import json
import os
import tempfile


def write_text(path, text, mode=None):
    """Replace `path` with `text` atomically; keeps the old file's permission bits unless `mode` is given."""
    path = os.path.abspath(path)
    try:
        keep = mode if mode is not None else (os.stat(path).st_mode & 0o7777)
    except OSError:
        keep = mode if mode is not None else 0o644
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix="." + os.path.basename(path) + ".")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, keep)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def write_json(path, data, indent=None, mode=None, **kw):
    write_text(path, json.dumps(data, indent=indent, **kw) + "\n", mode=mode)


def read_json(path, default=None):
    """The parsed file, or `default` if it is missing, empty or unreadable."""
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default
