"""The declared code identity (rules 24/53) — split from report/artifacts.py
for the 150-code-line cap."""

import subprocess


def git_commit_hash() -> str:
    """The exact code identity that played this game; best effort.
    A dirty working tree is NAMED (`<hash>-dirty`): declaring a commit that
    does not contain the code actually running would be a false declaration."""
    def _git(*args: str) -> str:
        return subprocess.run(["git", *args], capture_output=True, text=True,
                              timeout=10).stdout.strip()

    try:
        head = _git("rev-parse", "HEAD")
        if not head:
            return "unknown"
        # tracked modifications only (git describe --dirty semantics): a
        # series CREATES untracked artifacts as it plays, and those must not
        # stamp -dirty onto every later window's signed declaration
        status = _git("status", "--porcelain", "--untracked-files=no")
        return f"{head}-dirty" if status else head
    except OSError:
        return "unknown"
