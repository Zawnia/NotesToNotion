"""CLI entry point for NotesToNotion."""

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

from src.engine import Engine
from src.exceptions import PDFValidationError, TranscriptionError, NotionError

console = Console()


def load_config() -> tuple[str, str, str]:
    """Load configuration from environment.

    Returns:
        Tuple of (google_api_key, notion_key, notion_db_id).

    Raises:
        SystemExit: If required env vars are missing.
    """
    load_dotenv()

    google_api_key = os.getenv("GOOGLE_API_KEY")
    notion_key = os.getenv("NOTION_KEY")
    notion_db_id = os.getenv("NOTION_DB_ID")

    missing = []
    if not google_api_key:
        missing.append("GOOGLE_API_KEY")
    if not notion_key:
        missing.append("NOTION_KEY")
    if not notion_db_id:
        missing.append("NOTION_DB_ID")

    if missing:
        console.print(
            f"[red]Missing environment variables:[/red] {', '.join(missing)}"
        )
        console.print("Copy .env.example to .env and fill in your API keys.")
        sys.exit(1)

    return google_api_key, notion_key, notion_db_id


async def run_pipeline(pdf_path: str) -> None:
    """Execute the full PDF to Notion pipeline.

    Args:
        pdf_path: Path to the PDF file.
    """
    console.print(
        Panel.fit(
            "[bold blue]NotesToNotion[/bold blue] - PDF to Notion Pipeline",
            border_style="blue",
        )
    )

    google_api_key, notion_key, notion_db_id = load_config()

    engine = Engine(
        google_api_key=google_api_key,
        notion_key=notion_key,
        notion_db_id=notion_db_id,
    )

    pdf_name = Path(pdf_path).stem

    try:
        console.print("\n[bold]Step 1/2:[/bold] Transcribing PDF with Gemini...")
        markdown = await engine.transcribe_pdf(pdf_path)
        console.print(f"[green]Transcription complete[/green] ({len(markdown)} chars)\n")

        console.print("[bold]Step 2/2:[/bold] Pushing to Notion...")
        page_url = await engine.push_to_notion(markdown, page_title=pdf_name)

        console.print(
            Panel.fit(
                f"[bold green]Success![/bold green]\n\nPage: {page_url}",
                border_style="green",
            )
        )

    except FileNotFoundError as e:
        console.print(f"\n[red]Error:[/red] {e}")
        console.print("\n[yellow]Suggestion:[/yellow] Check that the file path is correct")
        console.print(f"  • Make sure the file exists: {pdf_path}")
        console.print(f"  • Check for typos in the path")
        sys.exit(1)

    except PDFValidationError as e:
        console.print(f"\n[red]Validation Error:[/red] {e}")
        console.print("\n[yellow]Suggestions:[/yellow]")
        if "too large" in str(e).lower():
            console.print("  • Compress the PDF using online tools")
            console.print("  • Split the PDF into smaller files")
        elif "must be a pdf" in str(e).lower():
            console.print("  • Ensure the file has a .pdf extension")
            console.print("  • Convert the file to PDF format")
        sys.exit(1)

    except TimeoutError as e:
        console.print(f"\n[red]Timeout:[/red] {e}")
        console.print("\n[yellow]Suggestions:[/yellow]")
        console.print("  • Try with a smaller PDF file")
        console.print("  • Check your internet connection")
        console.print("  • Wait a moment and try again (Gemini may be busy)")
        sys.exit(1)

    except TranscriptionError as e:
        console.print(f"\n[red]Transcription Error:[/red] {e}")
        console.print("\n[yellow]Suggestions:[/yellow]")
        console.print("  • Check if the PDF contains readable text")
        console.print("  • Ensure the PDF is not corrupted")
        console.print("  • Try re-scanning the document with better quality")
        sys.exit(1)

    except NotionError as e:
        console.print(f"\n[red]Notion Error:[/red] {e}")
        console.print("\n[yellow]Suggestions:[/yellow]")
        console.print("  • Check your Notion API key is valid")
        console.print("  • Verify the database ID is correct")
        console.print("  • Ensure the integration has access to the database")
        console.print(f"\n[dim]Check backups/ folder for saved transcription[/dim]")
        sys.exit(1)

    except RuntimeError as e:
        error_msg = str(e)
        console.print(f"\n[red]Runtime Error:[/red] {error_msg}")

        if "processing failed" in error_msg.lower():
            console.print("\n[yellow]Suggestions:[/yellow]")
            console.print("  • The PDF may be corrupted or in an unsupported format")
            console.print("  • Try re-saving or re-exporting the PDF")
            console.print("  • Contact support if the issue persists")

        sys.exit(1)

    except Exception as e:
        console.print(f"\n[red]Unexpected Error:[/red] {e}")
        console.print("\n[dim]Check backups/ folder for any saved transcription[/dim]")
        console.print("[dim]Run with --verbose flag for more details (coming soon)[/dim]")
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    if len(sys.argv) < 2:
        console.print("[yellow]Usage:[/yellow] python main.py <pdf_path>")
        console.print("\nExample: python main.py notes/lecture_01.pdf")
        sys.exit(1)

    pdf_path = sys.argv[1]
    asyncio.run(run_pipeline(pdf_path))


if __name__ == "__main__":
    main()
