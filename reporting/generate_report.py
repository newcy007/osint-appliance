#!/usr/bin/env python3
"""
Generate the Markdown OSINT report for a given target.

Usage:
    python reporting/generate_report.py --target acme
"""

import json
import re
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parent.parent

HOST_RE = re.compile(r"\b(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}\b")

SEVERITY_SCORES = {
    "critical": 100,
    "high": 70,
    "medium": 40,
    "low": 10,
    "info": 1,
}


def load_yaml(path: Path):
    with open(path, "r") as f:
        return yaml.safe_load(f)


def load_subdomains(target_name: str):
    """
    Load subdomains from raw/subdomains.txt, extracting only
    hostname / FQDN-like tokens and deduping them.
    """
    fp = ROOT / "data" / target_name / "raw" / "subdomains.txt"
    if not fp.exists():
        return []

    hosts = set()
    for line in fp.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        for m in HOST_RE.findall(line):
            hosts.add(m.lower())
    return sorted(hosts)


def load_naabu(target_name: str):
    fp = ROOT / "data" / target_name / "raw" / "naabu.json"
    if not fp.exists():
        return [], set()

    open_ports = []
    ips = set()

    for line in fp.read_text().splitlines():
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

        open_ports.append(
            {
                "ip": ip,
                "port": j.get("port"),
                "protocol": j.get("protocol"),
                "tls": j.get("tls"),
                "note": "",
            }
        )

    return open_ports, ips


def load_httpx(target_name: str):
    fp = ROOT / "data" / target_name / "raw" / "httpx.json"
    if not fp.exists():
        return []

    items = []
    for line in fp.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            j = json.loads(line)
        except json.JSONDecodeError:
            continue

        items.append(
            {
                "url": j.get("url"),
                "status": j.get("status_code"),
                "title": j.get("title"),
                "tech": ", ".join(j.get("technologies", []))[:80],
            }
        )

    return items


def load_nuclei(target_name: str):
    fp = ROOT / "data" / target_name / "raw" / "nuclei.json"
    if not fp.exists():
        return []

    items = []
    for line in fp.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            j = json.loads(line)
        except json.JSONDecodeError:
            continue

        items.append(
            {
                "severity": j.get("info", {}).get("severity"),
                "template_id": j.get("template-id"),
                "host": j.get("host"),
                "info": j.get("info", {}).get("description", "")[:100],
            }
        )

    return items


def load_jsonl(path: Path):
    if not path.exists():
        return []
    items = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return items


def load_breaches(target_name: str):
    return load_jsonl(ROOT / "data" / target_name / "raw" / "breaches_hibp.json")


def load_github(target_name: str):
    return load_jsonl(ROOT / "data" / target_name / "raw" / "github_leaks.json")


def load_ipintel(target_name: str):
    return load_jsonl(ROOT / "data" / target_name / "raw" / "ipintel.json")


def load_shodan(target_name: str):
    fp = ROOT / "data" / target_name / "raw" / "shodan.json"
    if not fp.exists():
        return []

    text = fp.read_text().strip()
    if not text:
        return []

    # try array first
    items_raw = []
    try:
        data = json.loads(text)
        if isinstance(data, list):
            items_raw = data
        else:
            items_raw = [data]
    except json.JSONDecodeError:
        # assume JSONL
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                items_raw.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    items = []
    for j in items_raw:
        items.append(
            {
                "ip": j.get("ip") or j.get("ip_str"),
                "org": j.get("org"),
                "ports": ", ".join(str(p) for p in j.get("ports", []))[:80],
                "tags": ", ".join(j.get("tags", []))[:80],
                "vuln_ids": ", ".join(j.get("vuln_ids", []))[:80],
            }
        )
    return items


def derive_key_findings(open_ports, http_services, nuclei_findings):
    findings = []

    # Example: public RDP
    for p in open_ports:
        if p.get("port") == 3389:
            findings.append(
                {
                    "title": "Public RDP service exposed",
                    "severity": "high",
                    "category": "attack_surface",
                    "description": f"Host {p['ip']} exposes RDP (3389/tcp) to the internet.",
                    "evidence": f"Port 3389 open on {p['ip']}",
                }
            )

    # Critical/high nuclei
    for n in nuclei_findings:
        sev = (n.get("severity") or "").lower()
        if sev in ("critical", "high"):
            findings.append(
                {
                    "title": f"Nuclei finding ({sev})",
                    "severity": sev,
                    "category": "vulnerability",
                    "description": f"Template {n.get('template_id')} triggered.",
                    "evidence": n.get("host"),
                }
            )

    return findings


def calculate_risk_score(nuclei_findings):
    total = 0
    for f in nuclei_findings:
        sev = (f.get("severity") or "").lower()
        total += SEVERITY_SCORES.get(sev, 0)
    return total


def generate(target_name: str):
    target_cfg = load_yaml(ROOT / "config" / "targets" / f"{target_name}.yml")

    # All discovered hostnames
    all_subdomains = load_subdomains(target_name)

    # Filter to target-owned domains only
    primary_domains = [d.lower() for d in target_cfg.get("domains", [])]
    if primary_domains:
        subdomains = [
            h
            for h in all_subdomains
            if any(h == d or h.endswith("." + d) for d in primary_domains)
        ]
    else:
        subdomains = all_subdomains

    open_ports, ips = load_naabu(target_name)
    http_services = load_httpx(target_name)
    nuclei_findings = load_nuclei(target_name)
    breaches = load_breaches(target_name)
    github_items = load_github(target_name)
    ipintel_items = load_ipintel(target_name)
    shodan_items = load_shodan(target_name)

    stats = {
        "subdomain_count": len(subdomains),
        "ip_count": len(ips),
        "hosts_with_open_ports": len({p["ip"] for p in open_ports if p.get("ip")}),
        "http_services_count": len(http_services),
        "nuclei_findings_count": len(nuclei_findings),
        "breach_records": len(breaches),
        "github_matches": len(github_items),
        "shodan_hosts": len(shodan_items),
        "risk_score": calculate_risk_score(nuclei_findings),
    }

    key_findings = derive_key_findings(open_ports, http_services, nuclei_findings)

    # Add a timestamp into target_cfg (used by template)
    from datetime import datetime

    target_cfg.setdefault(
        "timestamp", datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    )
    target_cfg.setdefault("engagement_id", "BBP-OSINT-2025-001")

    env = Environment(
        loader=FileSystemLoader(str(ROOT / "reporting" / "templates"))
    )
    template = env.get_template("osint_report.md.j2")

    report_md = template.render(
        target=target_cfg,
        stats=stats,
        subdomains=subdomains,
        open_ports=open_ports,
        http_services=http_services,
        nuclei_findings=nuclei_findings,
        key_findings=key_findings,
        breaches=breaches,
        github=github_items,
        ipintel=ipintel_items,
        shodan=shodan_items,
    )

    out_path = ROOT / "data" / target_name / f"{target_name}_osint_report.md"
    out_path.write_text(report_md)
    print(f"[*] OSINT report written to: {out_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True, help="Target name (e.g. acme)")
    args = parser.parse_args()
    generate(args.target)
