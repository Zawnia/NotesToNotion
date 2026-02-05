"""Pytest configuration and fixtures for NotesToNotion tests."""

import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from google.genai import types
from notion_client import AsyncClient as NotionClient

from src.engine import Engine


@pytest.fixture
def mock_google_api_key() -> str:
    """Mock Google API key."""
    return "test_google_api_key"


@pytest.fixture
def mock_notion_key() -> str:
    """Mock Notion API key."""
    return "test_notion_key"


@pytest.fixture
def mock_notion_db_id() -> str:
    """Mock Notion database ID."""
    return "test_notion_db_id"


@pytest.fixture
def engine(mock_google_api_key: str, mock_notion_key: str, mock_notion_db_id: str) -> Engine:
    """Create a test Engine instance."""
    return Engine(
        google_api_key=mock_google_api_key,
        notion_key=mock_notion_key,
        notion_db_id=mock_notion_db_id,
    )


@pytest.fixture
def sample_markdown() -> str:
    """Sample markdown with LaTeX for testing."""
    return """# Cours de Mathématiques

## Introduction

Voici la formule d'Einstein: $E = mc^2$

## Équations

L'intégrale suivante est importante:

$$
\\int_{0}^{\\infty} e^{-x^2} dx = \\frac{\\sqrt{\\pi}}{2}
$$

## Liste

- Point 1 avec $\\alpha$
- Point 2 avec $\\beta$

1. Première étape
2. Deuxième étape
"""


@pytest.fixture
def fixtures_dir() -> Path:
    """Path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def create_test_pdf(fixtures_dir: Path):
    """Factory fixture to create test PDFs."""

    def _create_pdf(filename: str, size_bytes: int = 1024) -> Path:
        """Create a dummy PDF file for testing.

        Args:
            filename: Name of the PDF file.
            size_bytes: Size of the file in bytes.

        Returns:
            Path to the created PDF.
        """
        fixtures_dir.mkdir(exist_ok=True)
        pdf_path = fixtures_dir / filename

        # Create a minimal valid PDF structure
        pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /Resources 4 0 R /MediaBox [0 0 612 792] /Contents 5 0 R >>
endobj
4 0 obj
<< /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >>
endobj
5 0 obj
<< /Length 44 >>
stream
BT
/F1 12 Tf
100 700 Td
(Test PDF) Tj
ET
endstream
endobj
xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000214 00000 n
0000000293 00000 n
trailer
<< /Size 6 /Root 1 0 R >>
startxref
385
%%EOF
"""

        # Pad to requested size if needed
        if len(pdf_content) < size_bytes:
            pdf_content += b"\n" * (size_bytes - len(pdf_content))
        else:
            pdf_content = pdf_content[:size_bytes]

        pdf_path.write_bytes(pdf_content)
        return pdf_path

    return _create_pdf


@pytest.fixture
def mock_gemini_file() -> types.File:
    """Mock Gemini uploaded file."""
    mock_file = MagicMock(spec=types.File)
    mock_file.name = "test_file_123"
    mock_file.state = "ACTIVE"
    return mock_file


@pytest.fixture
def mock_gemini_response() -> MagicMock:
    """Mock Gemini API response."""
    mock_response = MagicMock()
    mock_response.text = "# Test transcription\n\nThis is a test."
    return mock_response


@pytest.fixture
def mock_notion_page() -> dict:
    """Mock Notion page response."""
    return {
        "id": "test_page_id",
        "url": "https://notion.so/test_page_id",
        "properties": {},
    }


@pytest.fixture(autouse=True)
def cleanup_backups():
    """Clean up backup files after each test."""
    yield
    backup_dir = Path("backups")
    if backup_dir.exists():
        for file in backup_dir.glob("*.md"):
            file.unlink()
