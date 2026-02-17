import pdfplumber
from fastapi import UploadFile

async def extract_text_from_pdf(file: UploadFile) -> str:
    """
    Reads a PDF file and returns a single raw text string.
    """
    text_content = ""
    
    # Open the uploaded file stream
    with pdfplumber.open(file.file) as pdf:
        for page in pdf.pages:
            # Extract text and add a newline to separate rows
            page_text = page.extract_text()
            if page_text:
                text_content += page_text + "\n"
                
    return text_content