# PROJECT NotesToNotion: GLOBAL CONTEXT & ARCHITECTURE

## 1. The Mission
Build "NotesToNotion", a hyper-optimized ETL (Extract, Transform, Load) pipeline for scientific handwritten notes.
* **Input:** Raw PDF scans (University Math/Info Theory).
* **Process:** AI Vision transcription (Gemini Native).
* **Output:** Structured Notion pages with clean LaTeX.
* **UX Goal:** "The Drop Zone" - A zero-click, drag-and-drop interface.

## 2. The User (Critical Constraints)
* **Profile:** Science Student (Requires high-precision LaTeX for integrals, probability, entropy, ...).
* **Budget:** Low. Must use cost-efficient models.
* **Tolerance:** Zero tolerance for fragile code. If Notion fails, local backup is mandatory.

---

## 3. Project Status

### DONE (MVP Step 1 - The Engine)
- [x] Project initialization (`pyproject.toml`, `requirements.txt`)
- [x] Core `Engine` class with async methods
- [x] `transcribe_pdf()` - Gemini native PDF ingestion
- [x] `push_to_notion()` - Notion page creation with chunking
- [x] LaTeX parser (`$inline$` and `$$block$$` -> Notion equation blocks)
- [x] Smart text chunking (respects 2000 char limit)
- [x] Local backup system (auto-save on Notion failure)
- [x] CLI entry point (`main.py`)
- [x] Rich terminal logging

### TODO (Remaining Tasks)
- [ ] Test with real PDF files (validation)
- [ ] Handle edge cases (empty pages, corrupted PDFs)
- [ ] Add retry logic for API failures
- [ ] Implement progress bar during Gemini wait
- [ ] Create test suite (`pytest-asyncio`)

---

## 4. Architecture

```
NotesToNotion/
├── .env                  # API keys (git-ignored)
├── .env.example          # Template for API keys
├── .gitignore
├── pyproject.toml        # Project config (Python 3.12+)
├── requirements.txt      # Dependencies
├── main.py               # CLI entry point
├── backups/              # Auto-created for failed Notion pushes
└── src/
    ├── __init__.py       # Exports Engine class
    └── engine.py         # Core ETL logic
```

### Key Components

| File | Responsibility |
|------|----------------|
| `main.py` | CLI args, env loading, pipeline orchestration |
| `src/engine.py` | `Engine` class - all ETL logic |
| `Engine.transcribe_pdf()` | Upload PDF to Gemini, wait for ACTIVE, get Markdown |
| `Engine.push_to_notion()` | Convert Markdown to Notion blocks, create page |
| `Engine._parse_rich_text()` | LaTeX detection and conversion |
| `Engine._chunk_text()` | Smart splitting for 2000 char limit |

---

## 5. Data Flow / Workflow

```
┌─────────────┐     ┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
│   PDF File  │────>│  Gemini API     │────>│  Markdown    │────>│  Notion API │
│  (Input)    │     │  (Transcribe)   │     │  (+ LaTeX)   │     │  (Output)   │
└─────────────┘     └─────────────────┘     └──────────────┘     └─────────────┘
                           │                       │                    │
                           v                       v                    v
                    ┌─────────────┐         ┌───────────┐        ┌───────────┐
                    │ File Upload │         │ Chunking  │        │ Backup    │
                    │ Wait ACTIVE │         │ 2000 char │        │ on Fail   │
                    └─────────────┘         └───────────┘        └───────────┘
```

### Pipeline Steps
1. **Ingest:** `main.py` loads `.env`, validates PDF path
2. **Upload:** PDF sent to Gemini File API (MIME: `application/pdf`)
3. **Wait:** Poll file state until `ACTIVE` (timeout: 120s)
4. **Transcribe:** System prompt forces Scientific Typesetter mode
5. **Parse:** Split Markdown into Notion blocks (headings, paragraphs, equations)
6. **Chunk:** Enforce 2000 char limit per block
7. **Load:** Async push to Notion Database
8. **Backup:** On failure, save `.md` to `backups/`

---

## 6. Technical Stack

| Layer | Technology | Version | Purpose |
|-------|------------|---------|---------|
| Language | Python | 3.12+ | Asyncio native, type hints |
| AI Engine | `google-generativeai` | >=0.8.0 | Native PDF ingestion |
| Model | Gemini 2.0 Flash | - | Cost-efficient, fast |
| Integration | `notion-client` | >=2.2.0 | Async Notion API |
| Config | `python-dotenv` | >=1.0.0 | Environment management |
| Logging | `rich` | >=13.7.0 | Beautiful terminal output |
| Testing | `pytest-asyncio` | >=0.23.0 | Async test support |

### API Requirements
```
GOOGLE_API_KEY   # Gemini API access
NOTION_KEY       # Notion integration token
NOTION_DB_ID     # Target database ID
```

---

## 7. Coding Standards
* **Type Hinting:** Mandatory for all functions.
* **Error Handling:** Try/Except blocks around all API calls.
* **Logging:** Use `rich` library for beautiful, readable terminal logs.
* **Async:** All I/O operations must be async.
* **Backup:** Always save locally before considering operation complete.

---

## 8. Next Major Improvements

### Phase 2: Robustness
- [ ] **Retry Logic:** Exponential backoff for API failures
- [ ] **Progress Bar:** Visual feedback during Gemini processing
- [ ] **Batch Processing:** Handle multiple PDFs in one run
- [ ] **Better Error Messages:** Actionable feedback for common failures

### Phase 3: The Drop Zone (Frontend)
- [ ] **Web UI:** Minimalist drag-and-drop interface
- [ ] **FastAPI Backend:** REST API wrapper around Engine
- [ ] **Real-time Status:** WebSocket updates during processing
- [ ] **File Preview:** Show PDF thumbnail before processing

### Phase 4: Intelligence
- [ ] **Smart Titles:** Auto-generate page titles from content
- [ ] **Topic Detection:** Auto-tag pages (Algebra, Probability, etc.)
- [ ] **OCR Fallback:** Handle non-standard PDF formats
- [ ] **Quality Score:** Confidence rating for transcription

### Phase 5: Scale
- [ ] **Queue System:** Handle concurrent uploads
- [ ] **Caching:** Avoid re-processing identical PDFs
- [ ] **Analytics:** Track usage, success rates, common errors

---

## 9. Usage

### Installation
```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### Configuration
```bash
cp .env.example .env
# Edit .env with your API keys
```

### Run
```bash
python main.py path/to/notes.pdf
```

### Expected Output
```
╭─ NotesToNotion - PDF to Notion Pipeline ─╮
│                                          │
╰──────────────────────────────────────────╯

Step 1/2: Transcribing PDF with Gemini...
Uploading lecture_01.pdf to Gemini...
Waiting for Gemini processing...
Processing complete. Generating transcription...
Transcription complete (4523 chars)

Step 2/2: Pushing to Notion...
Creating Notion page: lecture_01
Page created: https://notion.so/...

╭─ Success! ─╮
│            │
│ Page: ...  │
╰────────────╯
```
