import json, base64
from pathlib import Path
from google.oauth2 import service_account
from google.cloud import bigquery

env_path = Path.home() / "AppData/Local/hermes/profiles/data-analyst/.env"
env_text = env_path.read_text()
for line in env_text.splitlines():
    if line.startswith("GCP_SERVICE_ACCOUNT_KEY=") and not line.startswith("#"):
        b64_key = line.split("=", 1)[1].strip().strip("'\"")
        break
key_json = base64.b64decode(b64_key).decode()
creds_info = json.loads(key_json)
creds = service_account.Credentials.from_service_account_info(creds_info)
client = bigquery.Client(credentials=creds, project="project-2f1e456e-b1be-4551-92b")

# Check the get_matches function in bigquery_enhanced.py to see what view it uses
print("Checking get_matches function in bigquery_enhanced.py:")
with open("data/bigquery_enhanced.py", "r") as f:
    lines = f.readlines()
    for i, line in enumerate(lines):
        if "def get_matches" in line:
            # Print the function and the next 20 lines
            for j in range(i, min(i+30, len(lines))):
                print(f"{j+1:3}: {lines[j].rstrip()}")
            break

# Also check what the matches page is using
print("\nChecking pages/matches.py:")
with open("pages/matches.py", "r") as f:
    print(f.read())