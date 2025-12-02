#!/usr/bin/env python3
"""
Main orchestrator for the OSINT appliance.

Usage:
    python main.py --target acme
"""

import argparse
from pathlib import Path

import yaml

from modules import (
    subdomains,
    ports_naabu,
    http_services,
    nuclei_scan,
    breaches_hibp,
    github_leaks,
    ipintel,
    shodan_scan,
)

ROOT = Path(__file__).resolve().parent


def load_yaml(path: Path):
    with open(path, "r") as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True, help="Target name (e.g. acme)")
    args = parser.parse_args()

    target_name = args.target

    global_cfg = load_yaml(ROOT / "config" / "config.yml")
    target_cfg = load_yaml(ROOT / "config" / "targets" / f"{target_name}.yml")

    data_dir = ROOT / "data" / target_name
    raw_dir = data_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    subdomains_file = raw_dir / "subdomains.txt"
    naabu_file = raw_dir / "naabu.json"
    httpx_file = raw_dir / "httpx.json"
    nuclei_file = raw_dir / "nuclei.json"
    breaches_file = raw_dir / "breaches_hibp.json"
    github_file = raw_dir / "github_leaks.json"
    ipintel_file = raw_dir / "ipintel.json"
    shodan_file = raw_dir / "shodan.json"

    print(f"[*] Running OSINT pipeline for {target_cfg.get('name', target_name)}")
    print(f"    Data dir: {data_dir}")

    # 1. Subdomain discovery
    print("[*] Enumerating subdomains...")
    domains = target_cfg.get("domains", [])
    subdomains.run(global_cfg, target_cfg, domains, subdomains_file)
    print(f"    [+] Subdomains saved to {subdomains_file}")

    # 2. Naabu (ports)
    print("[*] Running naabu...")
    ports_naabu.run(global_cfg, target_cfg, subdomains_file, naabu_file)
    print(f"    [+] Naabu JSON written to {naabu_file}")

    # 3. httpx (service discovery)
    print("[*] Running httpx...")
    http_services.run(global_cfg, target_cfg, subdomains_file, httpx_file)
    print(f"    [+] httpx results saved to {httpx_file}")

    # 4. nuclei (template-based checks)
    print("[*] Running nuclei...")
    nuclei_scan.run(global_cfg, target_cfg, httpx_file, nuclei_file)
    print(f"    [+] nuclei results saved to {nuclei_file}")

    # 5. Breach intel (HIBP)
    if global_cfg.get("apis", {}).get("hibp", {}).get("enabled", False):
        print("[*] Running breach intel (HIBP)...")
        breaches_hibp.run(global_cfg, target_cfg, breaches_file)
        print(f"    [+] breach intel saved to {breaches_file}")
    else:
        print("    [!] HIBP API key not set or disabled – skipping breach intel.")

    # 6. GitHub OSINT
    if global_cfg.get("apis", {}).get("github", {}).get("enabled", False):
        print("[*] Running GitHub OSINT...")
        github_leaks.run(global_cfg, target_cfg, github_file)
        print(f"    [+] GitHub OSINT saved to {github_file}")
    else:
        print("    [!] GitHub token not set or disabled – skipping GitHub OSINT.")

    # 7. IP intel
    if global_cfg.get("apis", {}).get("ipinfo", {}).get("enabled", False):
        print("[*] Running IP intel enrichment...")
        ipintel.run(global_cfg, target_cfg, naabu_file, ipintel_file)
        print(f"    [+] IP intel saved to {ipintel_file}")
    else:
        print("    [!] IP intel module disabled or not configured.")

    # 8. Shodan
    if global_cfg.get("apis", {}).get("shodan", {}).get("enabled", False):
        print("[*] Running Shodan enrichment...")
        shodan_scan.run(global_cfg, target_cfg, naabu_file, shodan_file)
        print(f"    [+] Shodan results saved to {shodan_file}")
    else:
        print("    [!] Shodan API key not set or disabled – skipping Shodan enrichment.")

    print("[*] DONE. All raw results saved under", raw_dir)


if __name__ == "__main__":
    main()

