from pydantic import BaseModel, HttpUrl, validator
from typing import List, Optional, Dict, Any
from datetime import datetime

# Request Models

class TextProcessorRequest(BaseModel):
    text: str
    document_id: str
    user_id: str
    title: str
    text_type: str = "summary"  # summary, lecture, notes, etc.
    metadata: Optional[Dict[str, Any]] = {}
class DocumentProcessRequest(BaseModel):
    file_url: HttpUrl
    document_id: str
    user_id: str
    filename: str
    file_type: str  # 'pdf' or 'docx'
    metadata: Optional[Dict[str, Any]] = None

class QueryRequest(BaseModel):
    query: str
    user_id: str
    document_ids: Optional[List[str]] = None  # Filter by specific documents
    top_k: int = 5
    similarity_threshold: float = 0.3
    
    @validator('query')
    def query_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Query cannot be empty')
        return v.strip()
    
    @validator('top_k')
    def top_k_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('top_k must be positive')
        if v > 20:
            raise ValueError('top_k cannot exceed 20')
        return v

# Response Models
class DocumentChunk(BaseModel):
    chunk_id: str
    document_id: str
    content: str
    chunk_index: int
    metadata: Optional[Dict[str, Any]] = None

class ProcessingStatus(BaseModel):
    status: str  # 'processing', 'completed', 'failed'
    message: str
    chunks_created: Optional[int] = None
    processing_time: Optional[float] = None

class DocumentProcessResponse(BaseModel):
    success: bool
    document_id: str
    processing_status: ProcessingStatus
    chunks_created: Optional[int] = None

class RelevantChunk(BaseModel):
    chunk_id: str
    document_id: str
    content: str
    similarity_score: float
    metadata: Optional[Dict[str, Any]] = None
    filename: Optional[str] = None

class QueryResponse(BaseModel):
    success: bool
    query: str
    relevant_chunks: List[RelevantChunk]
    total_chunks_found: int
    search_time: Optional[float] = None

# Error Models
class ErrorDetail(BaseModel):
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None

class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail