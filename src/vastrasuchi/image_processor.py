"""Image processing pipeline for product catalog photos."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

from PIL import Image, ImageEnhance, ImageStat


class ImageProcessor:
    """Enhance and validate product images for ONDC catalog quality."""

    def __init__(self) -> None:
        self.rembg_available = self._check_rembg()

    def _check_rembg(self) -> bool:
        try:
            import rembg  # type: ignore # noqa: F401

            return True
        except Exception:
            return False

    def process_product_image(self, image_path: str) -> str:
        """Process image: background -> crop -> resize -> enhance."""
        source = Path(image_path)
        if not source.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        image = Image.open(source).convert("RGBA")
        processed = image

        if self.rembg_available:
            try:
                from rembg import remove  # type: ignore

                buffer = io.BytesIO()
                image.save(buffer, format="PNG")
                removed = remove(buffer.getvalue())
                processed = Image.open(io.BytesIO(removed)).convert("RGBA")
            except Exception:
                processed = image

        processed = self._autocrop(processed)
        processed = self._fit_square(processed, 1000)
        processed = self._enhance_if_dark(processed)

        out_path = source.with_name(f"{source.stem}_processed.jpg")
        processed.convert("RGB").save(out_path, format="JPEG", quality=92, optimize=True)
        return str(out_path)

    def create_thumbnail(self, image_path: str, size: tuple[int, int] = (200, 200)) -> str:
        """Create thumbnail for quick catalog previews."""
        source = Path(image_path)
        if not source.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        image = Image.open(source).convert("RGB")
        image.thumbnail(size)
        out_path = source.with_name(f"{source.stem}_thumb.jpg")
        image.save(out_path, format="JPEG", quality=88, optimize=True)
        return str(out_path)

    def validate_image(self, image_path: str) -> dict[str, Any]:
        """Validate image resolution, size and format constraints."""
        issues: list[str] = []
        source = Path(image_path)
        if not source.exists():
            return {"valid": False, "issues": [f"File not found: {image_path}"]}

        allowed = {".jpg", ".jpeg", ".png", ".webp"}
        if source.suffix.lower() not in allowed:
            issues.append("Unsupported format. Use JPG/PNG/WEBP.")

        file_size_mb = source.stat().st_size / (1024 * 1024)
        if file_size_mb > 10:
            issues.append("File size exceeds 10MB.")

        with Image.open(source) as img:
            w, h = img.size
            if w < 300 or h < 300:
                issues.append("Resolution too low. Minimum 300x300 required.")
            if w / h > 3 or h / w > 3:
                issues.append("Extreme aspect ratio may hurt catalog quality.")

        return {"valid": len(issues) == 0, "issues": issues}

    def _autocrop(self, image: Image.Image) -> Image.Image:
        if image.mode != "RGBA":
            image = image.convert("RGBA")
        alpha = image.split()[-1]
        bbox = alpha.getbbox()
        if bbox:
            return image.crop(bbox)
        return image

    def _fit_square(self, image: Image.Image, size: int) -> Image.Image:
        image.thumbnail((size, size))
        canvas = Image.new("RGBA", (size, size), (255, 255, 255, 255))
        x = (size - image.width) // 2
        y = (size - image.height) // 2
        canvas.paste(image, (x, y), image if image.mode == "RGBA" else None)
        return canvas

    def _enhance_if_dark(self, image: Image.Image) -> Image.Image:
        grayscale = image.convert("L")
        brightness = ImageStat.Stat(grayscale).mean[0]
        result = image
        if brightness < 105:
            result = ImageEnhance.Brightness(result).enhance(1.15)
            result = ImageEnhance.Contrast(result).enhance(1.12)
        return result


def enhance_product_image(image_path: str) -> dict[str, str]:
    """Backward-compatible helper for image enhancement."""
    processor = ImageProcessor()
    try:
        output = processor.process_product_image(image_path)
        return {"input_path": image_path, "output_path": output, "status": "processed"}
    except Exception as exc:
        return {"input_path": image_path, "output_path": image_path, "status": f"skipped: {exc}"}
