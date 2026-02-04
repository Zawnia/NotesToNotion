"""Core ETL Engine for NotesToNotion."""

import asyncio
import time
from pathlib import Path

import google.generativeai as genai
from google.generativeai.types import File
from notion_client import AsyncClient as NotionClient
from rich.console import Console

console = Console()

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

    NOTION_BLOCK_LIMIT = 2000

    def __init__(
        self,
        google_api_key: str,
        notion_key: str,
        notion_db_id: str,
    ) -> None:
        """Initialize the engine with API credentials.

        Args:
            google_api_key: Google Gemini API key.
            notion_key: Notion integration token.
            notion_db_id: Target Notion database ID.
        """
        genai.configure(api_key=google_api_key)
        self.model = genai.GenerativeModel("gemini-2.0-flash")
        self.notion = NotionClient(auth=notion_key)
        self.notion_db_id = notion_db_id

    async def transcribe_pdf(self, pdf_path: str) -> str:
        """Transcribe a PDF file using Gemini's native PDF ingestion.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            Markdown transcription with LaTeX math.

        Raises:
            FileNotFoundError: If PDF file doesn't exist.
            RuntimeError: If Gemini processing fails.
        """
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        console.print(f"[blue]Uploading[/blue] {path.name} to Gemini...")

        uploaded_file = await asyncio.to_thread(
            genai.upload_file,
            path,
            mime_type="application/pdf",
        )

        console.print("[yellow]Waiting for Gemini processing...[/yellow]")
        file_state = await self._wait_for_file_active(uploaded_file)

        if file_state.state.name != "ACTIVE":
            raise RuntimeError(f"File processing failed: {file_state.state.name}")

        console.print("[green]Processing complete.[/green] Generating transcription...")

        response = await asyncio.to_thread(
            self.model.generate_content,
            [SYSTEM_PROMPT, file_state],
        )

        await asyncio.to_thread(genai.delete_file, uploaded_file.name)

        return response.text

    async def _wait_for_file_active(
        self,
        uploaded_file: File,
        timeout: int = 120,
        poll_interval: float = 2.0,
    ) -> File:
        """Poll until file is in ACTIVE state.

        Args:
            uploaded_file: The uploaded file object.
            timeout: Maximum wait time in seconds.
            poll_interval: Time between status checks.

        Returns:
            File object in ACTIVE state.

        Raises:
            TimeoutError: If file doesn't become active within timeout.
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            file_state = await asyncio.to_thread(
                genai.get_file,
                uploaded_file.name,
            )

            if file_state.state.name == "ACTIVE":
                return file_state

            if file_state.state.name == "FAILED":
                raise RuntimeError("File processing failed")

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
            page = await self.notion.pages.create(
                parent={"database_id": self.notion_db_id},
                properties={"Name": {"title": [{"text": {"content": page_title}}]}},
                children=blocks,
            )

            page_url = page.get("url", "")
            console.print(f"[green]Page created:[/green] {page_url}")
            return page_url

        except Exception as e:
            console.print(f"[red]Notion API error:[/red] {e}")
            await self._save_local_backup(markdown, page_title)
            raise

    def _markdown_to_notion_blocks(self, markdown: str) -> list[dict]:
        """Convert markdown to Notion block format with chunking.

        Args:
            markdown: Raw markdown text.

        Returns:
            List of Notion block objects.
        """
        blocks: list[dict] = []
        lines = markdown.split("\n")
        current_paragraph: list[str] = []

        for line in lines:
            if line.startswith("# "):
                if current_paragraph:
                    blocks.extend(self._create_text_blocks("\n".join(current_paragraph)))
                    current_paragraph = []
                blocks.append(self._create_heading_block(line[2:], level=1))

            elif line.startswith("## "):
                if current_paragraph:
                    blocks.extend(self._create_text_blocks("\n".join(current_paragraph)))
                    current_paragraph = []
                blocks.append(self._create_heading_block(line[3:], level=2))

            elif line.startswith("### "):
                if current_paragraph:
                    blocks.extend(self._create_text_blocks("\n".join(current_paragraph)))
                    current_paragraph = []
                blocks.append(self._create_heading_block(line[4:], level=3))

            elif line.startswith("$$") or line.strip() == "$$":
                if current_paragraph:
                    blocks.extend(self._create_text_blocks("\n".join(current_paragraph)))
                    current_paragraph = []
                current_paragraph.append(line)

            elif line.strip() == "":
                if current_paragraph:
                    blocks.extend(self._create_text_blocks("\n".join(current_paragraph)))
                    current_paragraph = []

            else:
                current_paragraph.append(line)

        if current_paragraph:
            blocks.extend(self._create_text_blocks("\n".join(current_paragraph)))

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
        """Parse text with LaTeX into Notion rich_text format.

        Notion supports equations via the 'equation' type in rich_text.

        Args:
            text: Text potentially containing LaTeX.

        Returns:
            List of rich_text objects.
        """
        rich_text: list[dict] = []
        i = 0

        while i < len(text):
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
        backup_dir = Path("backups")
        backup_dir.mkdir(exist_ok=True)

        safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in page_title)
        backup_path = backup_dir / f"{safe_title}.md"

        backup_path.write_text(markdown, encoding="utf-8")
        console.print(f"[yellow]Backup saved:[/yellow] {backup_path}")
