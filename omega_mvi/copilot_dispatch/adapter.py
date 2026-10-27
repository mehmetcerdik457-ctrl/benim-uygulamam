"""Owner-approved GitHub Copilot task adapter; no merge or deployment."""
import hashlib
import json
import os
import re
import urllib.error
import urllib.request
from .dispatch_journal import DispatchJournal

REPO = "mehmetcerdik457-ctrl/benim-uygulamam"
ROLES = ("architect", "security", "identity", "models", "orchestrator", "github", "android", "qa")

def validate(m):
    if not isinstance(m, dict) or m.get("repository") != REPO:
        raise ValueError("INVALID_REPOSITORY")
    if not isinstance(m.get("pinned_sha"), str) or not re.fullmatch("[a-f0-9]{40}", m["pinned_sha"]):
        raise ValueError("INVALID_SHA")
    tasks = m.get("tasks")
    if not isinstance(tasks, list) or len(tasks) != 8 or any(not isinstance(t, dict) for t in tasks):
        raise ValueError("EIGHT_TASKS_REQUIRED")
    if {t.get("role") for t in tasks} != set(ROLES):
        raise ValueError("EIGHT_UNIQUE_ROLES_REQUIRED")
    if len({t.get("issue") for t in tasks}) != 8:
        raise ValueError("UNIQUE_ISSUES_REQUIRED")
    for t in tasks:
        if type(t.get("issue")) is not int or t["issue"] <= 0 or t.get("approved") is not True:
            raise ValueError("INVALID_OR_UNAPPROVED_TASK")
        if not isinstance(t.get("prompt"), str) or not 20 <= len(t["prompt"]) <= 4000:
            raise ValueError("INVALID_PROMPT")
        agent = t.get("custom_agent")
        if agent is not None and (not isinstance(agent, str) or not re.fullmatch("[a-z0-9][a-z0-9-]{0,63}", agent)):
            raise ValueError("INVALID_CUSTOM_AGENT")
    return tasks

def api(method, path, token, body=None):
    headers = {"Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2026-03-10",
               "Authorization": "Bearer " + token,
               "User-Agent": "omega-copilot-dispatch/1"}
    data = json.dumps(body).encode("utf-8") if body is not None else None
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request("https://api.github.com" + path, headers=headers, data=data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise RuntimeError("GITHUB_HTTP_" + str(exc.code)) from None

def preflight(m, token):
    tasks = validate(m)
    branch = m.get("branch")
    if not isinstance(branch, str) or not re.fullmatch("omega/[a-zA-Z0-9._/-]{1,100}", branch) or ".." in branch:
        raise ValueError("INVALID_BRANCH")
    ref = api("GET", "/repos/" + REPO + "/git/ref/heads/" + branch, token)
    if ref.get("object", {}).get("sha") != m["pinned_sha"]:
        raise RuntimeError("STALE_BRANCH_SHA")
    for t in tasks:
        issue = api("GET", "/repos/" + REPO + "/issues/" + str(t["issue"]), token)
        if issue.get("state") != "open" or "pull_request" in issue:
            raise RuntimeError("ISSUE_NOT_OPEN_" + str(t["issue"]))
    return tasks

def dispatch(m, *, execute=False, token=None, journal_path=None):
    tasks = validate(m)
    if not execute:
        return {"mode": "PREVIEW", "sent": 0, "roles": [t["role"] for t in tasks]}
    if m.get("owner_dispatch_approved") is not True:
        raise RuntimeError("OWNER_APPROVAL_REQUIRED")
    if not token:
        token = os.environ.get("OMEGA_COPILOT_USER_TOKEN")
    if not token:
        raise RuntimeError("USER_TOKEN_REQUIRED")
    if not journal_path:
        raise RuntimeError("DURABLE_JOURNAL_REQUIRED")
    tasks = preflight(m, token)
    branch = m["branch"]
    fingerprint = {"repository": REPO, "branch": branch, "sha": m["pinned_sha"],
                   "tasks": sorted((t["role"], t["issue"]) for t in tasks)}
    batch = hashlib.sha256(json.dumps(fingerprint, sort_keys=True).encode()).hexdigest()
    journal = DispatchJournal(journal_path)
    receipts = []
    try:
        journal.claim_batch(batch)
        for t in tasks:
            journal.reserve(batch, t["role"], t["issue"])
            prompt = "OMEGA Issue #" + str(t["issue"]) + " [" + t["role"] + "]\n" + t["prompt"]
            body = {"prompt": prompt + "\nNo merge, deploy, secrets or permission changes.",
                    "base_ref": branch, "create_pull_request": True}
            if t.get("custom_agent"):
                body["custom_agent"] = t["custom_agent"]
            try:
                response = api("POST", "/agents/repos/" + REPO + "/tasks", token, body)
                if not isinstance(response, dict) or not response.get("id"):
                    raise RuntimeError("MISSING_TASK_ID")
                receipt = {"role": t["role"], "issue": t["issue"], "task_id": response["id"]}
                journal.confirmed(batch, t["role"], receipt)
                receipts.append(receipt)
            except Exception as exc:
                raise RuntimeError("DISPATCH_UNCERTAIN_RECONCILE_BEFORE_RETRY; confirmed=" + json.dumps(receipts)) from exc
        return {"mode": "DISPATCHED", "sent": len(receipts), "tasks": receipts}
    finally:
        journal.close()
