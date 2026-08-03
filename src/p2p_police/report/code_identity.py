"""The declared code identity (rules 24/53) — split from report/artifacts.py
for the 150-code-line cap."""

import subprocess


def git_commit_hash() -> str:
    """The HEAD commit of this checkout — the rule-53 provenance claim.

    A plain resolvable hash, the exact form the book's examples show and a
    grader's tooling can `git rev-parse`. No working-tree qualifier (pair
    decision with imreeyal, 2026-08-03): a series rewrites its own tracked
    artifact files mid-run, so a dirty marker fired on every window after
    the first artifact commit — an always-on alarm carrying no information,
    polluting a field whose spec is a commit id. "unknown" outside git.
    """
    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                              text=True, timeout=10).stdout.strip()
        return head or "unknown"
    except OSError:
        return "unknown"
