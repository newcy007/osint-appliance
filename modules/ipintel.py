from pathlib import Path
import json
import requests

def load_ips_from_naabu(naabu_file: Path):
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
    ipinfo_cfg = global_cfg.get("apis", {}).get("ipinfo", {})
    if not ipinfo_cfg or not ipinfo_cfg.get("enabled"):
        print("    [!] IP intel module disabled or not configured.")
        return

    token = ipinfo_cfg.get("token", "").strip()
    base_url = "https://ipinfo.io"

    ips = load_ips_from_naabu(naabu_file)
    if not ips:
        print("    [!] No IPs from Naabu to enrich.")
        return

    print(f"    [+] Enriching {len(ips)} IPs via ipinfo.io")

    session = requests.Session()
    if token and token != "CHANGE_ME":
        session.params = {"token": token}

    results = []

    for ip in sorted(ips):
        try:
            resp = session.get(f"{base_url}/{ip}/json", timeout=10)
            resp.raise_for_status()
            data = resp.json()
            data["_ip"] = ip
            results.append(data)
        except Exception as e:
            print(f"    [!] Failed to enrich {ip}: {e}")

    output_file.write_text("\n".join(json.dumps(r) for r in results))
    print(f"    [+] IP intel written to {output_file} ({len(results)} records)")
