# RAG Service API

A production-ready, reusable Retrieval-Augmented Generation (RAG) microservice built with FastAPI. Originally developed for a specific project need, this service has been architected as a standalone microservice that can be easily integrated into any application requiring document processing and semantic search capabilities. It uses pgvector and Supabase for efficient vector operations and is designed to be deployment-ready across different environments.

## Features

- **Document Processing**: Upload and process PDF/DOCX files
- **Semantic Search**: Vector-based similarity search across document content
- **Scalable Architecture**: Built with FastAPI and async/await patterns
- **Production Ready**: Comprehensive error handling, logging, and health checks
- **Database Integration**: Uses Supabase with pgvector for efficient vector operations

## Quick Start

### 1. Environment Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd rag-service

# Copy environment file
cp .env.example .env

# Edit .env with your Supabase credentials
```

### 2. Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### 3. Configure Supabase

Make sure you have:

- A Supabase project with pgvector extension enabled
- Database connection string
- Service role key for database operations

### 4. Run the Service

```bash
# Development mode
python -m uvicorn app.main:app --reload

# Production mode
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## API Endpoints

### Document Processing

#### Process Document

```http
POST /documents/process
Content-Type: application/json

{
  "file_url": "https://example.com/document.pdf",
  "document_id": "doc_123",
  "user_id": "user_456",
  "filename": "document.pdf",
  "file_type": "pdf",
  "metadata": {"source": "upload"}
}
```

**Response:**

```json
{
  "success": true,
  "message": "Document processing started",
  "document_id": "doc_123",
  "status": "processing",
  "estimated_completion_time": "2024-01-15T10:30:00Z"
}
```

#### Check Document Status

```http
GET /documents/status/{document_id}?user_id=user_456
```

**Response:**

```json
{
  "document_id": "doc_123",
  "user_id": "user_456",
  "status": "completed",
  "filename": "document.pdf",
  "file_type": "pdf",
  "total_chunks": 45,
  "processing_time": 12.5,
  "created_at": "2024-01-15T10:15:00Z",
  "completed_at": "2024-01-15T10:27:30Z",
  "metadata": { "source": "upload" }
}
```

#### List User Documents

```http
GET /documents/list?user_id=user_456&status=completed&limit=10&offset=0
```

**Response:**

```json
{
  "documents": [
    {
      "document_id": "doc_123",
      "filename": "document.pdf",
      "status": "completed",
      "total_chunks": 45,
      "created_at": "2024-01-15T10:15:00Z",
      "file_type": "pdf"
    }
  ],
  "total_count": 1,
  "limit": 10,
  "offset": 0
}
```

#### Delete Document

```http
DELETE /documents/{document_id}?user_id=user_456
```

**Response:**

```json
{
  "success": true,
  "message": "Document and associated chunks deleted successfully",
  "document_id": "doc_123"
}
```

### Query & Search

#### Semantic Search

```http
POST /query/search
Content-Type: application/json

{
  "query": "What is machine learning?",
  "user_id": "user_456",
  "top_k": 5,
  "similarity_threshold": 0.3,
  "document_ids": ["doc_123"]
}
```

**Response:**

```json
{
  "success": true,
  "query": "What is machine learning?",
  "relevant_chunks": [
    {
      "chunk_id": "chunk_789",
      "document_id": "doc_123",
      "content": "Machine learning is a subset of artificial intelligence...",
      "similarity_score": 0.89,
      "metadata": { "page": 5, "section": "Introduction" },
      "filename": "document.pdf"
    }
  ],
  "total_chunks_found": 5,
  "search_time": 0.156
}
```

#### Find Similar Chunks

```http
GET /query/similar/{chunk_id}?user_id=user_456&top_k=5
```

**Response:**

```json
{
  "original_chunk_id": "chunk_789",
  "original_content": "Machine learning is a subset of artificial intelligence...",
  "similar_chunks": [
    {
      "chunk_id": "chunk_790",
      "document_id": "doc_123",
      "content": "Deep learning, a branch of machine learning...",
      "similarity_score": 0.82,
      "metadata": { "page": 6 },
      "filename": "document.pdf"
    }
  ],
  "total_found": 4
}
```

#### Batch Search

```http
POST /query/batch-search
Content-Type: application/json

{
  "queries": ["machine learning", "deep learning", "neural networks"],
  "user_id": "user_456",
  "top_k": 3
}
```

**Response:**

```json
{
  "batch_results": [
    {
      "query": "machine learning",
      "relevant_chunks": [...],
      "chunks_found": 3
    }
  ],
  "total_queries": 3
}
```

#### Get Statistics

```http
GET /query/stats?user_id=user_456
```

**Response:**

```json
{
  "user_id": "user_456",
  "total_documents": 5,
  "completed_documents": 4,
  "total_chunks": 250,
  "avg_chunks_per_document": 62.5,
  "embedding_model": "text-embedding-3-small"
}
```

### Health & Monitoring

#### Health Check

```http
GET /health
```

**Response:**

```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "version": "1.0.0",
  "database_status": "connected",
  "embedding_service_status": "available"
}
```

#### Service Metrics

```http
GET /metrics
```

**Response:**

```json
{
  "total_documents_processed": 1250,
  "total_chunks_created": 75000,
  "total_searches_performed": 8500,
  "average_processing_time": 15.2,
  "average_search_time": 0.145,
  "uptime_seconds": 86400
}
```

## Data Models

### Document Processing Request

```json
{
  "file_url": "string (required)",
  "document_id": "string (required)",
  "user_id": "string (required)",
  "filename": "string (required)",
  "file_type": "string (pdf|docx)",
  "metadata": "object (optional)"
}
```

### Query Request

```json
{
  "query": "string (required)",
  "user_id": "string (required)",
  "top_k": "integer (default: 5)",
  "similarity_threshold": "float (default: 0.3)",
  "document_ids": "array[string] (optional)"
}
```

### Relevant Chunk

```json
{
  "chunk_id": "string",
  "document_id": "string",
  "content": "string",
  "similarity_score": "float",
  "metadata": "object",
  "filename": "string"
}
```

## Error Handling

All endpoints return structured error responses:

```json
{
  "detail": "Error description",
  "error_code": "DOCUMENT_NOT_FOUND",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Common Error Codes

- `DOCUMENT_NOT_FOUND` (404): Document doesn't exist or user doesn't have access
- `PROCESSING_FAILED` (500): Document processing failed
- `INVALID_FILE_TYPE` (400): Unsupported file format
- `SEARCH_FAILED` (500): Search operation failed
- `RATE_LIMIT_EXCEEDED` (429): Too many requests

## Environment Variables

Create a `.env` file with the variable specified in `.env.example`

## Database Schema

### Documents Table

```sql
CREATE TABLE documents (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    filename VARCHAR NOT NULL,
    file_type VARCHAR NOT NULL,
    status VARCHAR DEFAULT 'pending',
    total_chunks INTEGER DEFAULT 0,
    processing_time FLOAT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);
```

### Document Chunks Table

```sql
CREATE TABLE document_chunks (
    id VARCHAR PRIMARY KEY,
    document_id VARCHAR REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding VECTOR(1536),
    chunk_index INTEGER,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create vector similarity index
CREATE INDEX ON document_chunks USING ivfflat (embedding vector_cosine_ops);
```

## Deployment

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose

```yaml
version: "3.8"

services:
  rag-service:
    build: .
    ports:
      - "8000:8000"
    environment:
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_SERVICE_KEY=${SUPABASE_SERVICE_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

## Performance Considerations

- **Chunking Strategy**: Default chunk size of 1000 characters with 200 character overlap
- **Embedding Caching**: Embeddings are cached to avoid recomputation
- **Connection Pooling**: Database connections are pooled for efficiency
- **Async Processing**: All I/O operations use async/await patterns
- **Rate Limiting**: Built-in rate limiting to prevent abuse

## Monitoring & Logging

The service includes comprehensive logging and monitoring:

- **Structured Logging**: JSON-formatted logs with correlation IDs
- **Performance Metrics**: Request duration, processing times, search latency
- **Health Checks**: Database connectivity, embedding service availability
- **Error Tracking**: Detailed error logging with stack traces

## Security Features

- **Input Validation**: All inputs are validated and sanitized
- **User Isolation**: Users can only access their own documents
- **API Key Authentication**: Optional API key-based authentication
- **CORS Configuration**: Configurable CORS settings
- **File Size Limits**: Configurable maximum file sizes

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:

- Create an issue in the GitHub repository
- Check the documentation at `/docs` endpoint when running the service
- Review the API schema at `/redoc` endpoint
