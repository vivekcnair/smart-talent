import fitz
import docx
import pytesseract
from PIL import Image
import os

def extract_pdf(file_path):
    text = ""
    pdf = fitz.open(file_path)

    for page in pdf:
        text += page.get_text()

    return text

def extract_docx(file_path):
    doc = docx.Document(file_path)
    text = ""

    for para in doc.paragraphs:
        text += para.text + "\n"

    return text

def extract_image(file_path):
    img = Image.open(file_path)
    img = img.convert("L")
    text = pytesseract.image_to_string(img)
    return text

def extract_text(file_path):
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        return extract_pdf(file_path)
    elif ext == ".docx":
        return extract_docx(file_path)
    elif ext in [".png", ".jpg", ".jpeg"]:
        return extract_image(file_path)
    else:
        return ""