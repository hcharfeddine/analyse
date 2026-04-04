import os
import json
import re
from pathlib import Path

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

# === STREAM JSON OBJECTS FROM HUGE ARRAY ===
def stream_json_objects(file):
    buffer = ""
    depth = 0

    while True:
        chunk = file.read(1024 * 1024)  # 1MB chunks
        if not chunk:
            break

        buffer += chunk
        i = 0
        start = None

        while i < len(buffer):
            char = buffer[i]

            if char == '{':
                if depth == 0:
                    start = i
                depth += 1

            elif char == '}':
                depth -= 1
                if depth == 0 and start is not None:
                    yield buffer[start:i+1]
                    buffer = buffer[i+1:]
                    i = -1
                    start = None

            i += 1

# === PART 3 STORAGE ===
fos_from_keywords = []
fos_from_abstract = []
fos_from_pdf = []

# === PROCESS FILES ===
files = sorted(Path(INPUT_DIR).glob("*_filtered.json"))

for file_path in files:
    year = get_year_from_file(str(file_path))
    print(f"Processing {file_path} for year {year}...")

    output_file = os.path.join(modified_dir, f"papers_{year}_modified.json")

    updated_count = 0

    with open(file_path, 'r', encoding='utf-8') as f_in, \
         open(output_file, 'w', encoding='utf-8') as f_out:

        # Start JSON array
        f_out.write("[\n")
        first = True

        for obj_str in stream_json_objects(f_in):
            try:
                paper = json.loads(obj_str)
            except:
                continue

            # --- Venue ---
            if is_missing_venue(paper.get("venue")):
                paper["venue"] = paper.get("publisher") or paper.get("journal_name")

            # --- Field of Study ---
            if is_missing_fos(paper.get("field_of_study")):
                updated_count += 1

                if paper.get("keywords"):
                    paper["field_of_study"] = paper["keywords"]
                    fos_from_keywords.append(paper.get("paper_id"))

                elif paper.get("abstract") and paper["abstract"] != "Abstract not available":
                    paper["field_of_study"] = paper["abstract"]
                    fos_from_abstract.append(paper.get("paper_id"))

                elif paper.get("pdf"):
                    paper["field_of_study"] = paper["pdf"]
                    fos_from_pdf.append(paper.get("paper_id"))

            # Write JSON object properly with commas
            if not first:
                f_out.write(",\n")
            f_out.write(json.dumps(paper))
            first = False

        # Close JSON array
        f_out.write("\n]")

    print(f"Year {year}: {updated_count} papers updated.")

# === SAVE PART 3 FILES ===
with open(os.path.join(fos_sources_dir, "fos_from_keywords.json"), 'w') as f:
    json.dump(fos_from_keywords, f, indent=2)

with open(os.path.join(fos_sources_dir, "fos_from_abstract.json"), 'w') as f:
    json.dump(fos_from_abstract, f, indent=2)

with open(os.path.join(fos_sources_dir, "fos_from_pdf.json"), 'w') as f:
    json.dump(fos_from_pdf, f, indent=2)

print("\n=== DONE ===")
print(f"Modified JSON files: {modified_dir}")
print(f"Paper ID outputs: {fos_sources_dir}")
