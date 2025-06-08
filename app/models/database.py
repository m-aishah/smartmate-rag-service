import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
import logging
from app.config import settings
import json

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.connection_string = settings.database_url
        # print(settings.database_url)

        
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = None
        try:
            conn = psycopg2.connect(
                self.connection_string,
                cursor_factory=RealDictCursor
            )
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def initialize_tables(self):
        """Create necessary tables and extensions"""
        create_tables_sql = """
        -- Enable pgvector extension
        CREATE EXTENSION IF NOT EXISTS vector;
        
        -- Create documents table
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            file_type TEXT NOT NULL,
            file_url TEXT NOT NULL,
            status TEXT DEFAULT 'processing',
            metadata JSONB DEFAULT '{{}}',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        -- Create document_chunks table
        CREATE TABLE IF NOT EXISTS document_chunks (
            id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            content TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            embedding vector({embedding_dim}),
            metadata JSONB DEFAULT '{{}}',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            UNIQUE(document_id, chunk_index)
        );
        
        -- Create indexes for better performance
        CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents(user_id);
        CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
        CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON document_chunks(document_id);
        CREATE INDEX IF NOT EXISTS idx_chunks_embedding_cosine ON document_chunks 
        USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
        """.format(embedding_dim=settings.embedding_dimension)
        
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(create_tables_sql)
                logger.info("Database tables initialized successfully")
    
    def insert_document(self, document_id: str, user_id: str, filename: str, 
                    file_type: str, file_url: str, metadata: dict = None):
        """Insert a new document record"""
        sql = """
        INSERT INTO documents (id, user_id, filename, file_type, file_url, metadata)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            status = 'processing',
            updated_at = NOW()
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                metadata_json = json.dumps(metadata) if metadata else None
                cur.execute(sql, (document_id, user_id, filename, file_type, file_url, metadata_json))
        
    def update_document_status(self, document_id: str, status: str):
        """Update document processing status"""
        sql = """
        UPDATE documents 
        SET status = %s, updated_at = NOW()
        WHERE id = %s
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (status, document_id))
    
    import json

    def insert_chunks(self, chunks_data: list):
        """Batch insert document chunks with embeddings"""
        sql = """
        INSERT INTO document_chunks (id, document_id, content, chunk_index, embedding, metadata)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (document_id, chunk_index) DO UPDATE SET
            content = EXCLUDED.content,
            embedding = EXCLUDED.embedding,
            metadata = EXCLUDED.metadata
        """
        # Prepare data, convert metadata dict to JSON string
        prepared_data = []
        for chunk in chunks_data:
            # chunk is expected to be a tuple or list of values corresponding to columns
            # Assuming chunk[-1] is metadata dict, adjust if needed
            *other_fields, metadata = chunk
            metadata_json = json.dumps(metadata) if metadata else None
            prepared_data.append((*other_fields, metadata_json))
        
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.executemany(sql, prepared_data)
    
    def semantic_search(self, query_embedding: list, user_id: str, 
                       document_ids: list = None, top_k: int = 5, 
                       similarity_threshold: float = 0.3):
        """Perform semantic search using cosine similarity"""
        
        # Base query
        base_sql = """
        SELECT 
            dc.id as chunk_id,
            dc.document_id,
            dc.content,
            dc.metadata as chunk_metadata,
            d.filename,
            d.metadata as document_metadata,
            1 - (dc.embedding <=> %s::vector) as similarity_score
        FROM document_chunks dc
        JOIN documents d ON dc.document_id = d.id
        WHERE d.user_id = %s 
        AND d.status = 'completed'
        AND 1 - (dc.embedding <=> %s::vector) >= %s
        """
        
        params = [query_embedding, user_id, query_embedding, similarity_threshold]
        
        # Add document filter if specified
        if document_ids:
            placeholders = ','.join(['%s'] * len(document_ids))
            base_sql += f" AND d.id IN ({placeholders})"
            params.extend(document_ids)
        
        # Order by similarity and limit results
        base_sql += " ORDER BY similarity_score DESC LIMIT %s"
        params.append(top_k)
        
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(base_sql, params)
                return cur.fetchall()
    
    def get_document_chunks_count(self, document_id: str):
        """Get the number of chunks for a document"""
        sql = "SELECT COUNT(*) as count FROM document_chunks WHERE document_id = %s"
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (document_id,))
                result = cur.fetchone()
                return result['count'] if result else 0

# Global database manager instance
db_manager = DatabaseManager()