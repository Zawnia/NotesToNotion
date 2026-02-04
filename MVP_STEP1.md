# TASK: STEP 1 - THE ENGINE (backend mvp)

## Objective
Build the core Python logic. No UI yet. Just a CLI that proves we can turn a PDF into a Notion page reliably.

## Required Actions for Claude Code

### 1. Environment Setup
* Initialize a python project
* Install dependencies: `google-generativeai notion-client python-dotenv rich pytest-asyncio`.

### 2. Core Logic Implementation (`src/engine.py`)
Create a class `Engine` with two main async methods:

* `async def transcribe_pdf(self, pdf_path: str) -> str`:
    * Upload file to Gemini (File API).
    * Wait for processing state `ACTIVE`.
    * Prompt Gemini to act as a **Scientific Typesetter**.
    * *Constraint:* Output must be raw Markdown. Math must be in Latex `$ inline $` or `$$block$$`.

* `async def push_to_notion(self, markdown: str, page_title: str)`:
    * Create a new page in the target Database.
    * **CRITICAL:** Implement a chunking algorithm. Notion API blocks have a 2000 char limit. Split the text intelligently (by paragraphs) before sending.
    * If a chunk fails (400 Error), fallback to wrapping it in a Code Block so data is not lost.

### 3. The CLI Entry Point (`main.py`)
* Create a simple script that:
    1.  Loads `.env` (GOOGLE_API_KEY, NOTION_KEY, NOTION_DB_ID).
    2.  Takes a PDF path as argument.
    3.  Runs the pipeline.
    4.  Uses `rich` to show a progress bar during the "Gemini Processing" phase.

## Validation Criteria
* A new page appears in Notion.
* LaTeX formulas render correctly in Notion (not just raw text).
* Execution time < 15s for a 5-page PDF.

GENERATE THE CODEBASE NOW.