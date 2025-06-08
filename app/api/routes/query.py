from fastapi import APIRouter, HTTPException
import logging
import time
from app.models.schemas import QueryRequest, QueryResponse, ErrorResponse
from app.services.vector_store import vector_store

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/query",
    tags=["query"],
    responses={404: {"description": "Not found"}}
)

@router.post("/search", response_model=QueryResponse)
async def semantic_search(query_request: QueryRequest):
    """
    Perform semantic search across user's documents
    """
    try:
        start_time = time.time()
        
        logger.info(f"Processing search query for user {query_request.user_id}: '{query_request.query[:100]}...'")
        
        # Perform similarity search
        relevant_chunks = await vector_store.similarity_search(
            query=query_request.query,
            user_id=query_request.user_id,
            document_ids=query_request.document_ids,
            top_k=query_request.top_k,
            similarity_threshold=query_request.similarity_threshold
        )
        
        search_time = time.time() - start_time
        
        logger.info(f"Search completed in {search_time:.3f}s, found {len(relevant_chunks)} relevant chunks")
        
        return QueryResponse(
            success=True,
            query=query_request.query,
            relevant_chunks=relevant_chunks,
            total_chunks_found=len(relevant_chunks),
            search_time=search_time
        )
        
    except Exception as e:
        logger.error(f"Search query failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )

@router.get("/similar/{chunk_id}")
async def find_similar_chunks(chunk_id: str, user_id: str, top_k: int = 5):
    """
    Find chunks similar to a specific chunk
    """
    try:
        from app.models.database import db_manager
        
        # Get the chunk content and embedding
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT dc.content, dc.embedding, d.user_id
                    FROM document_chunks dc
                    JOIN documents d ON dc.document_id = d.id
                    WHERE dc.id = %s AND d.user_id = %s
                """, (chunk_id, user_id))
                
                result = cur.fetchone()
                
                if not result:
                    raise HTTPException(status_code=404, detail="Chunk not found")
                
                chunk_content = result['content']
                chunk_embedding = result['embedding']
        
        # Perform similarity search using the chunk's embedding
        search_results = db_manager.semantic_search(
            query_embedding=chunk_embedding,
            user_id=user_id,
            top_k=top_k + 1,  # +1 to account for the original chunk
            similarity_threshold=0.1
        )
        
        # Filter out the original chunk
        filtered_results = [r for r in search_results if r['chunk_id'] != chunk_id][:top_k]
        
        # Convert to RelevantChunk format
        from app.models.schemas import RelevantChunk
        similar_chunks = []
        for result in filtered_results:
            chunk = RelevantChunk(
                chunk_id=result['chunk_id'],
                document_id=result['document_id'],
                content=result['content'],
                similarity_score=float(result['similarity_score']),
                metadata=result.get('chunk_metadata') or {},
                filename=result.get('filename')
            )
            similar_chunks.append(chunk)
        
        return {
            "original_chunk_id": chunk_id,
            "original_content": chunk_content[:200] + "..." if len(chunk_content) > 200 else chunk_content,
            "similar_chunks": similar_chunks,
            "total_found": len(similar_chunks)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Similar chunks search failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Similar chunks search failed: {str(e)}"
        )

@router.post("/batch-search")
async def batch_search(queries: list[str], user_id: str, top_k: int = 3):
    """
    Perform multiple searches in batch
    """
    try:
        if len(queries) > 10:
            raise HTTPException(status_code=400, detail="Maximum 10 queries allowed in batch")
        
        results = []
        for query in queries:
            if not query.strip():
                continue
                
            relevant_chunks = await vector_store.similarity_search(
                query=query,
                user_id=user_id,
                top_k=top_k,
                similarity_threshold=0.3
            )
            
            results.append({
                "query": query,
                "relevant_chunks": relevant_chunks,
                "chunks_found": len(relevant_chunks)
            })
        
        return {
            "batch_results": results,
            "total_queries": len(results)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch search failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Batch search failed: {str(e)}"
        )

@router.get("/stats")
async def get_search_statistics(user_id: str):
    """
    Get search and document statistics for a user
    """
    try:
        from app.models.database import db_manager
        
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                # Get document and chunk counts
                cur.execute("""
                    SELECT 
                        COUNT(DISTINCT d.id) as total_documents,
                        COUNT(DISTINCT CASE WHEN d.status = 'completed' THEN d.id END) as completed_documents,
                        COUNT(dc.id) as total_chunks,
                        AVG(CASE WHEN d.status = 'completed' THEN 
                            (SELECT COUNT(*) FROM document_chunks WHERE document_id = d.id) 
                        END) as avg_chunks_per_document
                    FROM documents d
                    LEFT JOIN document_chunks dc ON d.id = dc.document_id
                    WHERE d.user_id = %s
                """, (user_id,))
                
                stats = cur.fetchone()
                
                return {
                    "user_id": user_id,
                    "total_documents": stats['total_documents'] or 0,
                    "completed_documents": stats['completed_documents'] or 0,
                    "total_chunks": stats['total_chunks'] or 0,
                    "avg_chunks_per_document": float(stats['avg_chunks_per_document'] or 0),
                    "embedding_model": vector_store.embedding_service.model_name
                }
                
    except Exception as e:
        logger.error(f"Failed to get search statistics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get statistics: {str(e)}"
        )