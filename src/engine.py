"""Core ETL Engine for NotesToNotion."""

import asyncio
import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TypeVar

from google import genai
from google.genai import types
from notion_client import AsyncClient as NotionClient
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

from src.config import AppConfig
from src.exceptions import PDFValidationError, TranscriptionError

console = Console()

T = TypeVar("T")


class BlockType(Enum):
    """Semantic block types for markdown parsing."""

    HEADING_1 = "heading_1"
    HEADING_2 = "heading_2"
    HEADING_3 = "heading_3"
    PARAGRAPH = "paragraph"
    EQUATION = "equation"
    BULLETED_LIST_ITEM = "bulleted_list_item"
    NUMBERED_LIST_ITEM = "numbered_list_item"


@dataclass
class SemanticBlock:
    """Represents a semantic block from markdown."""

    type: BlockType
    content: str
    level: int | None = None  # For headings only


async def retry_with_backoff(
    func: Callable[[], T],
    max_retries: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    retryable_errors: tuple = (Exception,),
) -> T:
    """Execute a function with exponential backoff retry.

    Args:
        func: The function to execute (sync or async).
        max_retries: Maximum number of retry attempts.
        base_delay: Initial delay in seconds.
        max_delay: Maximum delay between retries.
        retryable_errors: Tuple of exception types to retry on.

    Returns:
        The result of the function.

    Raises:
        The last exception if all retries fail.
    """
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            result = func()
            if asyncio.iscoroutine(result):
                return await result
            return result

        except retryable_errors as e:
            last_exception = e
            error_msg = str(e).lower()

            is_rate_limit = any(
                x in error_msg for x in ["429", "rate", "quota", "exhausted", "limit"]
            )

            if attempt == max_retries:
                raise

            if is_rate_limit:
                delay = min(base_delay * (2 ** attempt) + random.uniform(0, 1), max_delay)
                console.print(
                    f"[yellow]Rate limit hit. Retry {attempt + 1}/{max_retries} "
                    f"in {delay:.1f}s...[/yellow]"
                )
                await asyncio.sleep(delay)
            else:
                raise

    raise last_exception  # type: ignore

SYSTEM_PROMPT = """You are a Scientific Typesetter specialized in transcribing handwritten mathematical notes.

Your task is to convert the handwritten content from this PDF into clean, well-structured Markdown.

RULES:
1. Output ONLY raw Markdown - no explanations, no preamble.
2. Preserve the logical structure: headings, lists, paragraphs.
3. ALL mathematical expressions must use LaTeX:
   - Inline math: $expression$
   - Block math: $$expression$$
4. Be precise with mathematical notation: integrals, summations, limits, matrices, etc.
5. If text is unclear, make your best interpretation - do not leave blanks.
6. Preserve any diagrams or figures as [Figure: description].

Output the transcription now:"""


class Engine:
    """Main ETL engine for PDF to Notion pipeline."""

    def __init__(
        self,
        google_api_key: str,
        notion_key: str,
        notion_db_id: str,
        config: AppConfig | None = None,
    ) -> None:
        """Initialize the engine with API credentials.

        Args:
            google_api_key: Google Gemini API key.
            notion_key: Notion integration token.
            notion_db_id: Target Notion database ID.
            config: Optional configuration. Uses defaults if not provided.
        """
        self.config = config or AppConfig.default()
        self.genai = genai.Client(api_key=google_api_key)
        self.model_name = self.config.gemini.model
        self.notion = NotionClient(auth=notion_key)
        self.notion_db_id = notion_db_id

        # Cached property for backward compatibility
        self.NOTION_BLOCK_LIMIT = self.config.notion.block_limit

    async def transcribe_pdf(self, pdf_path: str) -> str:
        """Transcribe a PDF file using Gemini's native PDF ingestion.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            Markdown transcription with LaTeX math.

        Raises:
            FileNotFoundError: If PDF file doesn't exist.
            PDFValidationError: If PDF file is invalid (wrong format, too large, etc.).
            TranscriptionError: If transcription fails or returns empty result.
            RuntimeError: If Gemini processing fails.
        """
        path = Path(pdf_path)

        # Validation 1: File existence
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        # Validation 2: File extension
        if path.suffix.lower() != ".pdf":
            raise PDFValidationError(
                f"File must be a PDF, got: {path.suffix}\n"
                f"Please provide a valid PDF file."
            )

        # Validation 3: File size
        file_size_mb = path.stat().st_size / (1024 * 1024)
        max_size_mb = self.config.gemini.max_file_size_mb

        if file_size_mb > max_size_mb:
            raise PDFValidationError(
                f"PDF too large: {file_size_mb:.1f}MB (max {max_size_mb}MB)\n"
                f"Please compress or split the PDF before uploading."
            )

        # Warning for suspiciously small files
        if file_size_mb < 0.001:  # < 1KB
            console.print(
                f"[yellow]Warning:[/yellow] File is very small ({file_size_mb*1024:.1f}KB). "
                f"It may be empty or corrupted."
            )

        console.print(f"[blue]Uploading[/blue] {path.name} to Gemini...")

        uploaded_file = await retry_with_backoff(
            lambda: self.genai.aio.files.upload(
                file=path,
                config=types.UploadFileConfig(mime_type="application/pdf"),
            )
        )

        console.print("[yellow]Waiting for Gemini processing...[/yellow]")
        file_state = await self._wait_for_file_active(uploaded_file)

        if file_state.state != "ACTIVE":
            raise RuntimeError(f"File processing failed: {file_state.state}")

        console.print("[green]Processing complete.[/green] Generating transcription...")

        response = await retry_with_backoff(
            lambda: self.genai.aio.models.generate_content(
                model=self.model_name,
                contents=[file_state, "Transcribe this document."],
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                ),
            )
        )

        await self.genai.aio.files.delete(name=uploaded_file.name)

        # Validation 4: Check transcription is not empty
        transcription = response.text
        if not transcription or len(transcription.strip()) < 10:
            console.print(
                "[yellow]Warning:[/yellow] Transcription is very short or empty. "
                "The PDF may be empty, corrupted, or contain only images."
            )

        return transcription

    async def _wait_for_file_active(
        self,
        uploaded_file: types.File,
        timeout: int | None = None,
        poll_interval: float | None = None,
    ) -> types.File:
        """Poll until file is in ACTIVE state with progress bar.

        Args:
            uploaded_file: The uploaded file object.
            timeout: Maximum wait time in seconds. Uses config default if None.
            poll_interval: Time between status checks. Uses config default if None.

        Returns:
            File object in ACTIVE state.

        Raises:
            TimeoutError: If file doesn't become active within timeout.
            RuntimeError: If file processing fails.
        """
        timeout = timeout or self.config.gemini.upload_timeout
        poll_interval = poll_interval or self.config.gemini.poll_interval
        start_time = time.time()

        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]Processing PDF..."),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("", total=timeout)

            while time.time() - start_time < timeout:
                file_state = await self.genai.aio.files.get(name=uploaded_file.name)

                if file_state.state == "ACTIVE":
                    progress.update(task, completed=timeout)
                    return file_state

                if file_state.state == "FAILED":
                    raise RuntimeError("File processing failed")

                elapsed = time.time() - start_time
                progress.update(task, completed=elapsed)
                await asyncio.sleep(poll_interval)

        raise TimeoutError(f"File did not become active within {timeout}s")

    async def push_to_notion(self, markdown: str, page_title: str) -> str:
        """Push markdown content to Notion as a new page.

        Args:
            markdown: The markdown content to push.
            page_title: Title for the new Notion page.

        Returns:
            URL of the created Notion page.

        Raises:
            Exception: If Notion API fails.
        """
        console.print(f"[blue]Creating Notion page:[/blue] {page_title}")

        blocks = self._markdown_to_notion_blocks(markdown)

        try:
            page = await retry_with_backoff(
                lambda: self.notion.pages.create(
                    parent={"database_id": self.notion_db_id},
                    properties={"Name": {"title": [{"text": {"content": page_title}}]}},
                    children=blocks,
                )
            )

            page_url = page.get("url", "")
            console.print(f"[green]Page created:[/green] {page_url}")
            return page_url

        except Exception as e:
            console.print(f"[red]Notion API error:[/red] {e}")
            await self._save_local_backup(markdown, page_title)
            raise

    def _markdown_to_notion_blocks(self, markdown: str) -> list[dict]:
        """Convert markdown to Notion blocks via semantic parsing.

        Uses a two-phase approach:
        1. Parse markdown into semantic blocks (state machine)
        2. Convert semantic blocks to Notion format with chunking

        Args:
            markdown: Raw markdown text.

        Returns:
            List of Notion block objects.
        """
        # Phase 1: Tokenize into semantic blocks
        semantic_blocks = self._parse_semantic_blocks(markdown)

        # Phase 2: Convert to Notion format with chunking
        notion_blocks = []
        for block in semantic_blocks:
            notion_blocks.extend(self._semantic_to_notion(block))

        return notion_blocks

    def _parse_semantic_blocks(self, markdown: str) -> list[SemanticBlock]:
        """Parse markdown into semantic blocks using state machine.

        Args:
            markdown: Raw markdown text.

        Returns:
            List of semantic blocks.
        """
        blocks: list[SemanticBlock] = []
        lines = markdown.split("\n")
        i = 0

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # State 1: Headings (single-line)
            if stripped.startswith("### "):
                blocks.append(SemanticBlock(BlockType.HEADING_3, stripped[4:]))
                i += 1
            elif stripped.startswith("## "):
                blocks.append(SemanticBlock(BlockType.HEADING_2, stripped[3:]))
                i += 1
            elif stripped.startswith("# "):
                blocks.append(SemanticBlock(BlockType.HEADING_1, stripped[2:]))
                i += 1

            # State 2: Block equations (multi-line accumulation)
            elif stripped == "$$":
                equation_lines = []
                i += 1
                while i < len(lines) and lines[i].strip() != "$$":
                    equation_lines.append(lines[i])
                    i += 1
                i += 1  # Skip closing $$
                equation = "\n".join(equation_lines).strip()
                blocks.append(SemanticBlock(BlockType.EQUATION, equation))

            # State 3: Bulleted lists
            elif stripped.startswith("- ") or stripped.startswith("* "):
                blocks.append(SemanticBlock(BlockType.BULLETED_LIST_ITEM, stripped[2:]))
                i += 1

            # State 4: Numbered lists
            elif stripped and stripped[0].isdigit() and ". " in stripped:
                content = stripped.split(". ", 1)[1] if ". " in stripped else stripped
                blocks.append(SemanticBlock(BlockType.NUMBERED_LIST_ITEM, content))
                i += 1

            # State 5: Empty lines (skip)
            elif stripped == "":
                i += 1

            # State 6: Paragraphs (accumulate until empty line or special line)
            else:
                para_lines = []
                while (
                    i < len(lines)
                    and lines[i].strip() != ""
                    and not self._is_special_line(lines[i])
                ):
                    para_lines.append(lines[i].strip())
                    i += 1
                if para_lines:
                    blocks.append(SemanticBlock(BlockType.PARAGRAPH, "\n".join(para_lines)))

        return blocks

    def _is_special_line(self, line: str) -> bool:
        """Check if line starts a special block (heading, equation, list).

        Args:
            line: Line to check.

        Returns:
            True if line starts a special block.
        """
        stripped = line.strip()
        return (
            stripped.startswith("#")
            or stripped == "$$"
            or stripped.startswith("- ")
            or stripped.startswith("* ")
            or (len(stripped) > 0 and stripped[0].isdigit() and ". " in stripped)
        )

    def _semantic_to_notion(self, block: SemanticBlock) -> list[dict]:
        """Convert semantic block to Notion blocks with chunking.

        Args:
            block: Semantic block to convert.

        Returns:
            List of Notion block objects.
        """
        if block.type == BlockType.EQUATION:
            # Equation blocks are standalone (no rich_text parsing)
            return [
                {
                    "object": "block",
                    "type": "equation",
                    "equation": {"expression": block.content[: self.NOTION_BLOCK_LIMIT]},
                }
            ]

        elif block.type == BlockType.BULLETED_LIST_ITEM:
            return self._create_list_blocks(block.content, "bulleted_list_item")

        elif block.type == BlockType.NUMBERED_LIST_ITEM:
            return self._create_list_blocks(block.content, "numbered_list_item")

        elif block.type in [BlockType.HEADING_1, BlockType.HEADING_2, BlockType.HEADING_3]:
            level = int(block.type.value.split("_")[1])
            return [self._create_heading_block(block.content, level)]

        else:  # PARAGRAPH
            return self._create_text_blocks(block.content)

    def _create_list_blocks(self, text: str, list_type: str) -> list[dict]:
        """Create list item blocks with chunking support.

        Args:
            text: List item text content.
            list_type: Type of list ('bulleted_list_item' or 'numbered_list_item').

        Returns:
            List of Notion list item blocks.
        """
        blocks: list[dict] = []
        chunks = self._chunk_text(text)

        for chunk in chunks:
            blocks.append(
                {
                    "object": "block",
                    "type": list_type,
                    list_type: {"rich_text": self._parse_rich_text(chunk)},
                }
            )

        return blocks

    def _create_heading_block(self, text: str, level: int) -> dict:
        """Create a Notion heading block.

        Args:
            text: Heading text.
            level: Heading level (1, 2, or 3).

        Returns:
            Notion heading block object.
        """
        heading_type = f"heading_{level}"
        return {
            "object": "block",
            "type": heading_type,
            heading_type: {
                "rich_text": self._parse_rich_text(text[: self.NOTION_BLOCK_LIMIT]),
            },
        }

    def _create_text_blocks(self, text: str) -> list[dict]:
        """Create paragraph blocks, chunking if necessary.

        Args:
            text: Text content.

        Returns:
            List of Notion paragraph blocks.
        """
        blocks: list[dict] = []
        chunks = self._chunk_text(text)

        for chunk in chunks:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": self._parse_rich_text(chunk),
                },
            })

        return blocks

    def _chunk_text(self, text: str) -> list[str]:
        """Split text into chunks respecting the 2000 char limit.

        Splits by paragraphs first, then by sentences if needed.

        Args:
            text: Text to chunk.

        Returns:
            List of text chunks.
        """
        if len(text) <= self.NOTION_BLOCK_LIMIT:
            return [text]

        chunks: list[str] = []
        paragraphs = text.split("\n\n")

        current_chunk = ""
        for para in paragraphs:
            if len(current_chunk) + len(para) + 2 <= self.NOTION_BLOCK_LIMIT:
                current_chunk += ("\n\n" if current_chunk else "") + para
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                if len(para) <= self.NOTION_BLOCK_LIMIT:
                    current_chunk = para
                else:
                    for sub_chunk in self._force_chunk(para):
                        chunks.append(sub_chunk)
                    current_chunk = ""

        if current_chunk:
            chunks.append(current_chunk)

        return chunks if chunks else [text[: self.NOTION_BLOCK_LIMIT]]

    def _force_chunk(self, text: str) -> list[str]:
        """Force split text that exceeds limit.

        Args:
            text: Long text to split.

        Returns:
            List of chunks.
        """
        chunks: list[str] = []
        while len(text) > self.NOTION_BLOCK_LIMIT:
            split_point = text.rfind(" ", 0, self.NOTION_BLOCK_LIMIT)
            if split_point == -1:
                split_point = self.NOTION_BLOCK_LIMIT
            chunks.append(text[:split_point])
            text = text[split_point:].lstrip()
        if text:
            chunks.append(text)
        return chunks

    def _parse_rich_text(self, text: str) -> list[dict]:
        """Parse text with LaTeX and newlines into Notion rich_text format.

        Notion supports equations via the 'equation' type in rich_text.
        Preserves line breaks by splitting on newlines.

        Args:
            text: Text potentially containing LaTeX and newlines.

        Returns:
            List of rich_text objects.
        """
        # Split by newlines to preserve line breaks
        lines = text.split("\n")
        rich_text: list[dict] = []

        for idx, line in enumerate(lines):
            # Parse each line for LaTeX (existing logic)
            rich_text.extend(self._parse_line_for_latex(line))

            # Add line break between lines (except last)
            if idx < len(lines) - 1:
                rich_text.append({"type": "text", "text": {"content": "\n"}})

        return rich_text if rich_text else [{"type": "text", "text": {"content": text}}]

    def _parse_line_for_latex(self, text: str) -> list[dict]:
        """Parse single line for inline LaTeX equations ($ and $$).

        Args:
            text: Single line of text potentially containing LaTeX.

        Returns:
            List of rich_text objects for this line.
        """
        rich_text: list[dict] = []
        i = 0

        while i < len(text):
            # Detect block equations $$...$$
            if text[i : i + 2] == "$$":
                end = text.find("$$", i + 2)
                if end != -1:
                    equation = text[i + 2 : end].strip()
                    rich_text.append({
                        "type": "equation",
                        "equation": {"expression": equation},
                    })
                    i = end + 2
                    continue

            # Detect inline equations $...$
            if text[i] == "$" and (i + 1 < len(text) and text[i + 1] != "$"):
                end = text.find("$", i + 1)
                if end != -1:
                    equation = text[i + 1 : end]
                    rich_text.append({
                        "type": "equation",
                        "equation": {"expression": equation},
                    })
                    i = end + 1
                    continue

            # Plain text
            next_dollar = text.find("$", i)
            if next_dollar == -1:
                next_dollar = len(text)

            if next_dollar > i:
                plain_text = text[i:next_dollar]
                if plain_text:
                    rich_text.append({
                        "type": "text",
                        "text": {"content": plain_text},
                    })
            i = next_dollar if next_dollar > i else i + 1

        return rich_text if rich_text else [{"type": "text", "text": {"content": text}}]

    async def _save_local_backup(self, markdown: str, page_title: str) -> None:
        """Save markdown to local file as backup.

        Args:
            markdown: Content to save.
            page_title: Used for filename.
        """
        backup_dir = Path(self.config.backup_dir)
        backup_dir.mkdir(exist_ok=True)

        safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in page_title)
        backup_path = backup_dir / f"{safe_title}.md"

        backup_path.write_text(markdown, encoding="utf-8")
        console.print(f"[yellow]Backup saved:[/yellow] {backup_path}")
