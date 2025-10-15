# FastAPI PDF Merger

FastAPI PDF Merger is a web application and API for combining multiple PDF documents and JPG/PNG images into a single PDF, or converting PDF pages to images. It provides a drag-and-drop browser UI, a flexible `/pdf-merger/merge` endpoint that supports per-file page ranges and layout options, a `/pdf-merger/pdf-to-images` endpoint for converting PDFs to high-quality JPG images, and configurable upload limits suitable for self-hosted deployments.

## Features

- **Responsive web UI** served with Jinja2 templates (`/pdf-merger/`) for interactive merging of PDFs and JPG/PNG images.
- **PDF Merge API** `POST /pdf-merger/merge` that accepts multiple PDF, JPG, or PNG files, per-file page ranges, layout preferences (paper size, orientation, rotation, fit mode), and selectable processing engines (`pypdf` or `pikepdf`).
- **PDF to Images Conversion** `POST /pdf-merger/pdf-to-images` converts PDF pages to high-quality JPG images and packages them as a ZIP file. Supports DPI and quality adjustments, along with page range selection.
- **Upload safeguards** with configurable maximum total payload size and per-request validation of PDF extensions, empty files, encryption status, and malformed JSON inputs.
- **API key protection** enforced via `PDF_MERGER_API_KEY` (or compatible aliases) for API endpoints.
- **Health checks** through `/health` for integration with monitoring systems.
- **Concurrency control** using an AnyIO capacity limiter to avoid CPU spikes when merging or converting large documents.
- **Internationalization** supports English and Korean UI with automatic selection based on Accept-Language headers.

## Getting Started

### Requirements

- Python 3.11+
- System packages required by [PyPDF](https://pypdf.readthedocs.io/), [PyMuPDF](https://pymupdf.readthedocs.io/), and optionally [pikepdf](https://pikepdf.readthedocs.io/).

Install Python dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Configuration

Configuration is provided via environment variables (all are optional unless noted):

| Variable | Description | Default |
| --- | --- | --- |
| `PDF_MERGER_API_KEY` | API key required by API endpoints. Aliases: `API_KEY`. | _None_ (disables key requirement) |
| `PDF_MERGER_MAX_TOTAL_UPLOAD_MB` | Maximum combined upload size per request. Aliases: `MAX_MB`. | `200` |
| `PDF_MERGE_MAX_PARALLEL` | Maximum number of concurrent background merge/conversion workers. Aliases: `MERGE_MAX_PARALLEL`. | _Unlimited_ |

You can also place these in a `.env` file in the project root.

### Running the Server

Launch the FastAPI application locally with Uvicorn:

```bash
uvicorn app.main:app --reload
```

By default the UI is available at <http://127.0.0.1:8000/pdf-merger/>, the API endpoints at `/pdf-merger/merge` (merge) and `/pdf-merger/pdf-to-images` (convert), and the health check at `/health`.

## API Usage

### `POST /pdf-merger/merge`

Merges PDF and image files into a single PDF.

- **files**: one or more PDF, JPG, or PNG files (multipart form field `files`). Files cannot be encrypted or empty.
- **ranges**: (optional) JSON list of page range strings corresponding to each file (e.g., `["1-3,5",""]`).
- **options**: (optional) JSON list of per-file layout objects supporting `paper_size`, `orientation`, `fit_mode`, and `rotation` (via `rotate90`, `rotate180`, `rotate270`).
- **output_name**: (optional) Desired filename for the merged PDF (`merged.pdf` by default).
- **engine**: (optional) Processing backend (`pypdf` by default or `pikepdf` when installed).

The endpoint returns a streaming response containing the merged PDF. Errors are reported with clear HTTP status codes when validation fails.

### `POST /pdf-merger/pdf-to-images`

Converts PDF pages to JPG images and returns them as a ZIP file.

- **file**: single PDF file to convert (multipart form field `file`).
- **page_range**: (optional) Page range specification (e.g., `"1-3,5"`). Leave empty to convert all pages.
- **dpi**: (optional) Image resolution (72-600). Default is `200`.
- **quality**: (optional) JPG quality (1-100). Default is `85`.

The endpoint returns a streaming response containing a ZIP file with the converted JPG images.

## Development

- Static assets live in `app/static/` and templates in `app/templates/`.
- Business logic for merging lives in `app/services/pdf_merger.py`, conversion logic in `app/services/pdf_to_images.py`.
- API routes are organized under `app/api/routes/`.
- Internationalization strings are managed in `app/utils/i18n.py`.

Run type checks or tests as needed by your workflow. (No automated test suite is bundled.)

## License

This project is licensed under the [GNU Affero General Public License v3.0 (AGPLv3)](https://www.gnu.org/licenses/agpl-3.0.en.html). Any deployments must make the corresponding source available to network users as required by the license.

