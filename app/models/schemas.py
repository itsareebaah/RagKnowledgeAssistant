from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    filename: str
    chunks_indexed: int
    message: str


class SourceChunk(BaseModel):
    text: str
    filename: str
    score: float


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]
    provider: str


class DocumentInfo(BaseModel):
    filename: str
    chunk_count: int


class StatusResponse(BaseModel):
    documents: list[DocumentInfo]
    total_chunks: int
    embedding_model: str
    llm_provider: str
