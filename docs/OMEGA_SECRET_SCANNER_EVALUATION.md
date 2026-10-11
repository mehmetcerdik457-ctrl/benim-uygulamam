# PROJECT OMEGA V2.0 — Secret scanner assessment (not an approval)

Status: evaluation only; no new paid services, credentials, production access, or main merge.

The existing GitHub Actions **Privacy Guard** uses a quiet, exit-status-aware
tracked-text heuristic. Exit code 0 means match and rejection; 1 means no match;
all other codes reject. Test with synthetically assembled markers in temporary
Git repositories. Do not echo matching lines or paths to the job log.

Candidate: **Gitleaks**, to supplement—not replace—the fast heuristic.
Acceptance criteria for a later pinned, independent CI job:

1. Evaluate a **version- and digest-pinned** scanner artifact and trusted source.
2. Scan tracked files and relevant Git history as appropriate; verify no raw
   finding, secret string, diff, or sensitive path enters Actions log or artifacts.
3. Save only a masked aggregate (status and total count) and reject on findings,
   crash, timeout, download/checksum failure, or malformed report.
4. Use disposable repositories with *only synthetic* test tokens for hit,
   miss, error, baseline/history, and log non-disclosure tests.
5. Explicitly document false positives, false negatives, scan coverage, and
   the human-reviewed allowlist/change process, without storing sensitive values.
6. Never claim success based on a static YAML test or an `action_required` run;
   require exact SHA-tied GitHub Actions job IDs and logs.

No Gitleaks binary is installed or executed by this commit. Production secret
protection and security sign-off remain BLOCKED until the above is evidenced.
