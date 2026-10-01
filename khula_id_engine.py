"""
Khula ID Verification Engine v4.0 — POPIA Compliant
Uses pytesseract OCR + SA ID algorithmic validation.
"""
import re
import hashlib
import sqlite3
from datetime import datetime
from khula_config import DB_PATH, SA_ID_RULES

# Try to import pytesseract; handle if not installed
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False


def preprocess_image_for_ocr(image):
    """Preprocess ID image for better OCR accuracy. Returns PIL Image."""
    if not CV2_AVAILABLE or not NUMPY_AVAILABLE:
        return image
    try:
        import numpy as np
        img_array = np.array(image)
        # Convert to grayscale if needed
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
        # Apply adaptive thresholding
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        # Denoise
        denoised = cv2.fastNlMeansDenoising(thresh, None, 10, 7, 21)
        from PIL import Image as PILImage
        return PILImage.fromarray(denoised)
    except Exception:
        return image


def extract_id_number_from_image(image):
    """
    Use OCR to extract a 13-digit SA ID number from an ID document photo.
    Returns: (success: bool, id_number: str|None, raw_text: str)
    """
    if not TESSERACT_AVAILABLE:
        return False, None, "pytesseract not installed. Run: apt-get install tesseract-ocr && pip install pytesseract"

    try:
        processed = preprocess_image_for_ocr(image)
        raw_text = pytesseract.image_to_string(processed)

        # Look for 13-digit number patterns
        digits_only = re.sub(r'\D', '', raw_text)

        # Try to find 13 consecutive digits with valid SA ID format
        for i in range(len(digits_only) - 12):
            candidate = digits_only[i:i+13]
            is_valid, _ = validate_sa_id_format(candidate)
            if is_valid:
                return True, candidate, raw_text

        # If no valid ID found, return the longest digit sequence for debugging
        return False, None, raw_text
    except Exception as e:
        return False, None, f"OCR error: {str(e)}"


def validate_sa_id_format(id_number: str):
    """
    Validate SA ID number format and checksum.
    Returns: (is_valid: bool, details: dict)

    SA ID format: YYMMDD G SSS C A Z (13 digits)
    - Digits 1-6: Date of birth (YYMMDD)
    - Digits 7-10: Gender (0000-4999 = female, 5000-9999 = male)
    - Digit 11: Citizenship (0 = SA citizen, 1 = permanent resident)
    - Digits 12: Sequential/Random (usually)
    - Digit 13: Luhn checksum
    """
    if not id_number or len(id_number) != 13:
        return False, {"error": "ID must be exactly 13 digits"}

    if not id_number.isdigit():
        return False, {"error": "ID must contain only digits"}

    # Extract components
    yy = int(id_number[0:2])
    mm = int(id_number[2:4])
    dd = int(id_number[4:6])
    gender_seq = int(id_number[6:10])  # digits 7-10
    citizenship = int(id_number[10])   # digit 11
    # digit 12 is sequential, digit 13 is checksum

    # Determine full year
    current_year = datetime.now().year % 100
    full_year = 1900 + yy if yy > current_year else 2000 + yy

    # Validate date
    try:
        dob = datetime(full_year, mm, dd)
        if dob > datetime.now():
            return False, {"error": "Date of birth is in the future"}
        age = (datetime.now() - dob).days // 365
        if age > SA_ID_RULES.get("MAX_AGE", 120):
            return False, {"error": f"Age ({age}) exceeds maximum ({SA_ID_RULES.get('MAX_AGE', 120)})"}
    except ValueError:
        return False, {"error": "Invalid date of birth"}

    # Validate gender
    gender = "female" if gender_seq < SA_ID_RULES.get("GENDER_FEMALE_MAX", 4999) else "male"

    # Validate citizenship
    if citizenship == SA_ID_RULES.get("CITIZENSHIP_CITIZEN", 0):
        citizenship_status = "citizen"
    elif citizenship == SA_ID_RULES.get("CITIZENSHIP_PERMANENT", 1):
        citizenship_status = "permanent_resident"
    else:
        citizenship_status = "unknown"

    # Luhn checksum (SA uses leftward Luhn on first 12 digits)
    def luhn_check(digits):
        total = 0
        weights = SA_ID_RULES.get("LUHN_WEIGHTS", [1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2])
        for i, d in enumerate(digits[:12]):
            weight = weights[i] if i < len(weights) else 1
            product = int(d) * weight
            total += product if product < 10 else (product // 10 + product % 10)
        check_digit = (10 - (total % 10)) % 10
        return check_digit == int(digits[12])

    if not luhn_check(id_number):
        return False, {
            "error": "Checksum validation failed",
            "dob": dob.strftime("%Y-%m-%d"),
            "gender": gender,
            "citizenship": citizenship_status,
            "age": age
        }

    return True, {
        "dob": dob.strftime("%Y-%m-%d"),
        "gender": gender,
        "citizenship": citizenship_status,
        "age": age,
        "is_valid": True
    }


def hash_id_number(id_number: str):
    """SHA-256 hash the full ID number for secure storage."""
    return hashlib.sha256(id_number.encode()).hexdigest()


def store_verification_result(user_id: int, id_number: str, status: str, details: dict, photo_hash: str = None, method: str = "ocr"):
    """
    Store verification result POPIA-compliantly.
    Only stores HASH of ID, last 4 digits, and verification status.
    NEVER stores the full ID number or the photo itself.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO ID_Verifications
        (user_id, id_number_hash, id_number_last4, verified_status, verified_at, id_photo_hash, gender, citizenship, age, verification_method)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        hash_id_number(id_number),
        id_number[-4:],
        status,
        datetime.now().isoformat(),
        photo_hash,
        details.get("gender"),
        details.get("citizenship"),
        details.get("age"),
        method
    ))
    conn.commit()
    conn.close()


def get_user_verification_status(user_id: int):
    """Get the latest verification status for a user."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT verified_status, verified_at, gender, citizenship, age
        FROM ID_Verifications
        WHERE user_id=?
        ORDER BY verified_at DESC LIMIT 1
    """, (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "status": row[0],
            "verified_at": row[1],
            "gender": row[2],
            "citizenship": row[3],
            "age": row[4]
        }
    return None


def verify_id_from_photo(image, user_id: int = None):
    """
    Full pipeline: photo -> OCR -> validate -> store -> return result.
    This is the MAIN entry point for ID verification.
    """
    # Step 1: Extract ID number via OCR
    success, id_number, raw_text = extract_id_number_from_image(image)

    if not success:
        return {
            "success": False,
            "stage": "ocr",
            "message": "Could not read ID number from photo. Please ensure the ID is clearly visible, well-lit, and all 13 digits are readable.",
            "raw_text_preview": raw_text[:300] if raw_text else None
        }

    # Step 2: Validate ID format and checksum
    is_valid, details = validate_sa_id_format(id_number)

    if not is_valid:
        if user_id:
            store_verification_result(user_id, id_number, "failed", details)
        return {
            "success": False,
            "stage": "validation",
            "message": f"ID validation failed: {details.get('error', 'Unknown error')}",
            "details": details,
            "id_last4": id_number[-4:],
        }

    # Step 3: Calculate photo hash for audit trail (POPIA compliance)
    try:
        photo_hash = hashlib.sha256(image.tobytes()).hexdigest()[:32]
    except Exception:
        photo_hash = None

    # Step 4: Store verification result
    if user_id:
        store_verification_result(user_id, id_number, "verified", details, photo_hash)

    return {
        "success": True,
        "stage": "complete",
        "message": "ID verified successfully!",
        "id_last4": id_number[-4:],
        "details": details,
        "photo_hash": photo_hash
    }
