from pathlib import Path
import subprocess

def run_cmd(cmd):
    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if proc.returncode != 0:
        print(proc.stderr)
    return proc.stdout

def run(global_cfg, target_cfg, domains, output_file: Path):
    amass_bin = global_cfg["tool_paths"]["amass"]
    subfinder_bin = global_cfg["tool_paths"]["subfinder"]
    all_subs = set()

    for domain in domains:
        print(f"    [+] Amass: {domain}")
        out = run_cmd(f"{amass_bin} enum -passive -d {domain} -rf resolvers.txt")
        all_subs.update([i.strip() for i in out.splitlines() if i.strip()])

        print(f"    [+] Subfinder: {domain}")
        out = run_cmd(f"{subfinder_bin} -silent -d {domain}")
        all_subs.update([i.strip() for i in out.splitlines() if i.strip()])

    output_file.write_text("\n".join(sorted(all_subs)))
    print(f"    [+] {len(all_subs)} subdomains saved")
