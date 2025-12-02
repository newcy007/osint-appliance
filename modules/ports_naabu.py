from pathlib import Path
import subprocess
import socket

def run_cmd(cmd):
    proc = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True
    )
    if proc.returncode != 0:
        print(f"[!] Command failed: {cmd}")
        print(proc.stderr)
    return proc.stdout

def resolve_to_ips(hosts):
    """Resolve hostnames to IPv4 addresses (deduped), skipping anything invalid."""
    ips = set()
    for h in hosts:
        h = h.strip()
        if not h:
            continue
        # skip obviously broken lines (spaces, arrows, etc.)
        if " " in h or "-->" in h or "(" in h:
            print(f"    [!] Skipping non-host line: {h}")
            continue
        try:
            for res in socket.getaddrinfo(h, None):
                ip = res[4][0]
                if ":" not in ip:  # keep IPv4 only
                    ips.add(ip)
        except Exception as e:
            # any encoding / DNS / IDNA issues – just skip this host
            print(f"    [!] Failed to resolve {h}: {e}")
            continue
    return sorted(ips)

def run(global_cfg, target_cfg, subdomains_file: Path, output_file: Path):
    naabu_bin = global_cfg["tool_paths"]["naabu"]

    if not subdomains_file.exists():
        print(f"[!] No subdomains file found: {subdomains_file}")
        return

    hosts = [h.strip() for h in subdomains_file.read_text().splitlines() if h.strip()]
    if not hosts:
        print("[!] No hosts in subdomains file for Naabu.")
        return

    print(f"    [+] Resolving {len(hosts)} hosts to IPs for Naabu...")
    ips = resolve_to_ips(hosts)

    if not ips:
        print("[!] No IPv4 addresses could be resolved. Skipping Naabu.")
        return

    print(f"    [+] Resolved to {len(ips)} unique IPv4 addresses.")

    targets_ip_file = output_file.parent / "naabu_targets.txt"
    targets_ip_file.write_text("\n".join(ips))

    print(f"    [+] Scanning {len(ips)} IPs with Naabu (connect scan)...")
    cmd = f'{naabu_bin} -silent -json -s c -list {targets_ip_file}'
    out = run_cmd(cmd)

    output_file.write_text(out)
    print(f"    [+] Naabu JSON written to {output_file}")
