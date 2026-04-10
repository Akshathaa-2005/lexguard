import logging
import pdfplumber
import docx

logger = logging.getLogger(__name__)


def extract_text(file) -> str:
    """
    Extract plain text from an uploaded PDF or DOCX file object.
    """
    filename = file.filename.lower()

    if filename.endswith(".pdf"):
        return _extract_pdf(file)
    elif filename.endswith(".docx"):
        return _extract_docx(file)
    else:
        raise ValueError(f"Unsupported file type: {filename}")


def _extract_pdf(file) -> str:
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    logger.info(f"Extracted {len(text)} chars from PDF")
    return text.strip()


def _extract_docx(file) -> str:
    doc = docx.Document(file)
    text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    logger.info(f"Extracted {len(text)} chars from DOCX")
    return text.strip()
