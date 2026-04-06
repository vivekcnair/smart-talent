import fitz
import docx
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import os
import zipfile

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".png", ".jpg", ".jpeg"}


def validate_file(file_path):
    ext = os.path.splitext(file_path)[1].lower()

    if ext not in SUPPORTED_EXTENSIONS:
        return {"valid": False, "reason": "unsupported_format"}

    if os.path.getsize(file_path) == 0:
        return {"valid": False, "reason": "empty"}

    try:
        if ext == ".pdf":
            pdf = fitz.open(file_path)
            if pdf.page_count == 0:
                return {"valid": False, "reason": "corrupt"}
            pdf.close()

        elif ext == ".docx":
            if not zipfile.is_zipfile(file_path):
                return {"valid": False, "reason": "corrupt"}
            docx.Document(file_path)

        elif ext in {".png", ".jpg", ".jpeg"}:
            img = Image.open(file_path)
            img.verify()

    except Exception:
        return {"valid": False, "reason": "corrupt"}

    return {"valid": True, "reason": "ok"}


def _detect_column_threshold(blocks, page_width):
    x_starts = sorted(set(round(b[0] / 10) * 10 for b in blocks))

    best_gap = 0
    threshold = page_width / 2

    for i in range(1, len(x_starts)):
        gap = x_starts[i] - x_starts[i - 1]
        if gap > best_gap and x_starts[i - 1] > page_width * 0.2:
            best_gap = gap
            threshold = (x_starts[i] + x_starts[i - 1]) / 2

    return threshold


def _extract_page_text(page):
    try:
        page_width = page.rect.width
        blocks = page.get_text("blocks")

        if not blocks:
            return page.get_text()

        text_blocks = [b for b in blocks if b[6] == 0 and b[4].strip()]

        if not text_blocks:
            return page.get_text()

        x_positions = [b[0] for b in text_blocks]
        x_min, x_max = min(x_positions), max(x_positions)
        spread = x_max - x_min

        if spread > page_width * 0.35:
            threshold = _detect_column_threshold(text_blocks, page_width)

            sidebar_limit = page_width * 0.20

            sidebar_blocks = [b for b in text_blocks if b[0] < sidebar_limit]
            left_blocks = [b for b in text_blocks if sidebar_limit <= b[0] < threshold]
            right_blocks = [b for b in text_blocks if b[0] >= threshold]

            sidebar_blocks = sorted(sidebar_blocks, key=lambda b: (b[1], b[0]))
            left_blocks = sorted(left_blocks, key=lambda b: (b[1], b[0]))
            right_blocks = sorted(right_blocks, key=lambda b: (b[1], b[0]))

            ordered = sidebar_blocks + left_blocks + right_blocks
        else:
            ordered = sorted(text_blocks, key=lambda b: (b[1], b[0]))

        page_text = ""
        for b in ordered:
            block_text = b[4].strip()
            if block_text:
                page_text += block_text + "\n"

        return page_text

    except Exception:
        return page.get_text()


def extract_pdf(file_path):
    text = ""
    try:
        pdf = fitz.open(file_path)
        for page in pdf:
            text += _extract_page_text(page) + "\n"
        pdf.close()
    except Exception as e:
        raise RuntimeError(f"PDF extraction failed: {e}")
    return text


def extract_docx(file_path):
    try:
        doc = docx.Document(file_path)
        parts = []

        # Single pass over the document body — preserves order of paragraphs and tables
        for element in doc.element.body:
            tag = element.tag.split("}")[-1]

            if tag == "p":
                # Collect text from all runs in this paragraph
                para_text = "".join(
                    run.text for run in element.iterchildren()
                    if run.tag.split("}")[-1] == "r"
                    and hasattr(run, "text")
                ).strip()
                if para_text:
                    parts.append(para_text)

            elif tag == "tbl":
                for row in element.iterchildren():
                    if row.tag.split("}")[-1] != "tr":
                        continue
                    row_cells = []
                    for cell in row.iterchildren():
                        if cell.tag.split("}")[-1] == "tc":
                            cell_text = " ".join(
                                p.text_content() if hasattr(p, "text_content")
                                else "".join(r.text or "" for r in p.iterchildren())
                                for p in cell.iterchildren()
                            ).strip()
                            if cell_text:
                                row_cells.append(cell_text)
                    if row_cells:
                        parts.append(" | ".join(row_cells))

        return "\n".join(parts)

    except Exception as e:
        raise RuntimeError(f"DOCX extraction failed: {e}")


def extract_image(file_path):
    try:
        img = Image.open(file_path).convert("L")

        img = ImageEnhance.Contrast(img).enhance(2.0)
        img = img.filter(ImageFilter.SHARPEN)

        w, h = img.size
        if w < 1000:
            scale = 1000 / w
            img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

        custom_config = r"--oem 3 --psm 6"
        text = pytesseract.image_to_string(img, config=custom_config)
        return text

    except Exception as e:
        raise RuntimeError(f"Image OCR failed: {e}")


def extract_text(file_path):
    status = validate_file(file_path)

    if not status["valid"]:
        return "", status

    ext = os.path.splitext(file_path)[1].lower()

    try:
        if ext == ".pdf":
            text = extract_pdf(file_path)
        elif ext == ".docx":
            text = extract_docx(file_path)
        elif ext in {".png", ".jpg", ".jpeg"}:
            text = extract_image(file_path)
        else:
            return "", {"valid": False, "reason": "unsupported_format"}

        if not text.strip():
            return "", {"valid": False, "reason": "empty"}

        return text, {"valid": True, "reason": "ok"}

    except RuntimeError as e:
        return "", {"valid": False, "reason": f"corrupt — {e}"}
