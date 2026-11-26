import re, zipfile, os

file_path = "docs/overleaf_report/main.tex"
with open(file_path, "r", encoding="utf-8") as f:
    text = f.read()

# Fix the 3 corrupted money occurrences in Introduction
text = text.replace(
    r"unplanned corporate IT downtime incurs an average cost exceeding \,600 per minute (\,000 per hour)",
    r"unplanned corporate IT downtime incurs an average cost exceeding \$5,600 per minute (\$336,000 per hour)"
)
text = text.replace(
    r"yields over \,000 in direct downtime loss avoidance",
    r"yields over \$16,000 in direct downtime loss avoidance"
)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(text)

print("Fixed monetary expressions in main.tex!")

# Create a zip package containing main.tex, references.bib, and all 6 screenshots
zip_path = "docs/overleaf_report/unimind_overleaf_report.zip"
files_to_zip = [
    "main.tex",
    "references.bib",
    "fig_dashboard_overview.png",
    "fig_cluster_topology.png",
    "fig_self_healing.png",
    "fig_k8s_fleet.png",
    "fig_ai_assistant.png",
    "fig_doc_ingestion.png"
]

with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    for fname in files_to_zip:
        fpath = os.path.join("docs", "overleaf_report", fname)
        if os.path.exists(fpath):
            zf.write(fpath, arcname=fname)
            print(f"Added {fname} ({os.path.getsize(fpath)} bytes) to zip")
        else:
            print(f"WARNING: File not found: {fpath}")

print(f"Zip package created successfully at: {zip_path} ({os.path.getsize(zip_path)} bytes)")
