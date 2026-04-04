import glob
import re
import json
from collections import defaultdict
import os

def count_field_default(filepath):
    total_papers = 0
    fos_default = 0
    with open(filepath, 'r', encoding='utf-8') as f:
        content = ''
        while True:
            chunk = f.read(64*1024*1024)  # 64MB chunks
            if not chunk:
                break
            content += chunk
    # Count papers by paper_id occurrences (each paper has one)
    total_papers = len(re.findall(r'"paper_id"\s*:\s*"[^"]+"', content, re.IGNORECASE))
    # Count field_of_study default
    fos_default = len(re.findall(r'"field_of_study"\s*:\s*"Field not classified"', content))
    
    return {
        'file': filepath,
        'total_papers': total_papers,
        'fos_default_count': fos_default,
        'fos_default_pct': round(fos_default / total_papers * 100, 1) if total_papers > 0 else 0
    }

cwd = 'd:/Stage chine/Nouveau dossier/ACADEMIC_PAPER_COLLECTION/academic/output'
files = glob.glob(os.path.join(cwd, 'papers_*.json'))
results = []

grand_total_papers = 0
grand_fos_default = 0

for f in files:
    res = count_field_default(f)
    results.append(res)
    grand_total_papers += res['total_papers']
    grand_fos_default += res['fos_default_count']
    print(json.dumps(res))

print(f"GRAND TOTAL: papers={grand_total_papers}, fos_default={grand_fos_default}, pct={round(grand_fos_default / grand_total_papers * 100, 1) if grand_total_papers > 0 else 0}")

summary = {
    'per_file': results,
    'grand_total': {
        'papers': grand_total_papers,
        'fos_default': grand_fos_default,
        'pct': round(grand_fos_default / grand_total_papers * 100, 1) if grand_total_papers > 0 else 0
    }
}

with open('analy/fos_default_summary.json', 'w') as out:
    json.dump(summary, out, indent=2)

print("Summary saved to analy/fos_default_summary.json")

