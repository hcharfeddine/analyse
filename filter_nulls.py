import os
import json
import ijson
from collections import defaultdict

INPUT_FILE = 'output/papers_20260311_113216_2015.json'
OUTPUT_FILE = 'filtered_output/papers_2015_filtered.json'

# =========================
# SAME CONFIG
# =========================

MANDATORY_FIELDS = [
    'paper_id',
    'title',
    'year',
    'cited_by_count',
    'references',
    'publication_type'
]

VENUE_FIELDS = ['venue', 'publisher', 'journal_name']

MISSING_VALUES = {
    'paper_id': None,
    'title': '',
    'year': 0,
    'cited_by_count': 0,
    'references': [],
    'publication_type': 'Unknown',
    'venue': 'Venue not specified',
    'publisher': 'Unknown Publisher',
    'journal_name': 'Journal not specified',
    'abstract': 'Abstract not available',
    'keywords': [],
    'pdf_url': 'PDF URL not available',
    'field_of_study': 'Field not classified'
}

# =========================
# HELPERS
# =========================

def is_missing(field, value):
    if value is None:
        return True
    if field in MISSING_VALUES:
        mv = MISSING_VALUES[field]
        if isinstance(mv, list):
            return not value or len(value) == 0
        return value == mv
    return False


def has_keyword_or_abstract(paper):
    return (
        not is_missing('keywords', paper.get('keywords')) or
        not is_missing('abstract', paper.get('abstract'))
    )


def has_pdf_or_field(paper):
    return (
        not is_missing('pdf_url', paper.get('pdf_url')) or
        not is_missing('field_of_study', paper.get('field_of_study'))
    )


def paper_is_valid(paper):
    for field in MANDATORY_FIELDS:
        if is_missing(field, paper.get(field)):
            return False

    if all(is_missing(f, paper.get(f)) for f in VENUE_FIELDS):
        return False

    if not has_keyword_or_abstract(paper):
        return False

    if not has_pdf_or_field(paper):
        return False

    authors = paper.get('authors', [])
    if not authors or all(is_missing('author_id', a.get('author_id')) for a in authors):
        return False

    return True


# =========================
# PROCESS 2015 WITH RECOVERY
# =========================

def process_2015():
    os.makedirs('filtered_output', exist_ok=True)

    kept = 0
    total = 0
    year_dist = defaultdict(int)

    with open(INPUT_FILE, 'r', encoding='utf-8') as f, \
         open(OUTPUT_FILE, 'w', encoding='utf-8') as out_f:

        out_f.write('[\n')
        first = True

        try:
            for paper in ijson.items(f, 'item'):
                total += 1

                if paper_is_valid(paper):
                    if not first:
                        out_f.write(',\n')

                    json.dump(paper, out_f, ensure_ascii=False)
                    first = False
                    kept += 1

                    year = paper.get('year')
                    if year:
                        year_dist[year] += 1

        except ijson.common.IncompleteJSONError:
            print("⚠️ Reached end of corrupted file (partial recovery used)")

        out_f.write('\n]')

    print("\n=== 2015 RESULT ===")
    print(f"Total read: {total}")
    print(f"Total kept: {kept}")
    print("Distribution:")
    for y in sorted(year_dist):
        print(f"  {y}: {year_dist[y]}")


if __name__ == '__main__':
    process_2015()
