import os
import glob
import json
from json.decoder import JSONDecoder

def analyze_file(filepath):
    total = 0
    no_abs_with_pdf = 0

    with open(filepath, 'r', encoding='utf-8') as f:
        buffer = ''
        in_array = False

        while True:
            chunk = f.read(64 * 1024)  # 64KB chunks
            if not chunk:
                break
            buffer += chunk

            while True:
                try:
                    if not in_array:
                        buffer = buffer.strip()
                        if buffer.startswith('['):
                            buffer = buffer[1:]
                            in_array = True

                    obj, idx = JSONDecoder().raw_decode(buffer)
                    buffer = buffer[idx:].lstrip(', \n\r')

                    total += 1

                    abstract = obj.get('abstract')
                    pdf_url = obj.get('pdf_url')

                    # Condition: NO abstract BUT HAS PDF
                    if (
                        abstract == "Abstract not available"
                        and pdf_url is not None
                        and pdf_url != "PDF URL not available"
                    ):
                        no_abs_with_pdf += 1

                except (json.JSONDecodeError, ValueError):
                    break

    pct = (no_abs_with_pdf / total * 100) if total > 0 else 0

    print(f"{os.path.basename(filepath)}:")
    print(f"  Total papers: {total}")
    print(f"  No abstract BUT has PDF: {no_abs_with_pdf} ({pct:.2f}%)\n")

    return total, no_abs_with_pdf


def main():
    files = glob.glob(os.path.join('output', 'papers_*.json'))

    if not files:
        print("No files found in output/")
        return

    total_all = 0
    recoverable_all = 0

    for f in files:
        total, recoverable = analyze_file(f)
        total_all += total
        recoverable_all += recoverable

    pct_all = (recoverable_all / total_all * 100) if total_all > 0 else 0

    print("===== GLOBAL SUMMARY =====")
    print(f"Total papers: {total_all}")
    print(f"Recoverable (no abstract + has PDF): {recoverable_all}")
    print(f"Percentage: {pct_all:.2f}%")


if __name__ == "__main__":
    main()
