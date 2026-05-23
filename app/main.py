import shutil
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import PROJECT_ROOT, settings
from app.models.schemas import (
    QueryRequest,
    QueryResponse,
    SourceChunk,
    StatusResponse,
    UploadResponse,
)
from app.services.document_processor import chunk_text, extract_text
from app.services.rag_chain import _hits_to_sources, _resolve_provider, generate_answer
from app.services.vector_store import get_vector_store

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".csv"}

app = FastAPI(
    title="RAG Knowledge Assistant",
    description="Upload company docs, store embeddings, and query with contextual answers.",
    version="1.0.0",
)

static_dir = PROJECT_ROOT / "static"
static_dir.mkdir(exist_ok=True)


@app.on_event("startup")
def startup() -> None:
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.chroma_dir.mkdir(parents=True, exist_ok=True)
    get_vector_store()


@app.get("/api/health")
def health() -> dict:
    store = get_vector_store()
    return {
        "status": "ok",
        "documents": len(store.list_documents()),
        "chunks": store.total_chunks,
    }


@app.get("/api/status", response_model=StatusResponse)
def status() -> StatusResponse:
    store = get_vector_store()
    return StatusResponse(
        documents=store.list_documents(),
        total_chunks=store.total_chunks,
        embedding_model=settings.embedding_model,
        llm_provider=_resolve_provider(),
    )


@app.post("/api/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)) -> UploadResponse:
    if not file.filename:
        raise HTTPException(400, "Filename is required")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            400,
            f"Unsupported type '{suffix}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    dest = settings.upload_dir / file.filename
    with dest.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        text = extract_text(dest)
        chunks = chunk_text(text, file.filename)
        count = get_vector_store().add_chunks(chunks, file.filename)
    except Exception as exc:
        dest.unlink(missing_ok=True)
        raise HTTPException(400, f"Failed to process document: {exc}") from exc

    if count == 0:
        raise HTTPException(400, "No text could be extracted from this document.")

    return UploadResponse(
        filename=file.filename,
        chunks_indexed=count,
        message=f"Indexed {count} chunks from '{file.filename}'.",
    )


@app.delete("/api/documents/{filename}")
def delete_document(filename: str) -> dict:
    get_vector_store().delete_document(filename)
    (settings.upload_dir / filename).unlink(missing_ok=True)
    return {"message": f"Removed '{filename}' from the knowledge base."}


@app.post("/api/query", response_model=QueryResponse)
def query(request: QueryRequest) -> QueryResponse:
    store = get_vector_store()
    if store.total_chunks == 0:
        raise HTTPException(
            400,
            "Knowledge base is empty. Upload company documents before querying.",
        )

    try:
        hits = store.search(request.question)
        answer, provider = generate_answer(request.question, hits)
        return QueryResponse(
            answer=answer,
            sources=_hits_to_sources(hits),
            provider=provider,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, f"Query failed: {exc}") from exc


@app.get("/")
def index() -> FileResponse:
    return FileResponse(static_dir / "index.html")


app.mount("/static", StaticFiles(directory=static_dir), name="static")
