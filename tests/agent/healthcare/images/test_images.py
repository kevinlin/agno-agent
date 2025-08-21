"""Unit tests for image extraction service."""

import io
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pikepdf
import pytest
from PIL import Image

from agent.healthcare.images import AssetMetadata, ImageExtractionService


class TestAssetMetadata:
    """Test AssetMetadata dataclass."""

    def test_asset_metadata_creation(self):
        """Test creating AssetMetadata instance."""
        asset = AssetMetadata(
            kind="image",
            original_path=Path("original.pdf"),
            stored_path=Path("stored.png"),
            alt_text="Test image",
            page_number=1,
            caption="Figure 1: Test",
            index=1,
        )

        assert asset.kind == "image"
        assert asset.original_path == Path("original.pdf")
        assert asset.stored_path == Path("stored.png")
        assert asset.alt_text == "Test image"
        assert asset.page_number == 1
        assert asset.caption == "Figure 1: Test"
        assert asset.index == 1

    def test_asset_metadata_optional_fields(self):
        """Test AssetMetadata with minimal required fields."""
        asset = AssetMetadata(
            kind="image", original_path=None, stored_path=Path("stored.png")
        )

        assert asset.kind == "image"
        assert asset.original_path is None
        assert asset.stored_path == Path("stored.png")
        assert asset.alt_text is None
        assert asset.page_number is None
        assert asset.caption is None
        assert asset.index is None


class TestImageExtractionService:
    """Test ImageExtractionService class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = ImageExtractionService()
        self.test_pdf_path = Path("test.pdf")
        self.test_output_dir = Path("test_output")

    def test_service_initialization(self):
        """Test service initialization."""
        assert self.service.supported_formats == {
            ".png",
            ".jpg",
            ".jpeg",
            ".tiff",
            ".bmp",
        }

    @patch("pikepdf.Pdf.open")
    @patch("pathlib.Path.mkdir")
    def test_extract_images_pikepdf_success(self, mock_mkdir, mock_pdf_open):
        """Test successful image extraction using pikepdf."""
        # Mock PDF with pages
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf_open.return_value.__enter__.return_value = mock_pdf

        # Mock page image extraction
        with patch.object(self.service, "_extract_page_images") as mock_extract:
            mock_asset = AssetMetadata(
                kind="image",
                original_path=None,
                stored_path=Path("test_output/page-001-img-01.png"),
                page_number=1,
                index=1,
            )
            mock_extract.return_value = [mock_asset]

            result = self.service.extract_images_pikepdf(
                self.test_pdf_path, self.test_output_dir
            )

            assert len(result) == 1
            assert result[0].kind == "image"
            assert result[0].page_number == 1
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @patch("pikepdf.Pdf.open")
    def test_extract_images_pikepdf_failure(self, mock_pdf_open):
        """Test image extraction failure handling."""
        mock_pdf_open.side_effect = Exception("PDF open failed")

        with pytest.raises(Exception, match="PDF open failed"):
            self.service.extract_images_pikepdf(
                self.test_pdf_path, self.test_output_dir
            )

    def test_extract_page_images_no_resources(self):
        """Test page with no image resources."""
        mock_page = {}
        result = self.service._extract_page_images(mock_page, 1, self.test_output_dir)
        assert result == []

    def test_extract_page_images_no_xobjects(self):
        """Test page with resources but no XObjects."""
        mock_page = {"/Resources": {}}
        result = self.service._extract_page_images(mock_page, 1, self.test_output_dir)
        assert result == []

    def test_extract_page_images_with_images(self):
        """Test page with image XObjects."""
        # Mock page with image XObjects
        mock_img_obj = {"/Subtype": "/Image"}
        mock_page = {"/Resources": {"/XObject": {"Im1": mock_img_obj}}}

        with patch.object(self.service, "_extract_image_object") as mock_extract:
            mock_asset = AssetMetadata(
                kind="image",
                original_path=None,
                stored_path=Path("test_output/page-001-img-01.png"),
                page_number=1,
                index=1,
            )
            mock_extract.return_value = mock_asset

            result = self.service._extract_page_images(
                mock_page, 1, self.test_output_dir
            )

            assert len(result) == 1
            assert result[0] == mock_asset
            mock_extract.assert_called_once()

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.stat")
    def test_extract_image_object_success(self, mock_stat, mock_exists):
        """Test successful image object extraction."""
        mock_exists.return_value = True
        mock_stat.return_value.st_size = 1000  # Non-zero size

        mock_img_obj = {"/Filter": "/DCTDecode"}

        with patch.object(self.service, "_save_jpeg_image") as mock_save:
            result = self.service._extract_image_object(
                mock_img_obj, 1, 1, self.test_output_dir
            )

            assert result is not None
            assert result.kind == "image"
            assert result.page_number == 1
            assert result.index == 1
            assert "page-001-img-01.png" in str(result.stored_path)
            mock_save.assert_called_once()

    @patch("pathlib.Path.exists")
    def test_extract_image_object_file_not_saved(self, mock_exists):
        """Test image object extraction when file is not saved."""
        mock_exists.return_value = False
        mock_img_obj = {"/Filter": "/DCTDecode"}

        with patch.object(self.service, "_save_jpeg_image"):
            result = self.service._extract_image_object(
                mock_img_obj, 1, 1, self.test_output_dir
            )

            assert result is None

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.stat")
    def test_extract_image_object_zero_size_file(self, mock_stat, mock_exists):
        """Test image object extraction when saved file has zero size."""
        mock_exists.return_value = True
        mock_stat.return_value.st_size = 0  # Zero size

        mock_img_obj = {"/Filter": "/DCTDecode"}

        with patch.object(self.service, "_save_jpeg_image"):
            result = self.service._extract_image_object(
                mock_img_obj, 1, 1, self.test_output_dir
            )

            assert result is None

    def test_extract_image_object_exception_handling(self):
        """Test image object extraction exception handling."""
        mock_img_obj = {"/Filter": "/DCTDecode"}

        with patch.object(
            self.service, "_save_jpeg_image", side_effect=Exception("Save failed")
        ):
            result = self.service._extract_image_object(
                mock_img_obj, 1, 1, self.test_output_dir
            )

            assert result is None

    @patch("PIL.Image.open")
    def test_save_jpeg_image(self, mock_image_open):
        """Test JPEG image saving."""
        mock_img_obj = Mock()
        mock_img_obj.read_raw_bytes.return_value = b"fake_jpeg_data"

        mock_img = Mock()
        mock_image_open.return_value.__enter__.return_value = mock_img

        output_path = Path("test.png")
        self.service._save_jpeg_image(mock_img_obj, output_path)

        mock_img_obj.read_raw_bytes.assert_called_once()
        mock_img.save.assert_called_once_with(output_path, "PNG")

    @patch("PIL.Image.frombytes")
    def test_save_flate_image_rgb(self, mock_frombytes):
        """Test FlateDecode RGB image saving."""
        # Create a MagicMock that supports dictionary access
        mock_img_obj_with_data = MagicMock()
        mock_img_obj_with_data.__getitem__.side_effect = lambda key: {
            "/Width": 100,
            "/Height": 100,
            "/ColorSpace": "/DeviceRGB",
        }[key]
        mock_img_obj_with_data.get.side_effect = lambda key, default=None: {
            "/Width": 100,
            "/Height": 100,
            "/ColorSpace": "/DeviceRGB",
        }.get(key, default)
        mock_img_obj_with_data.read_bytes.return_value = b"x" * (100 * 100 * 3)

        mock_img = Mock()
        mock_frombytes.return_value = mock_img

        output_path = Path("test.png")
        self.service._save_flate_image(mock_img_obj_with_data, output_path)

        mock_frombytes.assert_called_once_with(
            "RGB", (100, 100), b"x" * (100 * 100 * 3)
        )
        mock_img.save.assert_called_once_with(output_path, "PNG")

    @patch("PIL.Image.frombytes")
    def test_save_flate_image_grayscale(self, mock_frombytes):
        """Test FlateDecode grayscale image saving."""
        # Create a MagicMock that supports dictionary access
        mock_img_obj_with_data = MagicMock()
        mock_img_obj_with_data.__getitem__.side_effect = lambda key: {
            "/Width": 50,
            "/Height": 50,
            "/ColorSpace": "/DeviceGray",
        }[key]
        mock_img_obj_with_data.get.side_effect = lambda key, default=None: {
            "/Width": 50,
            "/Height": 50,
            "/ColorSpace": "/DeviceGray",
        }.get(key, default)
        mock_img_obj_with_data.read_bytes.return_value = b"x" * (50 * 50 * 1)

        mock_img = Mock()
        mock_frombytes.return_value = mock_img

        output_path = Path("test.png")
        self.service._save_flate_image(mock_img_obj_with_data, output_path)

        mock_frombytes.assert_called_once_with("L", (50, 50), b"x" * (50 * 50 * 1))
        mock_img.save.assert_called_once_with(output_path, "PNG")

    @patch("pikepdf.PdfImage")
    def test_save_generic_image(self, mock_pdf_image):
        """Test generic image saving."""
        mock_img_obj = Mock()
        mock_pil_img = Mock()
        mock_pdf_image.return_value.as_pil_image.return_value = mock_pil_img

        output_path = Path("test.png")
        self.service._save_generic_image(mock_img_obj, output_path)

        mock_pdf_image.assert_called_once_with(mock_img_obj)
        mock_pil_img.save.assert_called_once_with(output_path, "PNG")

    def test_link_to_manifest_no_manifest(self):
        """Test linking images when no manifest is provided."""
        images = [
            AssetMetadata(
                kind="image",
                original_path=None,
                stored_path=Path("img1.png"),
                page_number=1,
            )
        ]

        result = self.service.link_to_manifest(images, None)
        assert result == images

        result = self.service.link_to_manifest(images, {})
        assert result == images

    def test_link_to_manifest_with_figures(self):
        """Test linking images to manifest figures."""
        images = [
            AssetMetadata(
                kind="image",
                original_path=None,
                stored_path=Path("page-001-img-01.png"),
                page_number=1,
                index=1,
            ),
            AssetMetadata(
                kind="image",
                original_path=None,
                stored_path=Path("page-002-img-01.png"),
                page_number=2,
                index=1,
            ),
        ]

        manifest = {
            "figures": [
                {"page": 1, "caption": "Figure 1: X-ray image"},
                {"page": 2, "caption": "Figure 2: Blood test chart"},
            ]
        }

        result = self.service.link_to_manifest(images, manifest)

        assert len(result) == 2
        assert result[0].caption == "Figure 1: X-ray image"
        assert result[0].alt_text == "Figure 1: X-ray image"
        assert result[1].caption == "Figure 2: Blood test chart"
        assert result[1].alt_text == "Figure 2: Blood test chart"

    def test_link_to_manifest_single_figure_per_page(self):
        """Test linking when there's only one figure per page."""
        images = [
            AssetMetadata(
                kind="image",
                original_path=None,
                stored_path=Path("page-001-img-01.png"),
                page_number=1,
                index=2,  # Index doesn't match, but only one figure on page
            )
        ]

        manifest = {"figures": [{"page": 1, "caption": "Single figure on page 1"}]}

        result = self.service.link_to_manifest(images, manifest)

        assert len(result) == 1
        assert result[0].caption == "Single figure on page 1"
        assert result[0].alt_text == "Single figure on page 1"

    @patch.object(ImageExtractionService, "extract_images_pikepdf")
    @patch.object(ImageExtractionService, "link_to_manifest")
    def test_extract_and_process_success(self, mock_link, mock_extract):
        """Test complete extraction and processing workflow."""
        mock_images = [
            AssetMetadata(
                kind="image", original_path=None, stored_path=Path("img1.png")
            )
        ]
        mock_linked = [
            AssetMetadata(
                kind="image",
                original_path=None,
                stored_path=Path("img1.png"),
                caption="Test",
            )
        ]

        mock_extract.return_value = mock_images
        mock_link.return_value = mock_linked

        manifest = {"figures": []}
        result = self.service.extract_and_process(
            self.test_pdf_path, manifest, self.test_output_dir
        )

        assert result == mock_linked
        mock_extract.assert_called_once_with(self.test_pdf_path, self.test_output_dir)
        mock_link.assert_called_once_with(mock_images, manifest)

    @patch.object(ImageExtractionService, "extract_images_pikepdf")
    def test_extract_and_process_failure(self, mock_extract):
        """Test extraction and processing failure handling."""
        mock_extract.side_effect = Exception("Extraction failed")

        manifest = {"figures": []}
        result = self.service.extract_and_process(
            self.test_pdf_path, manifest, self.test_output_dir
        )

        # Should return empty list on failure
        assert result == []
