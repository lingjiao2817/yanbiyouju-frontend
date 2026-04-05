from io import BytesIO
from pathlib import Path
from functools import lru_cache
import re
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile
import re

# 预编译两个正则表达式（模块级别，只编译一次）
_RE_SPACE_TO_SINGLE = re.compile(r"\s+")
_RE_REMOVE_CJK_SPACES = re.compile(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])")

MAX_UPLOAD_SIZE = 16 * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".docx"}
WORD_NAMESPACE = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


class DocumentParseError(ValueError):
    """Raised when the uploaded file cannot be parsed into text."""


def parse_uploaded_document(uploaded_file) -> tuple[str, str]:
    if uploaded_file is None or not uploaded_file.filename:
        raise DocumentParseError("请先上传 PDF 或 DOCX 文件。")

    suffix = Path(uploaded_file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise DocumentParseError("当前仅支持上传 PDF 或 DOCX 文件。")

    file_bytes = uploaded_file.read()
    uploaded_file.stream.seek(0)

    if not file_bytes:
        raise DocumentParseError("上传的文件为空。")
    
    if len(file_bytes) > MAX_UPLOAD_SIZE:
        raise DocumentParseError("文件过大（超过 16MB），请拆分后分多次上传。")

    if suffix == ".pdf":
        extracted_text = parse_pdf_text(file_bytes)
    else:
        extracted_text = parse_docx_text(file_bytes)

    return Path(uploaded_file.filename).stem, extracted_text


def parse_pdf_text(file_bytes: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("PDF 解析依赖未安装，请先执行 pip install -r requirements.txt。") from exc

    try:
        reader = PdfReader(BytesIO(file_bytes))
    except Exception as exc:
        raise DocumentParseError("PDF 文件无法解析，请确认文件未损坏。") from exc

    pages: list[str] = []
    missing_text_pages = 0
    for page in reader.pages:
        text = normalize_page_text(page.extract_text() or "")
        if text:
            pages.append(text)
        else:
            missing_text_pages += 1

    extracted_text = "\n\n".join(pages).strip()
    if extracted_text and missing_text_pages == 0:
        return extracted_text

    ocr_text = parse_pdf_text_with_ocr(file_bytes)
    if ocr_text:
        if extracted_text:
            return f"{extracted_text}\n\n{ocr_text}".strip()
        return ocr_text

    if extracted_text:
        return extracted_text

    raise DocumentParseError("未能从 PDF 中提取到文本，请确认文件不是扫描版、图片版或受保护 PDF。")


def parse_docx_text(file_bytes: bytes) -> str:
    try:
        archive = ZipFile(BytesIO(file_bytes))
    except BadZipFile as exc:
        raise DocumentParseError("DOCX 文件无法解析，请确认文件未损坏。") from exc

    try:
        document_xml = archive.read("word/document.xml")
    except KeyError as exc:
        raise DocumentParseError("DOCX 文件缺少正文内容，无法提取文本。") from exc

    try:
        root = ElementTree.fromstring(document_xml)
    except ElementTree.ParseError as exc:
        raise DocumentParseError("DOCX 内容格式异常，无法提取文本。") from exc

    paragraphs: list[str] = []
    for paragraph in root.findall(".//w:p", WORD_NAMESPACE):
        texts = [node.text or "" for node in paragraph.findall(".//w:t", WORD_NAMESPACE)]
        combined = normalize_page_text("".join(texts))
        if combined:
            paragraphs.append(combined)

    extracted_text = "\n\n".join(paragraphs).strip()
    if not extracted_text:
        raise DocumentParseError("未能从 DOCX 中提取到文本，请确认文档正文不是空白。")

    return extracted_text


def parse_pdf_text_with_ocr(file_bytes: bytes) -> str:
    try:
        import pypdfium2 as pdfium
    except ImportError as exc:
        raise RuntimeError("扫描版 PDF OCR 依赖未安装，请先执行 pip install -r requirements.txt。") from exc

    try:
        document = pdfium.PdfDocument(BytesIO(file_bytes))
    except Exception as exc:
        raise DocumentParseError("PDF 文件无法解析，请确认文件未损坏。") from exc

    ocr_engine = get_ocr_engine()
    pages: list[str] = []
    for page in document:
        bitmap = page.render(scale=1.5)   # 降低渲染分辨率，减少内存占用
        try:
            image = bitmap.to_numpy()
        finally:
            bitmap.close()
            page.close()                  # 每页处理完立即释放

        text = extract_text_from_ocr_image(ocr_engine, image)
        if text:
            pages.append(text)

    return "\n\n".join(pages).strip()


@lru_cache(maxsize=1)
def get_ocr_engine():
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError as exc:
        raise RuntimeError("扫描版 PDF OCR 依赖未安装，请先执行 pip install -r requirements.txt。") from exc

    return RapidOCR()


def extract_text_from_ocr_image(ocr_engine, image) -> str:
    EARLY_STOP_THRESHOLD = 0.92 
    best_text = ""
    best_score = float("-inf")
    for variant in generate_ocr_variants(image):
        ocr_result, _ = ocr_engine(variant)
        text, avg_confidence = extract_ocr_lines(ocr_result)
        score = len(text) + avg_confidence * 50
        if score > best_score:
            best_text = text
            best_score = score
        # 置信度足够高时提前退出，跳过剩余变体
        if avg_confidence >= EARLY_STOP_THRESHOLD:
            break
    return normalize_ocr_page_text(best_text)


def generate_ocr_variants(image):
    import cv2

    variants = [image]
    grayscale = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    normalized = cv2.normalize(grayscale, None, 0, 255, cv2.NORM_MINMAX)
    thresholded = cv2.adaptiveThreshold(
        normalized,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        11,
    )
    denoised = cv2.fastNlMeansDenoising(thresholded, None, 10, 7, 21)
    variants.append(cv2.cvtColor(normalized, cv2.COLOR_GRAY2BGR))
    variants.append(cv2.cvtColor(denoised, cv2.COLOR_GRAY2BGR))
    return variants


def extract_ocr_lines(ocr_result) -> tuple[str, float]:
    if not ocr_result:
        return "", 0.0

    items = []
    confidence_sum = 0.0
    confidence_count = 0
    for item in ocr_result:
        if len(item) < 3 or not isinstance(item[1], str):
            continue
        text = normalize_ocr_fragment(item[1])
        if not text:
            continue

        box = item[0]
        top = min(point[1] for point in box)
        bottom = max(point[1] for point in box)
        left = min(point[0] for point in box)
        right = max(point[0] for point in box)
        height = max(bottom - top, 1)
        items.append(
            {
                "text": text,
                "top": top,
                "bottom": bottom,
                "left": left,
                "right": right,
                "height": height,
            }
        )
        confidence_sum += float(item[2])
        confidence_count += 1

    if not items:
        return "", 0.0

    items.sort(key=lambda current: (current["top"], current["left"]))
    grouped_lines: list[list[dict]] = []
    for current in items:
        if not grouped_lines:
            grouped_lines.append([current])
            continue

        last_line = grouped_lines[-1]
        baseline = sum(item["top"] for item in last_line) / len(last_line)
        avg_height = sum(item["height"] for item in last_line) / len(last_line)
        if abs(current["top"] - baseline) <= max(12, avg_height * 0.6):
            last_line.append(current)
        else:
            grouped_lines.append([current])

    text_lines = [join_ocr_line(sorted(line, key=lambda current: current["left"])) for line in grouped_lines]
    average_confidence = confidence_sum / confidence_count if confidence_count else 0.0
    return "\n".join(line for line in text_lines if line), average_confidence


def join_ocr_line(items: list[dict]) -> str:
    if not items:
        return ""

    fragments = [items[0]["text"]]
    previous = items[0]
    for current in items[1:]:
        gap = current["left"] - previous["right"]
        if should_insert_space(previous["text"], current["text"], gap, previous["height"]):
            fragments.append(" ")
        fragments.append(current["text"])
        previous = current
    return "".join(fragments).strip()


def should_insert_space(previous_text: str, current_text: str, gap: float, height: float) -> bool:
    if gap <= max(8, height * 0.18):
        return False
    if contains_cjk(previous_text) or contains_cjk(current_text):
        return False
    return previous_text[-1].isalnum() and current_text[0].isalnum()


def normalize_ocr_fragment(text: str) -> str:
    # 1. 将任意连续空白压缩为一个空格，并去掉首尾空白
    text = _RE_SPACE_TO_SINGLE.sub(" ", text).strip()
    # 2. 删除中文字符之间的空白（如 "你 好" -> "你好"）
    text = _RE_REMOVE_CJK_SPACES.sub("", text)
    return text


def normalize_ocr_page_text(text: str) -> str:
    normalized_lines: list[str] = []
    for raw_line in text.splitlines():
        line = normalize_ocr_fragment(raw_line)
        if not line or is_noise_line(line):
            continue
        normalized_lines.append(line)

    return normalize_page_text("\n".join(normalized_lines))


def is_noise_line(line: str) -> bool:
    if re.fullmatch(r"[\W_]+", line):
        return True
    if len(line) == 1 and not line.isalnum() and not contains_cjk(line):
        return True
    return False


def contains_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)


def normalize_page_text(text: str) -> str:
    lines = [line.strip() for line in text.replace("\r\n", "\n").split("\n")]
    compact_lines = [line for line in lines if line]
    return "\n".join(compact_lines)
