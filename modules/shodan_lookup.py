import requests
import json
from pathlib import Path

def run(global_cfg, target_cfg, ips):
    shodan_cfg = global_cfg.get("apis", {}).get("shodan", {})
    if not shodan_cfg.get("enabled"):
        print("[!] Shodan module disabled.")
        return []

    api_key = shodan_cfg.get("key")
    if not api_key:
        print("[!] Shodan API key missing. Skipping.")
        return []

    print("[*] Running Shodan enrichment...")

    results = []
    out_dir = Path(target_cfg["data_dir"]) / "raw"
    out_dir.mkdir(parents=True, exist_ok=True)
    outfile = out_dir / "shodan.json"

    base_url = "https://api.shodan.io/shodan/host/{}?key={}"

    for ip in ips:
        url = base_url.format(ip, api_key)
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                data = r.json()
                data["ip"] = ip
                results.append(data)
                print(f"  [+] Shodan data for {ip} saved.")
            else:
                print(f"  [!] No Shodan data for {ip} (status {r.status_code})")
        except Exception as e:
            print(f"  [!] Error querying Shodan for {ip}: {e}")

    outfile.write_text(json.dumps(results, indent=2))
    print(f"[+] Shodan results written to: {outfile}")

    return results
