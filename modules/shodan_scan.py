from pathlib import Path
import json
import time

import requests


def load_ips_from_naabu(naabu_file: Path):
    """Read unique IPs from naabu JSONL output."""
    if not naabu_file.exists():
        return set()
    ips = set()
    for line in naabu_file.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            j = json.loads(line)
        except json.JSONDecodeError:
            continue
        ip = j.get("ip")
        if ip:
            ips.add(ip)
    return ips


def run(global_cfg, target_cfg, naabu_file: Path, output_file: Path):
    shodan_cfg = global_cfg.get("apis", {}).get("shodan", {})
    if not shodan_cfg or not shodan_cfg.get("enabled"):
        print("    [!] Shodan module disabled or not configured.")
        return

    api_key = shodan_cfg.get("key", "").strip()
    if not api_key or api_key == "CHANGE_ME":
        print("    [!] Shodan API key not set. Skipping Shodan enrichment.")
        return

    ips = load_ips_from_naabu(naabu_file)
    if not ips:
        print("    [!] No IPs from Naabu to query in Shodan.")
        return

    print(f"    [+] Querying Shodan for {len(ips)} IPs...")

    base_url = "https://api.shodan.io/shodan/host"
    session = requests.Session()
    results = []

    for idx, ip in enumerate(sorted(ips), start=1):
        try:
            params = {"key": api_key}
            resp = session.get(f"{base_url}/{ip}", params=params, timeout=20)
            if resp.status_code == 404:
                # Not found in Shodan – not necessarily good or bad, just no data
                continue
            resp.raise_for_status()
            data = resp.json()
            # Normalise a bit for reporting
            ports = data.get("ports", [])
            org = data.get("org") or data.get("isp")
            tags = data.get("tags", [])
            vulns = data.get("vulns", {})

            results.append({
                "_ip": ip,
                "org": org,
                "ports": ports,
                "tags": tags,
                "vuln_ids": list(vulns.keys()) if isinstance(vulns, dict) else [],
                "data_raw": data,
            })
        except Exception as e:
            print(f"    [!] Shodan query failed for {ip}: {e}")
        # be polite – avoid slamming their API
        time.sleep(1)

    if not results:
        print("    [!] No Shodan data collected.")
        return

    output_file.write_text("\n".join(json.dumps(r) for r in results))
    print(f"    [+] Shodan data written to {output_file} ({len(results)} hosts)")
