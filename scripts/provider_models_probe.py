"""Read only the model IDs exposed to the configured provider account."""
import json
import os
import urllib.request

request = urllib.request.Request("https://api.openai.com/v1/models", headers={"Authorization": "Bearer " + os.environ["OPENAI_API_KEY"]})
with urllib.request.urlopen(request, timeout=30) as response:
    data = json.load(response)
ids = sorted(x["id"] for x in data.get("data", []) if isinstance(x, dict) and isinstance(x.get("id"), str) and x["id"].startswith(("gpt-", "o3", "o4")))
print("AVAILABLE_PROVIDER_MODELS=" + json.dumps(ids), flush=True)
