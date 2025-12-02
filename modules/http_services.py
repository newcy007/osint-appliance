from pathlib import Path
import subprocess

def run_cmd(cmd, input_data=None):
    proc = subprocess.run(cmd, shell=True, text=True, capture_output=True, input=input_data)
    if proc.returncode != 0:
        print(proc.stderr)
    return proc.stdout

def run(global_cfg, target_cfg, subdomains_file: Path, output_file: Path):
    httpx_bin = global_cfg["tool_paths"]["httpx"]

    if not subdomains_file.exists():
        print("[!] No subdomains.txt found.")
        return

    hosts = subdomains_file.read_text().splitlines()
    hosts = [h for h in hosts if h.strip()]

    print(f"    [+] Probing {len(hosts)} hosts with httpx")

    input_data = "\n".join(hosts)
    out = run_cmd(f"{httpx_bin} -silent -json", input_data=input_data)

    output_file.write_text(out)
    print("[+] httpx results saved")
