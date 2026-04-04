import glob
import re
import json
import os

def count_empty_abstract(filepath):
    total_papers = 0
    empty_abstracts = 0

    with open(filepath, 'r', encoding='utf-8') as f:
        content = ''
        while True:
            chunk = f.read(64 * 1024 * 1024)  # 64MB chunks
            if not chunk:
                break
            content += chunk

    # Count total papers
    total_papers = len(re.findall(
        r'"paper_id"\s*:\s*"[^"]+"',
        content,
        re.IGNORECASE
    ))

    # Count empty abstracts (your default value + optional cases)
    empty_abstracts = len(re.findall(
        r'"abstract"\s*:\s*(null|""|" "|"Abstract not available")',
        content,
        re.IGNORECASE
    ))

    return {
        'file': filepath,
        'total_papers': total_papers,
        'empty_abstracts': empty_abstracts,
        'empty_pct': round(empty_abstracts / total_papers * 100, 1) if total_papers > 0 else 0
    }

# Folder path
cwd = 'd:/Stage chine/Nouveau dossier/ACADEMIC_PAPER_COLLECTION/academic/filtered_output'
files = glob.glob(os.path.join(cwd, '*.json'))

results = []
grand_total = 0
grand_empty = 0

for f in files:
    res = count_empty_abstract(f)
    results.append(res)
    grand_total += res['total_papers']
    grand_empty += res['empty_abstracts']
    print(json.dumps(res))

# Grand summary
print(f"GRAND TOTAL: papers={grand_total}, empty_abstracts={grand_empty}, pct={round(grand_empty / grand_total * 100, 1) if grand_total > 0 else 0}")

summary = {
    'per_file': results,
    'grand_total': {
        'papers': grand_total,
        'empty_abstracts': grand_empty,
        'pct': round(grand_empty / grand_total * 100, 1) if grand_total > 0 else 0
    }
}

# Save result
os.makedirs('analy', exist_ok=True)
with open('analy/empty_abstract_summary.json', 'w') as out:
    json.dump(summary, out, indent=2)

print("Summary saved to analy/empty_abstract_summary.json")
