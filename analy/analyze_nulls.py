import glob
import re
import json
from collections import defaultdict
import os

def analyze_file(filepath):
    stats = defaultdict(int)
    total_papers = 0
    with open(filepath, 'r', encoding='utf-8') as f:
        content = ''
        while True:
            chunk = f.read(64*1024*1024)  # 64MB chunks
            if not chunk:
                break
            content += chunk
    # Count papers by paper_id occurrences (each paper has one)
    total_papers = len(re.findall(r'"paper_id"\s*:\s*"[^"]+"', content, re.IGNORECASE))
    if total_papers == 0:
        return {'file': filepath, 'total_papers': 0, 'pdf_null_pct': 0, 'abs_null_pct': 0, 'doi_null_pct': 0, 'pub_null_pct': 0, 'auth_aff_empty_pct': 0, 'auth_cite_zero_est_pct': 0}
    
    pdf_null = len(re.findall(r'"pdf_url"\s*:\s*"PDF URL not available"', content))
    abs_null = len(re.findall(r'"abstract"\s*:\s*"Abstract not available"', content))
    doi_null = len(re.findall(r'"doi"\s*:\s*"DOI not available"', content))
    pub_null = len(re.findall(r'"publisher"\s*:\s*"Unknown Publisher"', content))
    cite_zero = len(re.findall(r'"citation_count"\s*:\s*0', content)) / 6  # rough, ~6 authors avg
    # More fields
    venue_null = len(re.findall(r'"venue"\s*:\s*"Journal not specified"', content))
    journal_null = len(re.findall(r'"journal_name"\s*:\s*"Journal not specified"', content))
    ref_empty = len(re.findall(r'"references"\s*:\s*\[\]', content))
    aff_empty = len(re.findall(r'"affiliations"\s*:\s*\[\]', content))
    kw_empty = len(re.findall(r'"keywords"\s*:\s*\[\]', content))
    
    return {
        'file': filepath,
        'total_papers': total_papers,
        'pdf_null_pct': round(pdf_null / total_papers * 100, 1),
        'abs_null_pct': round(abs_null / total_papers * 100, 1),
        'doi_null_pct': round(doi_null / total_papers * 100, 1),
        'pub_null_pct': round(pub_null / total_papers * 100, 1),
        'auth_aff_empty_pct': round(aff_empty / total_papers * 100, 1),
        'auth_cite_zero_est_pct': round(min(cite_zero / total_papers * 100, 100), 1)
    }

cwd = 'd:/Stage chine/Nouveau dossier/ACADEMIC_PAPER_COLLECTION/academic/output'
files = glob.glob(os.path.join(cwd, 'papers_*.json'))
results = []

for f in files:
    res = analyze_file(f)
    results.append(res)
    print(json.dumps(res))

# Summary
avgs = {}
for key in ['pdf_null_pct', 'abs_null_pct', 'doi_null_pct']:
    avgs[key] = round(sum(r[key] for r in results)/len(results), 1)

print('SUMMARY AVERAGES:', json.dumps(avgs))
with open('analy_summary.json', 'w') as out:
    json.dump({'per_file': results, 'averages': avgs}, out, indent=2)
