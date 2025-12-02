from pathlib import Path
import requests
import urllib.parse
import json
import time

def run(global_cfg, target_cfg, output_file: Path):
    gh_cfg = global_cfg.get("apis", {}).get("github", {})
    if not gh_cfg or not gh_cfg.get("enabled"):
        print("    [!] GitHub module disabled or not configured.")
        return

    token = gh_cfg.get("token")
    if not token or token == "CHANGE_ME":
        print("    [!] GitHub token not set. Skipping GitHub OSINT.")
        return

    name = target_cfg.get("name", "")
    domains = target_cfg.get("domains", [])

    queries = set()

    if name:
        queries.add(f'"{name}"')
    for d in domains:
        queries.add(f'"{d}"')

    if not queries:
        print("    [!] No GitHub search queries derived from config.")
        return

    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "blackbox-osint/1.0"
    })

    results = []

    for q in queries:
        print(f"    [+] GitHub code search for: {q}")
        page = 1
        # limit pages to avoid rate limits; adjust as needed
        while page <= 3:
            params = {
                "q": q,
                "per_page": 50,
                "page": page
            }
            try:
                resp = session.get(
                    "https://api.github.com/search/code",
                    params=params,
                    timeout=20
                )
                if resp.status_code == 403:
                    print("    [!] Hit GitHub rate limit or permission issue.")
                    break
                resp.raise_for_status()
                data = resp.json()
                items = data.get("items", [])
                if not items:
                    break

                for item in items:
                    results.append({
                        "query": q,
                        "name": item.get("name"),
                        "path": item.get("path"),
                        "repo_full_name": item.get("repository", {}).get("full_name"),
                        "html_url": item.get("html_url"),
                        "score": item.get("score")
                    })

                # stop early if fewer than requested returned
                if len(items) < params["per_page"]:
                    break

                page += 1
                time.sleep(1)  # politeness
            except Exception as e:
                print(f"    [!] GitHub search error for {q}: {e}")
                break

    output_file.write_text("\n".join(json.dumps(r) for r in results))
    print(f"    [+] GitHub OSINT written to {output_file} ({len(results)} matches)")
