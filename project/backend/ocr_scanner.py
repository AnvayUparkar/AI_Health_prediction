"""
General-Purpose OCR Scanner Module
===================================

A reusable OCR utility built on top of Tesseract OCR. Designed to be
imported from anywhere in the project for any text-extraction use case:

    from backend.ocr_scanner import extract_text_from_image
    from backend.ocr_scanner import extract_text_from_pdf
    from backend.ocr_scanner import extract_text

This module is NOT coupled to any specific feature (diet, report analysis, etc.).
It provides clean, general-purpose text extraction with optional image
preprocessing optimized for document scanning (medical reports, receipts,
handwritten notes, printed documents, etc.).

Dependencies:
    - pytesseract (+ Tesseract binary installed on the system)
    - Pillow (PIL)
    - opencv-python (cv2) — for advanced preprocessing
    - pdfplumber / PyPDF2 — for PDF extraction (optional)
"""

import os
import logging
from typing import Optional

import numpy as np

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy / optional imports — fail gracefully so the module can still be
# imported even if some deps are missing (e.g. in a test environment).
# ---------------------------------------------------------------------------
try:
    import cv2  # type: ignore
except ImportError:
    cv2 = None
    logger.warning("opencv-python not installed. Advanced preprocessing disabled.")

try:
    from PIL import Image, ImageFilter, ImageEnhance  # type: ignore
except ImportError:
    Image = None  # type: ignore
    ImageFilter = None
    ImageEnhance = None
    logger.warning("Pillow not installed. Image-based OCR will not work.")

try:
    import pytesseract  # type: ignore
except ImportError:
    pytesseract = None  # type: ignore
    logger.warning("pytesseract not installed. OCR will not work.")

try:
    import pdfplumber  # type: ignore
except ImportError:
    pdfplumber = None

# ---------------------------------------------------------------------------
# Tesseract binary auto-detection (Windows)
# ---------------------------------------------------------------------------
_COMMON_TESSERACT_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    r"C:\Users\{}\AppData\Local\Tesseract-OCR\tesseract.exe",
]


def _configure_tesseract() -> None:
    """
    Auto-detect and set the Tesseract binary path on Windows.
    Respects the TESSERACT_CMD environment variable if set.
    """
    if pytesseract is None:
        return

    # Environment variable takes priority
    env_path = os.environ.get("TESSERACT_CMD")
    if env_path and os.path.isfile(env_path):
        pytesseract.pytesseract.tesseract_cmd = env_path
        logger.info("Tesseract path set from TESSERACT_CMD: %s", env_path)
        return

    # Try common Windows paths
    username = os.environ.get("USERNAME", "")
    for path_template in _COMMON_TESSERACT_PATHS:
        path = path_template.format(username)
        if os.path.isfile(path):
            pytesseract.pytesseract.tesseract_cmd = path
            logger.info("Tesseract auto-detected at: %s", path)
            return

    # Fall back to system PATH (works on Linux/macOS or if already in PATH)
    logger.debug("Tesseract not found in common paths; assuming it's in system PATH.")


_configure_tesseract()

# ---------------------------------------------------------------------------
# Supported file extensions
# ---------------------------------------------------------------------------
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}
PDF_EXTENSIONS = {".pdf"}
SUPPORTED_EXTENSIONS = IMAGE_EXTENSIONS | PDF_EXTENSIONS


# ===================================================================
# IMAGE PREPROCESSING
# ===================================================================

def preprocess_image(
    image_path: str,
    *,
    grayscale: bool = True,
    denoise: bool = True,
    threshold: bool = True,
    sharpen: bool = False,
    resize_factor: Optional[float] = None,
    medical_report_mode: bool = False,
) -> "np.ndarray":
    """
    Preprocess an image to improve OCR accuracy.

    This function is designed for general-purpose document preprocessing but
    includes optimisations for medical reports (tabular data, aligned rows,
    flags like High/Low near values).

    Parameters
    ----------
    image_path : str
        Absolute or relative path to the image file.
    grayscale : bool
        Convert to grayscale.
    denoise : bool
        Apply Gaussian blur / non-local means denoising.
    threshold : bool
        Apply Otsu / adaptive thresholding for binarisation.
    sharpen : bool
        Apply unsharp-mask sharpening.
    resize_factor : float or None
        Scale factor for resizing (e.g. 2.0 = double size). None = auto.
    medical_report_mode : bool
        Enable medical-report-specific optimisations (adaptive threshold,
        morphological operations for table line removal, contrast boost).

    Returns
    -------
    numpy.ndarray
        The preprocessed image as a NumPy array (grayscale uint8).

    Raises
    ------
    FileNotFoundError
        If *image_path* does not exist.
    RuntimeError
        If opencv-python is not installed.
    """
    if cv2 is None:
        raise RuntimeError(
            "opencv-python is required for image preprocessing. "
            "Install it with: pip install opencv-python"
        )

    if not os.path.isfile(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    # Read the image
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Failed to read image (corrupt or unsupported format): {image_path}")

    # --- Resize (upscale small images for better OCR) ---
    h, w = img.shape[:2]
    if resize_factor is not None:
        img = cv2.resize(img, None, fx=resize_factor, fy=resize_factor, interpolation=cv2.INTER_CUBIC)
    elif max(h, w) < 1000:
        # Auto-upscale small images
        scale = 1500.0 / max(h, w)
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        logger.debug("Auto-upscaled small image by factor %.2f", scale)

    # --- Grayscale conversion ---
    if grayscale and len(img.shape) == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # --- Medical report optimisations ---
    if medical_report_mode:
        # Boost contrast using CLAHE (useful for scanned documents)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        img = clahe.apply(img)

        # Remove horizontal and vertical lines (table borders)
        img = _remove_table_lines(img)

    # --- Denoising ---
    if denoise:
        if len(img.shape) == 2:
            # Grayscale denoising
            img = cv2.fastNlMeansDenoising(img, h=10, templateWindowSize=7, searchWindowSize=21)
        else:
            img = cv2.fastNlMeansDenoisingColored(img, h=10, hForColorComponents=10)

    # --- Thresholding / Binarisation ---
    if threshold and len(img.shape) == 2:
        if medical_report_mode:
            # Adaptive threshold works better for uneven lighting in scans
            img = cv2.adaptiveThreshold(
                img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 8
            )
        else:
            # Otsu's threshold for general documents
            _, img = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # --- Sharpening ---
    if sharpen:
        kernel = np.array([[-1, -1, -1],
                           [-1,  9, -1],
                           [-1, -1, -1]])
        img = cv2.filter2D(img, -1, kernel)

    return img


def _remove_table_lines(img: "np.ndarray") -> "np.ndarray":
    """
    Remove horizontal and vertical lines from a grayscale image.
    This helps OCR when dealing with tabular medical reports where
    cell borders interfere with character recognition.
    """
    if cv2 is None:
        return img

    # Detect horizontal lines
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
    h_lines = cv2.morphologyEx(img, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)

    # Detect vertical lines
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
    v_lines = cv2.morphologyEx(img, cv2.MORPH_OPEN, vertical_kernel, iterations=2)

    # Combine detected lines
    lines = cv2.add(h_lines, v_lines)

    # Subtract lines from original image (invert, subtract, invert back)
    # Use bitwise operations to remove lines while preserving text
    result = cv2.add(img, lines)

    return result


# ===================================================================
# TEXT EXTRACTION — IMAGES
# ===================================================================

def extract_text_from_image(
    image_path: str,
    *,
    preprocess: bool = True,
    medical_report_mode: bool = False,
    lang: str = "eng",
    config: str = "",
) -> str:
    """
    Extract text from an image file using Tesseract OCR.

    Parameters
    ----------
    image_path : str
        Path to the image file (.jpg, .png, .bmp, .tiff, etc.).
    preprocess : bool
        Whether to apply image preprocessing before OCR.
    medical_report_mode : bool
        Enable medical-report-specific preprocessing.
    lang : str
        Tesseract language code (default: ``eng``).
    config : str
        Additional Tesseract config flags (e.g. ``--psm 6`` for table mode).

    Returns
    -------
    str
        Extracted text. Empty string on failure.

    Raises
    ------
    FileNotFoundError
        If the image file does not exist.
    RuntimeError
        If pytesseract or Pillow is not available.
    """
    if pytesseract is None:
        raise RuntimeError("pytesseract is required for OCR. pip install pytesseract")
    if Image is None:
        raise RuntimeError("Pillow is required for OCR. pip install Pillow")

    if not os.path.isfile(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    # Build Tesseract config — use PSM 6 (block of text) for medical reports
    ocr_config = config
    if medical_report_mode and not config:
        ocr_config = "--psm 6"

    try:
        if preprocess and cv2 is not None:
            # Use OpenCV preprocessing pipeline
            processed = preprocess_image(
                image_path,
                medical_report_mode=medical_report_mode,
            )
            # Convert NumPy array to PIL Image for pytesseract
            pil_img = Image.fromarray(processed)
        else:
            # Direct PIL open (basic fallback)
            pil_img = Image.open(image_path)
            # Basic Pillow preprocessing if OpenCV not available
            if preprocess:
                pil_img = pil_img.convert("L")  # grayscale
                enhancer = ImageEnhance.Contrast(pil_img)
                pil_img = enhancer.enhance(2.0)
                pil_img = pil_img.filter(ImageFilter.SHARPEN)

        text = pytesseract.image_to_string(pil_img, lang=lang, config=ocr_config)
        return text.strip()

    except Exception as e:
        logger.error("OCR extraction failed for '%s': %s", image_path, e)
        return ""


# ===================================================================
# TEXT EXTRACTION — PDFs
# ===================================================================

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract text from a PDF file.

    Uses pdfplumber as the primary extractor with PyPDF2 as fallback.

    Parameters
    ----------
    pdf_path : str
        Path to the PDF file.

    Returns
    -------
    str
        Extracted text. Empty string on failure.

    Raises
    ------
    FileNotFoundError
        If the PDF file does not exist.
    """
    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    # --- Strategy 1: pdfplumber (best for tables / medical reports) ---
    if pdfplumber is not None:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                pages = [page.extract_text() or "" for page in pdf.pages]
                text = "\n".join(pages).strip()
                if text:
                    return text
        except Exception as e:
            logger.warning("pdfplumber failed for '%s': %s", pdf_path, e)

    # --- Strategy 2: PyPDF2 fallback ---
    try:
        import PyPDF2  # type: ignore
        with open(pdf_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            pages = [page.extract_text() or "" for page in reader.pages]
            text = "\n".join(pages).strip()
            if text:
                return text
    except ImportError:
        logger.warning("PyPDF2 not installed; cannot extract text from PDF.")
    except Exception as e:
        logger.warning("PyPDF2 failed for '%s': %s", pdf_path, e)

    logger.error("All PDF extraction strategies failed for '%s'", pdf_path)
    return ""


# ===================================================================
# UNIFIED EXTRACTION (auto-detect file type)
# ===================================================================

def extract_text(
    file_path: str,
    *,
    medical_report_mode: bool = False,
    lang: str = "eng",
) -> str:
    """
    Auto-detect file type and extract text using the appropriate method.

    Parameters
    ----------
    file_path : str
        Path to the file (image or PDF).
    medical_report_mode : bool
        Enable medical-report optimisations for image OCR.
    lang : str
        Tesseract language code.

    Returns
    -------
    str
        Extracted text.
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()

    if ext in PDF_EXTENSIONS:
        return extract_text_from_pdf(file_path)
    elif ext in IMAGE_EXTENSIONS:
        return extract_text_from_image(
            file_path,
            medical_report_mode=medical_report_mode,
            lang=lang,
        )
    else:
        raise ValueError(
            f"Unsupported file type '{ext}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )


# ===================================================================
# UTILITY — Save extracted text
# ===================================================================

def save_extracted_text(text: str, output_path: str) -> str:
    """
    Save extracted text to a file.

    Parameters
    ----------
    text : str
        The text content to save.
    output_path : str
        Destination file path.

    Returns
    -------
    str
        The absolute path where the file was saved.
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)
    abs_path = os.path.abspath(output_path)
    logger.info("Extracted text saved to: %s", abs_path)
    return abs_path


# ===================================================================
# CLI — Quick test when run directly
# ===================================================================
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m backend.ocr_scanner <image_or_pdf_path>")
        sys.exit(1)

    path = sys.argv[1]
    print(f"Extracting text from: {path}")
    result = extract_text(path, medical_report_mode=True)
    print("=" * 60)
    print(result if result else "(No text extracted)")
    print("=" * 60)
