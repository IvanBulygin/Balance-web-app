"""
Extract text from supplement guide PDFs and save as .txt alongside each PDF.

Path 3 interim step: text extraction only, no ingestion into sources/chunks
tables yet. That requires the Phase 1A Supabase migration + a designed PDF
ingestion feature (currently undocumented).

Usage:
    python backend/scripts/extract_pdf_text.py
"""

from pathlib import Path

from pdfminer.high_level import extract_text

PDF_DIR = Path(__file__).resolve().parent.parent / "data" / "pdfs"


def extract(pdf_path: Path) -> str:
    return extract_text(str(pdf_path)) or ""


def main() -> None:
    pdfs = sorted(PDF_DIR.glob("*.pdf"))
    if not pdfs:
        print(f"No PDFs found in {PDF_DIR}")
        return

    for pdf in pdfs:
        out = pdf.with_suffix(".txt")
        text = extract(pdf)
        out.write_text(text, encoding="utf-8")
        print(f"{pdf.name} -> {out.name} ({len(text):,} chars)")


if __name__ == "__main__":
    main()
