"""Image processor using Llama 4 (or any vision-capable LLM) for extracting text and descriptions."""

import base64
import logging
import mimetypes
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

VISION_SYSTEM_PROMPT = """You are an Ayurveda document analyzer. When given an image, extract and describe ALL relevant information.

For book pages or manuscripts:
- Extract all readable text accurately, preserving structure
- Note any Sanskrit/Devanagari text
- Describe any diagrams, illustrations, or charts

For herb/plant photos:
- Identify the plant if recognizable from an Ayurvedic context
- Describe physical characteristics (leaves, flowers, roots, color)
- Note any medicinal relevance if apparent

For anatomical or yoga diagrams:
- Describe the pose, technique, or body region shown
- Extract any labels or annotations
- Note the sequence or flow if multiple steps are shown

Be thorough and precise. This extracted content will be used for knowledge retrieval."""


class ImageProcessor:
    """Processes images through a vision-capable LLM for text extraction and description."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434/v1",
        model: str = "llama4",
        api_key: str = "ollama",
        timeout: float = 180.0,
    ):
        self.base_url = base_url
        self.model = model
        self.api_key = api_key
        self._client = httpx.Client(timeout=timeout)

    def _encode_image(self, image_path: Path) -> tuple[str, str]:
        """Read and base64-encode an image file. Returns (base64_data, mime_type)."""
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        mime_type, _ = mimetypes.guess_type(str(image_path))
        if mime_type is None:
            mime_type = "image/png"

        with open(image_path, "rb") as f:
            data = base64.b64encode(f.read()).decode("utf-8")

        return data, mime_type

    def process_image(
        self,
        image_path: str | Path,
        prompt: str = "Extract and describe all content from this image in detail.",
        system_prompt: str = VISION_SYSTEM_PROMPT,
    ) -> dict:
        """Process a single image and return extracted content."""
        image_path = Path(image_path)
        b64_data, mime_type = self._encode_image(image_path)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime_type};base64,{b64_data}"},
                },
                {"type": "text", "text": prompt},
            ],
        })

        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 2048,
            "temperature": 0.2,
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        try:
            response = self._client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]

            return {
                "content": content,
                "source_file": str(image_path),
                "file_name": image_path.name,
                "model": self.model,
                "error": None,
            }
        except httpx.ConnectError:
            error_msg = (
                f"Cannot connect to vision LLM at {self.base_url}. "
                "Make sure your LLM server is running with a vision model. "
                "For Ollama: 'ollama pull llama4' then 'ollama serve'"
            )
            logger.error(error_msg)
            return {
                "content": None,
                "source_file": str(image_path),
                "file_name": image_path.name,
                "model": self.model,
                "error": error_msg,
            }
        except Exception as e:
            logger.error(f"Vision processing failed for {image_path}: {e}")
            return {
                "content": None,
                "source_file": str(image_path),
                "file_name": image_path.name,
                "model": self.model,
                "error": str(e),
            }

    def process_directory(
        self,
        dir_path: str | Path,
        extensions: tuple = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"),
    ) -> list[dict]:
        """Process all images in a directory."""
        dir_path = Path(dir_path)
        results = []

        image_files = sorted(
            f for f in dir_path.rglob("*") if f.suffix.lower() in extensions
        )

        logger.info(f"Found {len(image_files)} images in {dir_path}")

        for img_path in image_files:
            logger.info(f"Processing: {img_path.name}")
            result = self.process_image(img_path)
            results.append(result)

        return results

    def is_available(self) -> bool:
        """Check if the vision LLM server is reachable."""
        try:
            url = f"{self.base_url}/models"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = self._client.get(url, headers=headers)
            return response.status_code == 200
        except Exception:
            return False

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
