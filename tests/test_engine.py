"""Unit tests for Engine class."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.engine import Engine, BlockType, SemanticBlock


class TestMarkdownParsing:
    """Tests for markdown to Notion block conversion."""

    def test_parse_rich_text_inline_latex(self, engine: Engine):
        """Test inline LaTeX parsing with $...$"""
        text = "La formule $E = mc^2$ est célèbre"
        result = engine._parse_rich_text(text)

        assert len(result) == 3
        assert result[0]["type"] == "text"
        assert result[0]["text"]["content"] == "La formule "
        assert result[1]["type"] == "equation"
        assert result[1]["equation"]["expression"] == "E = mc^2"
        assert result[2]["type"] == "text"
        assert result[2]["text"]["content"] == " est célèbre"

    def test_parse_rich_text_block_latex(self, engine: Engine):
        """Test block LaTeX parsing with $$...$$"""
        text = "Voici: $$\\int_0^1 x dx$$ une intégrale"
        result = engine._parse_rich_text(text)

        assert len(result) == 3
        assert result[1]["type"] == "equation"
        assert result[1]["equation"]["expression"] == "\\int_0^1 x dx"

    def test_parse_rich_text_preserves_newlines(self, engine: Engine):
        """Test that newlines are preserved in rich text."""
        text = "Line 1\nLine 2\nLine 3"
        result = engine._parse_rich_text(text)

        # Should have: text, newline, text, newline, text
        assert len(result) == 5
        assert result[0]["text"]["content"] == "Line 1"
        assert result[1]["text"]["content"] == "\n"
        assert result[2]["text"]["content"] == "Line 2"

    def test_parse_semantic_blocks_headings(self, engine: Engine):
        """Test parsing markdown headings."""
        markdown = "# Heading 1\n## Heading 2\n### Heading 3"
        blocks = engine._parse_semantic_blocks(markdown)

        assert len(blocks) == 3
        assert blocks[0].type == BlockType.HEADING_1
        assert blocks[0].content == "Heading 1"
        assert blocks[1].type == BlockType.HEADING_2
        assert blocks[1].content == "Heading 2"
        assert blocks[2].type == BlockType.HEADING_3
        assert blocks[2].content == "Heading 3"

    def test_parse_semantic_blocks_equation(self, engine: Engine):
        """Test parsing block equations."""
        markdown = "Text before\n$$\n\\int x dx\n$$\nText after"
        blocks = engine._parse_semantic_blocks(markdown)

        assert len(blocks) == 3
        assert blocks[1].type == BlockType.EQUATION
        assert blocks[1].content == "\\int x dx"

    def test_parse_semantic_blocks_lists(self, engine: Engine):
        """Test parsing bulleted and numbered lists."""
        markdown = "- Item 1\n- Item 2\n\n1. First\n2. Second"
        blocks = engine._parse_semantic_blocks(markdown)

        assert len(blocks) == 4
        assert blocks[0].type == BlockType.BULLETED_LIST_ITEM
        assert blocks[0].content == "Item 1"
        assert blocks[2].type == BlockType.NUMBERED_LIST_ITEM
        assert blocks[2].content == "First"

    def test_markdown_to_notion_blocks(self, engine: Engine, sample_markdown: str):
        """Test full markdown to Notion blocks conversion."""
        blocks = engine._markdown_to_notion_blocks(sample_markdown)

        assert len(blocks) > 0
        assert blocks[0]["type"] == "heading_1"

        # Check that equations are present
        equation_blocks = [b for b in blocks if b["type"] == "equation"]
        assert len(equation_blocks) > 0


class TestTextChunking:
    """Tests for text chunking logic."""

    def test_chunk_text_respects_limit(self, engine: Engine):
        """Test that chunking respects 2000 char limit."""
        long_text = "x" * 5000
        chunks = engine._chunk_text(long_text)

        for chunk in chunks:
            assert len(chunk) <= engine.NOTION_BLOCK_LIMIT

        # Verify all text is preserved
        assert "".join(chunks) == long_text.rstrip()

    def test_chunk_text_no_chunking_needed(self, engine: Engine):
        """Test that short text is not chunked."""
        short_text = "Short text"
        chunks = engine._chunk_text(short_text)

        assert len(chunks) == 1
        assert chunks[0] == short_text

    def test_force_chunk_splits_correctly(self, engine: Engine):
        """Test force chunking for very long text."""
        # Text without spaces that exceeds limit
        long_text = "a" * 3000
        chunks = engine._force_chunk(long_text)

        for chunk in chunks:
            assert len(chunk) <= engine.NOTION_BLOCK_LIMIT


class TestPDFTranscription:
    """Tests for PDF transcription functionality."""

    @pytest.mark.asyncio
    async def test_transcribe_pdf_file_not_found(self, engine: Engine):
        """Test that FileNotFoundError is raised for non-existent PDF."""
        with pytest.raises(FileNotFoundError, match="PDF not found"):
            await engine.transcribe_pdf("nonexistent.pdf")

    @pytest.mark.asyncio
    async def test_wait_for_file_active_timeout(self, engine: Engine):
        """Test timeout when file doesn't become active."""
        mock_file = MagicMock()
        mock_file.name = "test_file"

        # Mock the get method to always return PROCESSING state
        with patch.object(engine.genai.aio.files, 'get') as mock_get:
            mock_get.return_value = MagicMock(state="PROCESSING")

            with pytest.raises(TimeoutError, match="did not become active"):
                await engine._wait_for_file_active(mock_file, timeout=1, poll_interval=0.1)

    @pytest.mark.asyncio
    async def test_wait_for_file_active_failed_state(self, engine: Engine):
        """Test error when file processing fails."""
        mock_file = MagicMock()
        mock_file.name = "test_file"

        with patch.object(engine.genai.aio.files, 'get') as mock_get:
            mock_get.return_value = MagicMock(state="FAILED")

            with pytest.raises(RuntimeError, match="File processing failed"):
                await engine._wait_for_file_active(mock_file)


class TestNotionIntegration:
    """Tests for Notion API integration."""

    @pytest.mark.asyncio
    async def test_push_to_notion_creates_page(self, engine: Engine, sample_markdown: str):
        """Test that push_to_notion creates a Notion page."""
        mock_page = {
            "id": "test_page_id",
            "url": "https://notion.so/test_page_id",
        }

        with patch.object(engine.notion.pages, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_page

            page_url = await engine.push_to_notion(sample_markdown, "Test Page")

            assert page_url == "https://notion.so/test_page_id"
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_backup_created_on_notion_failure(self, engine: Engine, sample_markdown: str):
        """Test that backup is created when Notion API fails."""
        with patch.object(engine.notion.pages, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = Exception("API Error")

            with pytest.raises(Exception, match="API Error"):
                await engine.push_to_notion(sample_markdown, "test_page")

            # Check backup was created
            backup_path = Path("backups/test_page.md")
            assert backup_path.exists()
            content = backup_path.read_text(encoding="utf-8")
            assert content == sample_markdown


class TestRetryLogic:
    """Tests for retry with exponential backoff."""

    @pytest.mark.asyncio
    async def test_retry_succeeds_on_first_attempt(self):
        """Test that retry logic succeeds immediately if no error."""
        from src.engine import retry_with_backoff

        async def success_func():
            return "success"

        result = await retry_with_backoff(success_func)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_retry_eventually_succeeds(self):
        """Test that retry logic retries and eventually succeeds."""
        from src.engine import retry_with_backoff

        attempt_count = 0

        async def flaky_func():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise Exception("429 rate limit")
            return "success"

        result = await retry_with_backoff(
            flaky_func,
            max_retries=5,
            base_delay=0.01,
        )

        assert result == "success"
        assert attempt_count == 3

    @pytest.mark.asyncio
    async def test_retry_fails_after_max_retries(self):
        """Test that retry logic fails after max retries."""
        from src.engine import retry_with_backoff

        async def always_fail():
            raise Exception("429 rate limit")

        with pytest.raises(Exception, match="429 rate limit"):
            await retry_with_backoff(
                always_fail,
                max_retries=2,
                base_delay=0.01,
            )


class TestSemanticBlock:
    """Tests for SemanticBlock dataclass."""

    def test_semantic_block_creation(self):
        """Test creating a SemanticBlock."""
        block = SemanticBlock(BlockType.HEADING_1, "Test Heading")

        assert block.type == BlockType.HEADING_1
        assert block.content == "Test Heading"
        assert block.level is None

    def test_semantic_block_with_level(self):
        """Test creating a SemanticBlock with level."""
        block = SemanticBlock(BlockType.HEADING_2, "Test", level=2)

        assert block.level == 2
