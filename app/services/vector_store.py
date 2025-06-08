import logging
from typing import List, Dict, Any
import time
from app.models.database import db_manager
from app.services.embedding_service import embedding_service
from app.models.schemas import RelevantChunk

logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self):
        self.db_manager = db_manager
        self.embedding_service = embedding_service
    
    async def store_document_chunks(self, chunks_data: List[dict]) -> int:
        """
        Store document chunks with their embeddings in the vector database
        """
        try:
            if not chunks_data:
                return 0
            
            logger.info(f"Processing {len(chunks_data)} chunks for embedding storage")
            
            # Extract texts for batch embedding generation
            texts = [chunk['content'] for chunk in chunks_data]
            
            # Generate embeddings in batch
            embeddings = self.embedding_service.generate_embeddings_batch(texts)
            
            # Prepare data for database insertion
            db_chunks_data = []
            for chunk, embedding in zip(chunks_data, embeddings):
                db_chunks_data.append((
                    chunk['chunk_id'],
                    chunk['document_id'],
                    chunk['content'],
                    chunk['chunk_index'],
                    embedding,  # This will be converted to vector type by psycopg2
                    chunk.get('metadata', {})
                ))
            
            # Insert chunks into database
            self.db_manager.insert_chunks(db_chunks_data)
            
            logger.info(f"Successfully stored {len(db_chunks_data)} chunks with embeddings")
            return len(db_chunks_data)
            
        except Exception as e:
            logger.error(f"Failed to store document chunks: {e}")
            raise RuntimeError(f"Vector storage failed: {str(e)}")
    
    async def similarity_search(self, query: str, user_id: str, 
                               document_ids: List[str] = None, 
                               top_k: int = 5, 
                               similarity_threshold: float = 0.3) -> List[RelevantChunk]:
        """
        Perform similarity search against stored document chunks
        """
        try:
            start_time = time.time()
            
            # Generate embedding for the query
            query_embedding = self.embedding_service.generate_embedding(query)
            
            # Perform semantic search
            search_results = self.db_manager.semantic_search(
                query_embedding=query_embedding,
                user_id=user_id,
                document_ids=document_ids,
                top_k=top_k,
                similarity_threshold=similarity_threshold
            )
            
            search_time = time.time() - start_time
            
            # Convert results to RelevantChunk objects
            relevant_chunks = []
            for result in search_results:
                chunk = RelevantChunk(
                    chunk_id=result['chunk_id'],
                    document_id=result['document_id'],
                    content=result['content'],
                    similarity_score=float(result['similarity_score']),
                    metadata={
                        **(result.get('chunk_metadata') or {}),
                        'document_metadata': result.get('document_metadata') or {},
                        'search_time': search_time
                    },
                    filename=result.get('filename')
                )
                relevant_chunks.append(chunk)
            
            logger.info(f"Found {len(relevant_chunks)} relevant chunks in {search_time:.3f}s")
            
            return relevant_chunks
            
        except Exception as e:
            logger.error(f"Similarity search failed: {e}")
            raise RuntimeError(f"Search failed: {str(e)}")
    
    def get_document_statistics(self, document_id: str) -> Dict[str, Any]:
        """Get statistics for a processed document"""
        try:
            chunk_count = self.db_manager.get_document_chunks_count(document_id)
            
            return {
                'document_id': document_id,
                'total_chunks': chunk_count,
                'embedding_model': self.embedding_service.model_name,
                'embedding_dimension': len(self.embedding_service.generate_embedding("test"))
            }
            
        except Exception as e:
            logger.error(f"Failed to get document statistics: {e}")
            return {
                'document_id': document_id,
                'error': str(e)
            }
    
    def health_check(self) -> Dict[str, Any]:
        """Check the health of the vector store"""
        try:
            # Test database connection
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    db_healthy = cur.fetchone() is not None
            
            # Test embedding service
            test_embedding = self.embedding_service.generate_embedding("test")
            embedding_healthy = len(test_embedding) == self.embedding_service.model.get_sentence_embedding_dimension()
            
            return {
                'database_healthy': db_healthy,
                'embedding_service_healthy': embedding_healthy,
                'model_info': self.embedding_service.get_model_info()
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'database_healthy': False,
                'embedding_service_healthy': False,
                'error': str(e)
            }

# Global vector store instance
vector_store = VectorStore()