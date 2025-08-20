"""Image extraction service for healthcare PDFs."""

import io
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import pikepdf
from PIL import Image

logger = logging.getLogger(__name__)


@dataclass
class AssetMetadata:
    """Metadata for extracted assets (images, tables, etc.)."""

    kind: str  # "image" | "table"
    original_path: Optional[Path]
    stored_path: Path
    alt_text: Optional[str] = None
    page_number: Optional[int] = None
    caption: Optional[str] = None
    index: Optional[int] = None


class ImageExtractionService:
    """Service for extracting images from PDF files."""

    def __init__(self):
        """Initialize the image extraction service."""
        self.supported_formats = {".png", ".jpg", ".jpeg", ".tiff", ".bmp"}

    def extract_images_pikepdf(
        self, pdf_path: Path, output_dir: Path
    ) -> List[AssetMetadata]:
        """
        Extract images from PDF using pikepdf library.

        Args:
            pdf_path: Path to the PDF file
            output_dir: Directory to save extracted images

        Returns:
            List of AssetMetadata objects for extracted images
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        extracted_images = []

        try:
            with pikepdf.Pdf.open(pdf_path) as pdf:
                logger.info(f"Extracting images from PDF: {pdf_path}")

                for page_num, page in enumerate(pdf.pages, 1):
                    page_images = self._extract_page_images(page, page_num, output_dir)
                    extracted_images.extend(page_images)

        except Exception as e:
            logger.error(f"Failed to extract images from {pdf_path}: {e}")
            raise

        logger.info(f"Extracted {len(extracted_images)} images from {pdf_path}")
        return extracted_images

    def _extract_page_images(
        self, page, page_num: int, output_dir: Path
    ) -> List[AssetMetadata]:
        """Extract images from a specific page."""
        page_images = []
        image_index = 1

        try:
            # Get page resources
            if "/Resources" not in page or "/XObject" not in page["/Resources"]:
                return page_images

            xobjects = page["/Resources"]["/XObject"]

            for name, obj in xobjects.items():
                if obj.get("/Subtype") == "/Image":
                    try:
                        image_metadata = self._extract_image_object(
                            obj, page_num, image_index, output_dir
                        )
                        if image_metadata:
                            page_images.append(image_metadata)
                            image_index += 1
                    except Exception as e:
                        logger.warning(
                            f"Failed to extract image {name} from page {page_num}: {e}"
                        )
                        continue

        except Exception as e:
            logger.warning(f"Failed to process page {page_num} for images: {e}")

        return page_images

    def _extract_image_object(
        self, img_obj, page_num: int, img_index: int, output_dir: Path
    ) -> Optional[AssetMetadata]:
        """Extract a single image object from the PDF."""
        try:
            # Generate filename with page-indexed naming convention
            filename = f"page-{page_num:03d}-img-{img_index:02d}.png"
            output_path = output_dir / filename

            # Extract image data
            if "/Filter" in img_obj:
                # Handle different image filters
                filter_type = img_obj["/Filter"]
                if filter_type == "/DCTDecode":
                    # JPEG image
                    self._save_jpeg_image(img_obj, output_path)
                elif filter_type == "/FlateDecode":
                    # PNG or other compressed image
                    self._save_flate_image(img_obj, output_path)
                else:
                    # Try generic extraction
                    self._save_generic_image(img_obj, output_path)
            else:
                # Uncompressed image
                self._save_generic_image(img_obj, output_path)

            # Verify the image was saved successfully
            if output_path.exists() and output_path.stat().st_size > 0:
                return AssetMetadata(
                    kind="image",
                    original_path=None,
                    stored_path=output_path,
                    page_number=page_num,
                    index=img_index,
                )
            else:
                logger.warning(
                    f"Image extraction failed for page {page_num}, image {img_index}"
                )
                return None

        except Exception as e:
            logger.warning(
                f"Failed to extract image from page {page_num}, index {img_index}: {e}"
            )
            return None

    def _save_jpeg_image(self, img_obj, output_path: Path) -> None:
        """Save JPEG image from PDF object."""
        try:
            # Extract raw JPEG data
            raw_data = img_obj.read_raw_bytes()

            # Convert to PIL Image and save as PNG for consistency
            with Image.open(io.BytesIO(raw_data)) as img:
                img.save(output_path, "PNG")

        except Exception as e:
            logger.warning(f"Failed to save JPEG image to {output_path}: {e}")
            raise

    def _save_flate_image(self, img_obj, output_path: Path) -> None:
        """Save FlateDecode compressed image from PDF object."""
        try:
            # Get image properties
            width = int(img_obj["/Width"])
            height = int(img_obj["/Height"])

            # Extract decompressed data
            data = img_obj.read_bytes()

            # Determine color space and mode
            color_space = img_obj.get("/ColorSpace", "/DeviceRGB")
            if color_space == "/DeviceGray":
                mode = "L"
                components = 1
            elif color_space == "/DeviceRGB":
                mode = "RGB"
                components = 3
            elif color_space == "/DeviceCMYK":
                mode = "CMYK"
                components = 4
            else:
                mode = "RGB"
                components = 3

            # Create PIL Image
            expected_size = width * height * components
            if len(data) >= expected_size:
                img = Image.frombytes(mode, (width, height), data[:expected_size])
                img.save(output_path, "PNG")
            else:
                logger.warning(f"Insufficient image data for {output_path}")
                raise ValueError("Insufficient image data")

        except Exception as e:
            logger.warning(f"Failed to save FlateDecode image to {output_path}: {e}")
            raise

    def _save_generic_image(self, img_obj, output_path: Path) -> None:
        """Save image using generic extraction method."""
        try:
            # Try to extract as PIL image
            pil_image = pikepdf.PdfImage(img_obj).as_pil_image()
            pil_image.save(output_path, "PNG")

        except Exception as e:
            logger.warning(f"Failed to save generic image to {output_path}: {e}")
            raise

    def link_to_manifest(
        self, extracted_images: List[AssetMetadata], manifest: dict
    ) -> List[AssetMetadata]:
        """
        Link extracted images to manifest placeholders.

        Args:
            extracted_images: List of extracted image metadata
            manifest: Conversion manifest with figure information

        Returns:
            Updated list of AssetMetadata with linked captions
        """
        if not manifest or "figures" not in manifest:
            return extracted_images

        figures = manifest.get("figures", [])

        # Create a mapping of page numbers to figures
        page_to_figures = {}
        for figure in figures:
            page = figure.get("page", 0)
            if page not in page_to_figures:
                page_to_figures[page] = []
            page_to_figures[page].append(figure)

        # Link extracted images to figures based on page number and index
        for img_metadata in extracted_images:
            if img_metadata.page_number in page_to_figures:
                page_figures = page_to_figures[img_metadata.page_number]

                # Try to match by index within the page
                if img_metadata.index and img_metadata.index <= len(page_figures):
                    figure = page_figures[img_metadata.index - 1]
                    img_metadata.caption = figure.get("caption")
                    img_metadata.alt_text = figure.get("caption")
                elif len(page_figures) == 1:
                    # If only one figure on the page, link it
                    figure = page_figures[0]
                    img_metadata.caption = figure.get("caption")
                    img_metadata.alt_text = figure.get("caption")

        return extracted_images

    def extract_and_process(
        self, pdf_path: Path, manifest: dict, images_dir: Path
    ) -> List[AssetMetadata]:
        """
        Complete image extraction and processing workflow.

        Args:
            pdf_path: Path to the PDF file
            manifest: Conversion manifest with figure information
            images_dir: Directory to save extracted images

        Returns:
            List of processed AssetMetadata objects
        """
        try:
            # Extract images using pikepdf
            extracted_images = self.extract_images_pikepdf(pdf_path, images_dir)

            # Link to manifest placeholders
            linked_images = self.link_to_manifest(extracted_images, manifest)

            logger.info(
                f"Successfully processed {len(linked_images)} images for {pdf_path}"
            )
            return linked_images

        except Exception as e:
            logger.error(f"Image extraction and processing failed for {pdf_path}: {e}")
            # Return empty list to allow processing to continue
            return []


def extract_images_from_pdf(pdf_path: Path, output_dir: Path) -> List[AssetMetadata]:
    """Extract images from PDF file.

    Args:
        pdf_path: Path to the PDF file
        output_dir: Directory to save extracted images

    Returns:
        List of extracted image metadata
    """
    service = ImageExtractionService()
    return service.extract_images_pikepdf(pdf_path, output_dir)
