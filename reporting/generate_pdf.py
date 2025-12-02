#!/usr/bin/env python3
"""
Generate a styled PDF OSINT report from the Markdown report.

Usage:
    python reporting/generate_pdf.py --target acme
"""

import argparse
from pathlib import Path

from markdown import markdown
from weasyprint import HTML

ROOT = Path(__file__).resolve().parent.parent


def build_html(md_text: str, target_name: str) -> str:
    body_html = markdown(md_text, extensions=["extra", "tables", "toc"])

    css = """
    @page {
        size: A4;
        margin: 20mm 18mm 18mm 18mm;
    }

    body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Open Sans", Arial, sans-serif;
        font-size: 11pt;
        color: #222;
        line-height: 1.4;
    }

    h1, h2, h3 {
        font-family: "Montserrat", "Segoe UI Semibold", sans-serif;
        margin-top: 18pt;
        margin-bottom: 8pt;
        page-break-after: avoid;
    }

    h1 {
        font-size: 20pt;
        border-bottom: 2px solid #00ffff;
        padding-bottom: 4pt;
    }

    h2 {
        font-size: 16pt;
        border-left: 4px solid #00ffff;
        padding-left: 6pt;
    }

    h3 {
        font-size: 13pt;
        color: #00aaaa;
    }

    p {
        margin: 4pt 0 6pt 0;
    }

    strong {
        font-weight: 600;
    }

    table {
        border-collapse: collapse;
        width: 100%;
        margin: 8pt 0 14pt 0;
        font-size: 9.5pt;
    }

    th, td {
        border: 1px solid #ddd;
        padding: 4px 6px;
        vertical-align: top;
    }

    th {
        background-color: #00a0a0;
        color: #fff;
        font-weight: 600;
    }

    tr:nth-child(even) td {
        background-color: #f9f9f9;
    }

    hr {
        border: 0;
        border-top: 1px solid #ccc;
        margin: 12pt 0;
    }

    .footer {
        margin-top: 18pt;
        font-size: 8.5pt;
        color: #777;
        border-top: 1px solid #e0e0e0;
        padding-top: 6pt;
        text-align: right;
    }
    """

    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>OSINT Reconnaissance Report – {target_name}</title>
    <style>
    {css}
    </style>
</head>
<body>
{body_html}
<div class="footer">
    BlackBox Pentesters &mdash; Raising Standards in Cybersecurity Testing
</div>
</body>
</html>
"""
    return html_doc


def generate_pdf(target_name: str):
    data_dir = ROOT / "data" / target_name
    md_path = data_dir / f"{target_name}_osint_report.md"
    pdf_path = data_dir / f"{target_name}_osint_report.pdf"

    if not md_path.exists():
        raise SystemExit("Markdown report not found – run generate_report.py first.")

    md_text = md_path.read_text(encoding="utf-8")
    html = build_html(md_text, target_name)

    HTML(string=html, base_url=str(data_dir)).write_pdf(str(pdf_path))
    print(f"[*] PDF written to: {pdf_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate PDF OSINT report from Markdown.")
    parser.add_argument("--target", required=True, help="Target name (e.g. acme)")
    args = parser.parse_args()
    generate_pdf(args.target)
