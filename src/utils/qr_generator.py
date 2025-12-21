"""QR code generator for VLESS URLs."""

import io

import qrcode


def generate_qr_code(data: str) -> io.BytesIO:
    """Generate QR code image from data string.

    Args:
        data: String to encode in QR code (e.g., VLESS URL)

    Returns:
        BytesIO buffer containing PNG image
    """
    qr = qrcode.QRCode(
        version=None,  # Auto-select version based on data length
        error_correction=qrcode.constants.ERROR_CORRECT_M,  # Medium error correction
        box_size=10,
        border=4,  # Standard border for better scanning
    )
    qr.add_data(data)
    qr.make(fit=True)

    # Simple image without styling - better compatibility with phone scanners
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer
