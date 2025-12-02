from pathlib import Path
import requests

def run(global_cfg, target_cfg, output_file: Path):
    hibp_cfg = global_cfg.get("apis", {}).get("hibp", {})
    if not hibp_cfg or not hibp_cfg.get("enabled"):
        print("    [!] HIBP breach module disabled or not configured.")
        return

    api_key = hibp_cfg.get("key")
    if not api_key or api_key == "CHANGE_ME":
        print("    [!] HIBP API key not set. Skipping breach intel.")
        return

    domains = target_cfg.get("domains", [])
    if not domains:
        print("    [!] No domains configured for breach search.")
        return

    all_results = []

    session = requests.Session()
    session.headers.update({
        "hibp-api-key": api_key,
        "User-Agent": "blackbox-osint/1.0",
        "Accept": "application/json"
    })

    for d in domains:
        print(f"    [+] Querying breach intel for domain: {d}")
        try:
            # Domain search endpoint (for domain owners) – check your HIBP subscription & docs
            url = f"https://haveibeenpwned.com/api/v3/breaches?domain={d}"
            resp = session.get(url, timeout=15)
            if resp.status_code == 404:
                # no breaches for this domain
                continue
            resp.raise_for_status()
            data = resp.json()
            # normalise: attach which domain we asked for
            for item in data:
                item["_queried_domain"] = d
            all_results.extend(data)
        except Exception as e:
            print(f"    [!] Error querying HIBP for {d}: {e}")

    try:
        import json
        output_file.write_text("\n".join(json.dumps(r) for r in all_results))
        print(f"    [+] Breach intel written to {output_file} ({len(all_results)} records)")
    except Exception as e:
        print(f"    [!] Failed to write breach intel file: {e}")
