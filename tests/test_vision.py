"""Tests for the vision module."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.vision.image_processor import ImageProcessor, VISION_SYSTEM_PROMPT


def test_vision_system_prompt_exists():
    assert "Ayurveda" in VISION_SYSTEM_PROMPT
    assert "Sanskrit" in VISION_SYSTEM_PROMPT


def test_encode_image():
    """Test base64 encoding of an image file."""
    processor = ImageProcessor()

    # Create a tiny test PNG (1x1 pixel)
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        # Minimal valid PNG
        import struct, zlib
        png_header = b'\x89PNG\r\n\x1a\n'
        ihdr_data = struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)
        ihdr_crc = zlib.crc32(b'IHDR' + ihdr_data) & 0xffffffff
        ihdr = struct.pack('>I', 13) + b'IHDR' + ihdr_data + struct.pack('>I', ihdr_crc)
        raw = zlib.compress(b'\x00\x00\x00\x00')
        idat_crc = zlib.crc32(b'IDAT' + raw) & 0xffffffff
        idat = struct.pack('>I', len(raw)) + b'IDAT' + raw + struct.pack('>I', idat_crc)
        iend_crc = zlib.crc32(b'IEND') & 0xffffffff
        iend = struct.pack('>I', 0) + b'IEND' + struct.pack('>I', iend_crc)
        f.write(png_header + ihdr + idat + iend)
        f.flush()

        b64_data, mime_type = processor._encode_image(Path(f.name))

    assert len(b64_data) > 0
    assert mime_type == "image/png"


def test_process_image_server_unavailable():
    """Test graceful handling when vision server is not running."""
    processor = ImageProcessor(base_url="http://localhost:99999/v1")

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        f.write(b'\x89PNG\r\n\x1a\n' + b'\x00' * 50)
        f.flush()

        result = processor.process_image(Path(f.name))

    assert result["content"] is None
    assert result["error"] is not None


def test_process_image_file_not_found():
    """Test handling of missing image file."""
    processor = ImageProcessor()
    try:
        processor.process_image("/nonexistent/image.png")
        assert False, "Should have raised FileNotFoundError"
    except FileNotFoundError:
        pass


def test_is_available_when_offline():
    processor = ImageProcessor(base_url="http://localhost:99999/v1")
    assert processor.is_available() is False


if __name__ == "__main__":
    test_vision_system_prompt_exists()
    test_encode_image()
    test_process_image_server_unavailable()
    test_process_image_file_not_found()
    test_is_available_when_offline()
    print("All vision tests passed!")
