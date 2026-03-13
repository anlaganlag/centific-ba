# Docling Serve API Documentation

**Base URL:** `https://docling-serve.nicemoss-edd0d815.eastus.azurecontainerapps.io`

**Version:** 1.14.0 (Docling 2.75.0)

**Authentication:** None required — the API is publicly accessible.

---

## Quick Start

Convert a PDF to Markdown:

```bash
curl -X POST https://docling-serve.nicemoss-edd0d815.eastus.azurecontainerapps.io/v1/convert/file \
  -F "files=@document.pdf" \
  -F 'options={"to_formats":["md"]}' \
  -H "Accept: application/json"
```

Convert a URL to Markdown:

```bash
curl -X POST https://docling-serve.nicemoss-edd0d815.eastus.azurecontainerapps.io/v1/convert/source \
  -H "Content-Type: application/json" \
  -d '{
    "sources": ["https://example.com/document.pdf"],
    "to_formats": ["md"]
  }'
```

---

## Endpoints

### Health & Info

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check — returns `{"status": "ok"}` |
| GET | `/version` | Returns version info for all components |
| GET | `/openapi-3.0.json` | Full OpenAPI 3.0 specification |

---

### Document Conversion

These endpoints convert documents (PDF, DOCX, PPTX, images, HTML, etc.) into structured output formats (Markdown, JSON, HTML, text).

#### POST `/v1/convert/file` — Convert uploaded file (sync)

Upload one or more files and get the conversion result immediately.

**Request:** `multipart/form-data`

| Field | Type | Description |
|-------|------|-------------|
| `files` | file(s) | One or more files to convert |
| `options` | JSON string | Conversion options (see Options below) |

**Example:**
```bash
curl -X POST .../v1/convert/file \
  -F "files=@report.pdf" \
  -F "files=@notes.docx" \
  -F 'options={"to_formats":["md","json"],"do_ocr":true}'
```

**Response:** `ConvertDocumentResponse`
```json
{
  "documents": [
    {
      "filename": "report.pdf",
      "md": "# Report Title\n\nContent here...",
      "json": { ... },
      "status": "success",
      "num_pages": 12,
      "processing_time": 3.45
    }
  ]
}
```

---

#### POST `/v1/convert/source` — Convert from URL (sync)

Convert documents from URLs without uploading files.

**Request:** `application/json`

```json
{
  "sources": ["https://example.com/report.pdf"],
  "to_formats": ["md"],
  "do_ocr": true
}
```

---

#### POST `/v1/convert/file/async` — Convert file (async)

Same as `/v1/convert/file` but returns a task ID immediately. Use for large files.

**Response:**
```json
{
  "task_id": "abc-123-def",
  "status": "pending"
}
```

Then poll with `GET /v1/status/poll/{task_id}` and retrieve with `GET /v1/result/{task_id}`.

---

#### POST `/v1/convert/source/async` — Convert URL (async)

Same as `/v1/convert/source` but returns a task ID.

---

### Document Chunking

These endpoints convert documents AND split them into chunks suitable for embedding/RAG pipelines. Two chunking strategies are available.

#### Hybrid Chunker

Combines semantic and token-based chunking. Best for RAG with embedding models.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/chunk/hybrid/file` | Upload file → convert + chunk (sync) |
| POST | `/v1/chunk/hybrid/source` | URL → convert + chunk (sync) |
| POST | `/v1/chunk/hybrid/file/async` | Upload file → async task |
| POST | `/v1/chunk/hybrid/source/async` | URL → async task |

**Example:**
```bash
curl -X POST .../v1/chunk/hybrid/file \
  -F "files=@report.pdf" \
  -F 'options={"to_formats":["md"],"chunking_max_tokens":512,"chunking_tokenizer":"sentence-transformers/all-MiniLM-L6-v2"}'
```

**Response:** `ChunkDocumentResponse`
```json
{
  "chunks": [
    {
      "filename": "report.pdf",
      "chunk_index": 0,
      "text": "## Introduction\n\nThis report covers...",
      "num_tokens": 128,
      "headings": ["Introduction"],
      "page_numbers": [1],
      "metadata": null
    },
    {
      "filename": "report.pdf",
      "chunk_index": 1,
      "text": "## Methodology\n\nWe used...",
      "num_tokens": 256,
      "headings": ["Methodology"],
      "page_numbers": [2, 3],
      "metadata": null
    }
  ],
  "documents": [...],
  "processing_time": 5.12
}
```

#### Hierarchical Chunker

Preserves document hierarchy (headings, sections). Best when you need structured chunks that respect document outline.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/chunk/hierarchical/file` | Upload file → convert + chunk (sync) |
| POST | `/v1/chunk/hierarchical/source` | URL → convert + chunk (sync) |
| POST | `/v1/chunk/hierarchical/file/async` | Upload file → async task |
| POST | `/v1/chunk/hierarchical/source/async` | URL → async task |

Same request/response format as hybrid chunker.

---

### Async Task Management

For any `/async` endpoint, you get back a `task_id`. Use these endpoints to track and retrieve results.

#### GET `/v1/status/poll/{task_id}` — Check task status

| Parameter | Type | Description |
|-----------|------|-------------|
| `task_id` | string (path) | Task identifier from async endpoint |
| `wait` | number (query) | Seconds to long-poll before returning (default: 0) |

**Example:**
```bash
# Instant check
curl .../v1/status/poll/abc-123-def

# Long-poll (wait up to 30 seconds for completion)
curl ".../v1/status/poll/abc-123-def?wait=30"
```

**Response:**
```json
{
  "task_id": "abc-123-def",
  "status": "completed"
}
```

Status values: `pending`, `running`, `completed`, `failed`

---

#### GET `/v1/result/{task_id}` — Get task result

Returns the same response as the sync version of the endpoint.

```bash
curl .../v1/result/abc-123-def
```

---

### Maintenance

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/v1/clear/converters` | Clear converter instances from memory |
| GET | `/v1/clear/results` | Clear cached results (default: older than 1 hour) |
| GET | `/v1/memory/stats` | Memory usage statistics |
| GET | `/v1/memory/counts` | Count of objects in memory |

**Clear old results:**
```bash
# Clear results older than 30 minutes (1800 seconds)
curl ".../v1/clear/results?older_then=1800"
```

---

## Conversion Options

These options can be passed as `options` JSON in file uploads, or as body fields for source endpoints.

### Output Formats

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `to_formats` | string[] | `["md"]` | Output formats: `md`, `json`, `html`, `text`, `doctags` |
| `image_export_mode` | string | `"embedded"` | `"placeholder"`, `"embedded"`, or `"referenced"` |

### OCR Settings

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `do_ocr` | bool | `true` | Enable OCR for scanned documents |
| `force_ocr` | bool | `false` | Force OCR even on text-based PDFs |
| `ocr_engine` | string | `"easyocr"` | Engine: `easyocr`, `tesseract`, `tesserocr`, `rapidocr`, `ocrmac` |

### PDF Settings

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `pdf_backend` | string | `"docling_parse"` | PDF parser backend |
| `table_mode` | string | `"accurate"` | Table extraction: `"fast"` or `"accurate"` |
| `page_range` | [int, int] | `[1, max]` | Page range to process |

### Advanced Features

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `do_picture_description` | bool | `false` | Generate descriptions for images |
| `do_chart_extraction` | bool | `false` | Extract data from charts |
| `do_code_enrichment` | bool | `false` | Enrich code blocks |
| `do_formula_enrichment` | bool | `false` | Enrich mathematical formulas |
| `pipeline` | string | `"standard"` | Processing pipeline to use |
| `document_timeout` | number | `604800` | Timeout per document (seconds) |

### Chunking Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `chunking_max_tokens` | int/null | `null` | Max tokens per chunk (null = auto) |
| `chunking_tokenizer` | string | `"sentence-transformers/all-MiniLM-L6-v2"` | HuggingFace tokenizer model |
| `chunking_merge_peers` | bool | `true` | Merge small peer chunks |
| `chunking_use_markdown_tables` | bool | `false` | Keep tables as markdown in chunks |
| `chunking_include_raw_text` | bool | `false` | Include raw text alongside formatted |

---

## Supported Input Formats

PDF, DOCX, PPTX, XLSX, HTML, images (PNG, JPG, TIFF, BMP), AsciiDoc, Markdown, CSV, and more.

---

## Usage from Python

```python
import httpx

BASE = "https://docling-serve.nicemoss-edd0d815.eastus.azurecontainerapps.io"

# Sync file conversion
with open("report.pdf", "rb") as f:
    response = httpx.post(
        f"{BASE}/v1/convert/file",
        files={"files": ("report.pdf", f, "application/pdf")},
        data={"options": '{"to_formats": ["md"]}'},
    )
result = response.json()
markdown = result["documents"][0]["md"]

# Async conversion with polling
with open("large_report.pdf", "rb") as f:
    task = httpx.post(
        f"{BASE}/v1/convert/file/async",
        files={"files": ("large_report.pdf", f, "application/pdf")},
        data={"options": '{"to_formats": ["md"]}'},
    ).json()

task_id = task["task_id"]

# Poll until done
import time
while True:
    status = httpx.get(f"{BASE}/v1/status/poll/{task_id}?wait=5").json()
    if status["status"] == "completed":
        break
    time.sleep(1)

# Get result
result = httpx.get(f"{BASE}/v1/result/{task_id}").json()
```

---

## Usage from JavaScript/TypeScript

```typescript
const BASE = "https://docling-serve.nicemoss-edd0d815.eastus.azurecontainerapps.io";

// File conversion
const formData = new FormData();
formData.append("files", file);
formData.append("options", JSON.stringify({ to_formats: ["md"] }));

const response = await fetch(`${BASE}/v1/convert/file`, {
  method: "POST",
  body: formData,
});
const result = await response.json();
const markdown = result.documents[0].md;
```

---

## Error Responses

| Status | Description |
|--------|-------------|
| 200 | Success |
| 422 | Validation error — check request body/parameters |
| 500 | Internal server error — document processing failed |

Validation errors return:
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "sources"],
      "msg": "Field required"
    }
  ]
}
```
