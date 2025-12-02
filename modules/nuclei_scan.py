from pathlib import Path
import subprocess
import json

def run_cmd(cmd, input_data=None):
    proc = subprocess.run(cmd, shell=True, text=True, capture_output=True, input=input_data)
    if proc.returncode != 0:
        print(proc.stderr)
    return proc.stdout

def run(global_cfg, target_cfg, httpx_file: Path, output_file: Path):
    nuclei_bin = global_cfg["tool_paths"]["nuclei"]

    if not httpx_file.exists():
        print("[!] httpx.json missing")
        return

    urls = []
    for line in httpx_file.read_text().splitlines():
        try:
            j = json.loads(line)
            if "url" in j:
                urls.append(j["url"])
        except:
            pass

    if not urls:
        print("[!] No URLs for nuclei")
        return

    print(f"    [+] Running nuclei on {len(urls)} URLs")

    input_data = "\n".join(urls)
    out = run_cmd(f"{nuclei_bin} -json -silent", input_data=input_data)

    output_file.write_text(out)
    print("[+] nuclei results saved")
