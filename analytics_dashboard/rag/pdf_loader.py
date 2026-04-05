# rag/loaders/pdf_loader.py

from pypdf import PdfReader


def load_pdf(file_path):
    """
    Load PDF and extract text from all pages
    """
    reader = PdfReader(file_path)
    text = ""

    for page_num, page in enumerate(reader.pages):
        try:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        except Exception as e:
            print(f"Error reading page {page_num}: {e}")

    return text