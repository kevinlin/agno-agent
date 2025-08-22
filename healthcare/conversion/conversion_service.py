"""PDF conversion service using OpenAI Files API and Responses API."""

import json
import logging
import re
import time
from pathlib import Path
from typing import Optional

import openai
from openai import OpenAI
from pydantic import BaseModel
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from healthcare.config.config import Config
from healthcare.images import AssetMetadata, ImageExtractionService

logger = logging.getLogger(__name__)


class Figure(BaseModel):
    """Represents a figure/image detected in the PDF."""

    page: int
    index: int
    caption: Optional[str] = None
    filename: str  # e.g., "page-003-img-01.png"


class TableRef(BaseModel):
    """Represents a table detected in the PDF."""

    page: int
    index: int
    title: Optional[str] = None
    format: str  # "markdown" | "tsv"


class ConversionResult(BaseModel):
    """Result of PDF to Markdown conversion."""

    markdown: str
    manifest: dict  # {"figures": List[Figure], "tables": List[TableRef]}
    extracted_images: list[AssetMetadata] = []  # List of extracted image metadata


class PDFConversionService:
    """Service for converting PDF files to Markdown using OpenAI APIs."""

    def __init__(self, config: Config, openai_client: Optional[OpenAI] = None):
        """Initialize the PDF conversion service.

        Args:
            config: Configuration object containing API keys and settings
            openai_client: Optional OpenAI client instance (for testing)
        """
        self.config = config
        self.client = openai_client or OpenAI(api_key=config.openai_api_key)
        self.image_service = ImageExtractionService()

        # Conversion prompt template
        self.conversion_prompt = """You are a document conversion engine. Given the attached PDF, output:

1) A faithful Markdown conversion preserving hierarchy, lists, page anchors, and tables.
   - Use ATX headings (#, ##, ###) reflecting the original structure.
   - Convert tables to Markdown tables. For very wide tables, use a fenced block with TSV inside.
   - When you encounter images/figures, insert placeholders using this format:
     ![<short descriptive caption>](images/page-<PAGE_3DIGITS>-img-<IDX_2DIGITS>.png)
     Also include a figure caption line immediately after the image.
   - Add page anchors like: <a id="page-<PAGE_3DIGITS>"></a>

2) A compact JSON manifest listing each table and figure with page numbers and suggested filenames.

Return both as a JSON object with keys: {"markdown": str, "manifest": {"figures": [...], "tables": [...]}}.
"""

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((openai.APIError, openai.APITimeoutError)),
    )
    def upload_to_openai(self, pdf_path: Path) -> str:
        """Upload PDF file to OpenAI Files API.

        Args:
            pdf_path: Path to the PDF file to upload

        Returns:
            file_id: OpenAI file ID for the uploaded PDF

        Raises:
            openai.APIError: If the upload fails after retries
            FileNotFoundError: If the PDF file doesn't exist
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        logger.info(f"Uploading PDF to OpenAI Files API: {pdf_path.name}")
        upload_start_time = time.time()

        try:
            with open(pdf_path, "rb") as f:
                uploaded_file = self.client.files.create(
                    file=f,
                    purpose="assistants",  # or appropriate purpose for responses API
                )

            upload_duration = time.time() - upload_start_time
            logger.info(
                f"Successfully uploaded PDF, file_id: {uploaded_file.id} - Upload took {upload_duration:.2f} seconds"
            )
            return uploaded_file.id

        except Exception as e:
            logger.error(f"Failed to upload PDF to OpenAI: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((openai.APIError, openai.APITimeoutError)),
    )
    def convert_pdf_to_markdown(self, file_id: str) -> ConversionResult:
        """Convert PDF to Markdown using OpenAI Responses API with File Inputs.

        Args:
            file_id: OpenAI file ID of the uploaded PDF

        Returns:
            ConversionResult containing markdown and manifest

        Raises:
            openai.APIError: If the conversion fails after retries
        """
        logger.info(f"Converting PDF to Markdown using file_id: {file_id}")
        conversion_start_time = time.time()

        try:
            # Use Responses API with File Input
            logger.info("Starting OpenAI Responses API call...")
            start_time = time.time()

            response = self.client.responses.create(
                model=self.config.openai_model,
                input=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": self.conversion_prompt},
                            {"type": "input_file", "file_id": file_id},
                        ],
                    }
                ],
                timeout=self.config.request_timeout,
            )

            api_duration = time.time() - start_time
            logger.info(
                f"OpenAI Responses API call completed in {api_duration:.2f} seconds"
            )

            # Parse the JSON response from output_text
            if not response.output_text:
                raise ValueError("OpenAI response output_text is empty or None")

            try:
                result_data = json.loads(response.output_text)
                logger.info(f"Successfully parsed JSON result")
            except json.JSONDecodeError as json_err:
                logger.error(f"JSON decode error: {json_err}")
                logger.error(
                    f"Raw output_text content: '{response.output_text[:500]}...' (first 500 chars)"
                )
                raise ValueError(
                    f"Invalid JSON response from OpenAI: {json_err}"
                ) from json_err
            conversion_result = ConversionResult(**result_data)

            total_conversion_time = time.time() - conversion_start_time
            logger.info(
                f"Successfully converted PDF to Markdown ({len(conversion_result.markdown)} chars) - "
                f"Total conversion time: {total_conversion_time:.2f} seconds"
            )

            return conversion_result

        except Exception as e:
            logger.error(f"Failed to convert PDF to Markdown: {e}")
            raise

    def save_markdown(self, markdown: str, report_dir: Path) -> Path:
        """Save converted Markdown content to file.

        Args:
            markdown: Markdown content to save
            report_dir: Directory to save the report in

        Returns:
            Path to the saved Markdown file
        """
        # Ensure report directory exists
        report_dir.mkdir(parents=True, exist_ok=True)

        markdown_path = report_dir / "report.md"

        try:
            markdown_path.write_text(markdown, encoding="utf-8")
            logger.info(f"Saved Markdown to: {markdown_path}")
            return markdown_path

        except Exception as e:
            logger.error(f"Failed to save Markdown to {markdown_path}: {e}")
            raise

    async def process_pdf(self, pdf_path: Path, report_dir: Path) -> ConversionResult:
        """Process a PDF file through the complete conversion pipeline.

        Args:
            pdf_path: Path to the PDF file to process
            report_dir: Directory to save the converted content

        Returns:
            ConversionResult containing markdown, manifest, and extracted images

        Raises:
            Exception: If any step in the pipeline fails
        """
        logger.info(f"Starting PDF processing pipeline for: {pdf_path.name}")

        try:
            # Step 1: Upload PDF to OpenAI
            file_id = self.upload_to_openai(pdf_path)

            # Step 2: Convert to Markdown
            conversion_result = self.convert_pdf_to_markdown(file_id)

            # Step 3: Save Markdown to disk
            markdown_path = self.save_markdown(conversion_result.markdown, report_dir)

            # Step 4: Extract images from PDF
            images_dir = report_dir / "images"
            try:
                extracted_images = self.image_service.extract_and_process(
                    pdf_path, conversion_result.manifest, images_dir
                )
                conversion_result.extracted_images = extracted_images
                logger.info(f"Successfully extracted {len(extracted_images)} images")
            except Exception as image_error:
                logger.warning(
                    f"Image extraction failed, continuing without images: {image_error}"
                )
                conversion_result.extracted_images = []

            logger.info(
                f"Successfully completed PDF processing pipeline with {len(conversion_result.extracted_images)} images"
            )
            return conversion_result

        except Exception as e:
            logger.error(f"PDF processing pipeline failed: {e}")
            raise

    def cleanup_openai_file(self, file_id: str) -> None:
        """Clean up uploaded file from OpenAI (optional, for privacy).

        Args:
            file_id: OpenAI file ID to delete
        """
        try:
            self.client.files.delete(file_id)
            logger.info(f"Deleted OpenAI file: {file_id}")
        except Exception as e:
            logger.warning(f"Failed to delete OpenAI file {file_id}: {e}")
