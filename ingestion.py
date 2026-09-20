import os
import re
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from config import settings


class RepositoryIngestionError(Exception):
    pass


def is_git_url(value: str) -> bool:
    return bool(re.match(r"^(https?://|git@)", value.strip()))


def is_github_https_url(value: str) -> bool:
    try:
        parsed = urlparse(value.strip())
        return parsed.scheme == "https" and parsed.hostname in {"github.com", "www.github.com"}
    except Exception:
        return False


def _name(source: str, path: Path) -> str:
    if is_git_url(source):
        if source.startswith("git@"):
            raw = source.split(":", 1)[-1]
        else:
            raw = urlparse(source).path
        name = raw.rstrip("/").split("/")[-1]
        return name[:-4] if name.endswith(".git") else name
    return path.name


def _github_clone_env(token: str, temp_dir: Path) -> dict:
    """Create a non-interactive Git authentication environment.

    The token is supplied through the child-process environment and is NOT
    inserted into the clone URL or command-line arguments.
    """
    askpass = temp_dir / "git-askpass.sh"
    askpass.write_text(
        "#!/bin/sh\n"
        "case \"$1\" in\n"
        "  *Username*) printf '%s\\n' \"${GITHUB_GIT_USERNAME:-x-access-token}\" ;;\n"
        "  *Password*) printf '%s\\n' \"$GITHUB_GIT_TOKEN\" ;;\n"
        "  *) printf '\\n' ;;\n"
        "esac\n",
        encoding="utf-8",
    )
    askpass.chmod(askpass.stat().st_mode | stat.S_IXUSR)

    env = os.environ.copy()
    env["GIT_ASKPASS"] = str(askpass)
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GITHUB_GIT_USERNAME"] = "x-access-token"
    env["GITHUB_GIT_TOKEN"] = token
    return env


def ingest_repository(source: str):
    source = source.strip()
    local = Path(source).expanduser()

    # Local repository/folder: no GitHub authentication required.
    if local.exists() and local.is_dir():
        p = local.resolve()
        return p, False, _name(source, p)

    if not is_git_url(source):
        raise RepositoryIngestionError(
            "Source must be a Git/GitHub URL or local repository folder."
        )

    work = Path(tempfile.mkdtemp(prefix="repo-intelligence-"))
    dest = work / "repository"

    # Keep the original URL clean. Never inject the token into the URL.
    clone_url = source
    clone_env = os.environ.copy()

    if settings.github_token and is_github_https_url(source):
        clone_env = _github_clone_env(settings.github_token, work)

    try:
        result = subprocess.run(
            ["git", "clone", "--depth", "1", "--", clone_url, str(dest)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=clone_env,
        )

        if result.returncode != 0:
            stderr = (result.stderr or "Git clone failed").strip()
            # Do not echo credentials if Git unexpectedly includes them.
            if settings.github_token:
                stderr = stderr.replace(settings.github_token, "***REDACTED***")
            raise RepositoryIngestionError(stderr)

        return dest, True, _name(source, dest)

    except RepositoryIngestionError:
        shutil.rmtree(work, ignore_errors=True)
        raise
    except Exception as exc:
        shutil.rmtree(work, ignore_errors=True)
        raise RepositoryIngestionError(f"Git clone failed: {exc}") from exc
