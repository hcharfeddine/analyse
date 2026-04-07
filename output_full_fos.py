import os
import json
import re
from pathlib import Path
import ijson

# === PATHS ===
INPUT_DIR = r"d:/Stage chine/Nouveau dossier/ACADEMIC_PAPER_COLLECTION/academic/filtered_output"
OUTPUT_DIR = r"d:/Stage chine/Nouveau dossier/ACADEMIC_PAPER_COLLECTION/academic/output_full_fos"

modified_dir = os.path.join(OUTPUT_DIR, "modified_per_year")
fos_sources_dir = os.path.join(OUTPUT_DIR, "fos_fill_sources")

Path(modified_dir).mkdir(parents=True, exist_ok=True)
Path(fos_sources_dir).mkdir(parents=True, exist_ok=True)

# === HELPERS ===
def is_missing_fos(fos):
    return not fos or fos == "Field not classified"

def is_missing_venue(venue):
    return not venue or venue == "Venue not specified"

def get_year_from_file(file_path):
    filename = os.path.basename(file_path)
    match = re.search(r'_(\d{4})_filtered\.json$', filename)
    return match.group(1) if match else "unknown"

# === OPTIMIZED: Fast streaming JSON parser using ijson ===
def stream_json_objects_fast(file_path):
    """Stream JSON objects from large array using ijson (much faster)"""
    with open(file_path, 'rb') as f:
        for obj in ijson.items(f, 'item'):
            yield obj

# === BATCH PROCESSING ===
def process_batch_papers(papers):
    """Process a batch of papers and return updated batch + tracking info"""
    batch = []
    keywords_ids = []
    abstract_ids = []
    pdf_ids = []
    updated_count = 0

    for paper in papers:
        # --- Venue ---
        if is_missing_venue(paper.get("venue")):
            paper["venue"] = paper.get("publisher") or paper.get("journal_name")

        # --- Field of Study ---
        if is_missing_fos(paper.get("field_of_study")):
            updated_count += 1
            paper_id = paper.get("paper_id")

            if paper.get("keywords"):
                paper["field_of_study"] = paper["keywords"]
                keywords_ids.append(paper_id)

            elif paper.get("abstract") and paper["abstract"] != "Abstract not available":
                paper["field_of_study"] = paper["abstract"]
                abstract_ids.append(paper_id)

            elif paper.get("pdf"):
                paper["field_of_study"] = paper["pdf"]
                pdf_ids.append(paper_id)

        batch.append(paper)

    return batch, updated_count, keywords_ids, abstract_ids, pdf_ids

# === MAIN PROCESSING ===
BATCH_SIZE = 500  # Process 500 papers at a time
fos_from_keywords_all = []
fos_from_abstract_all = []
fos_from_pdf_all = []

files = sorted(Path(INPUT_DIR).glob("*_filtered.json"))

for file_path in files:
    year = get_year_from_file(str(file_path))
    print(f"\n▶ Processing {file_path.name} (Year {year})...")

    output_file = os.path.join(modified_dir, f"papers_{year}_modified.json")
    total_updated = 0
    total_papers = 0

    batch = []
    with open(output_file, 'w', encoding='utf-8') as f_out:
        f_out.write("[\n")
        first = True

        try:
            for paper in stream_json_objects_fast(file_path):
                batch.append(paper)
                total_papers += 1

                # Process batch when size reached
                if len(batch) >= BATCH_SIZE:
                    processed, batch_updated, kw_ids, abs_ids, pdf_ids = process_batch_papers(batch)

                    # Write batch
                    for p in processed:
                        if not first:
                            f_out.write(",\n")
                        f_out.write(json.dumps(p))
                        first = False

                    # Track sources
                    total_updated += batch_updated
                    fos_from_keywords_all.extend(kw_ids)
                    fos_from_abstract_all.extend(abs_ids)
                    fos_from_pdf_all.extend(pdf_ids)

                    batch = []
                    print(f"  ✓ Processed {total_papers} papers...")

        except Exception as e:
            print(f"  ✗ Error: {e}")
            continue

        # Process remaining papers
        if batch:
            processed, batch_updated, kw_ids, abs_ids, pdf_ids = process_batch_papers(batch)
            for p in processed:
                if not first:
                    f_out.write(",\n")
                f_out.write(json.dumps(p))
                first = False

            total_updated += batch_updated
            fos_from_keywords_all.extend(kw_ids)
            fos_from_abstract_all.extend(abs_ids)
            fos_from_pdf_all.extend(pdf_ids)

        f_out.write("\n]")

    print(f"  ✓ Year {year}: {total_updated}/{total_papers} papers updated")

# === SAVE SOURCES FILES (only paper IDs) ===
print("\n▶ Saving source tracking files...")
with open(os.path.join(fos_sources_dir, "fos_from_keywords.json"), 'w') as f:
    json.dump({"count": len(fos_from_keywords_all), "paper_ids": fos_from_keywords_all}, f)

with open(os.path.join(fos_sources_dir, "fos_from_abstract.json"), 'w') as f:
    json.dump({"count": len(fos_from_abstract_all), "paper_ids": fos_from_abstract_all}, f)

with open(os.path.join(fos_sources_dir, "fos_from_pdf.json"), 'w') as f:
    json.dump({"count": len(fos_from_pdf_all), "paper_ids": fos_from_pdf_all}, f)

print("\n" + "="*60)
print("✓ PROCESSING COMPLETE")
print("="*60)
print(f"Modified JSON files: {modified_dir}")
print(f"Source tracking: {fos_sources_dir}")
print(f"\nSummary:")
print(f"  - Keywords source: {len(fos_from_keywords_all)} papers")
print(f"  - Abstract source: {len(fos_from_abstract_all)} papers")
print(f"  - PDF source: {len(fos_from_pdf_all)} papers")
print(f"  - Total updated: {len(fos_from_keywords_all) + len(fos_from_abstract_all) + len(fos_from_pdf_all)} papers")
