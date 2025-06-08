from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any
import logging
import time
import uuid
from app.models.schemas import (
    DocumentProcessRequest, 
    DocumentProcessResponse, 
    ProcessingStatus, 
    ErrorResponse
)
from app.models.database import db_manager
from app.services.document_processor import document_processor
from app.services.vector_store import vector_store

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/documents",
    tags=["documents"],
    responses={404: {"description": "Not found"}}
)

async def process_document_background(document_request: DocumentProcessRequest):
    """Background task to process document"""
    try:
        logger.info(f"Starting background processing for document {document_request.document_id}")
        
        # Process the document
        full_text, chunks_data = await document_processor.process_document(
            file_url=str(document_request.file_url),
            file_type=document_request.file_type,
            document_id=document_request.document_id
        )
        
        # Store chunks with embeddings
        chunks_stored = await vector_store.store_document_chunks(chunks_data)
        
        # Update document status to completed
        db_manager.update_document_status(document_request.document_id, "completed")
        
        logger.info(f"Successfully processed document {document_request.document_id} with {chunks_stored} chunks")
        
    except Exception as e:
        logger.error(f"Background processing failed for document {document_request.document_id}: {e}")
        # Update document status to failed
        try:
            db_manager.update_document_status(document_request.document_id, "failed")
        except Exception as db_error:
            logger.error(f"Failed to update document status: {db_error}")

@router.post("/process", response_model=DocumentProcessResponse)
async def process_document(
    document_request: DocumentProcessRequest,
    background_tasks: BackgroundTasks
):
    """
    Process a document by downloading, extracting text, chunking, and storing embeddings
    """
    try:
        # Insert document record
        db_manager.insert_document(
            document_id=document_request.document_id,
            user_id=document_request.user_id,
            filename=document_request.filename,
            file_type=document_request.file_type,
            file_url=str(document_request.file_url),
            metadata=document_request.metadata
        )
        
        # Add background task for processing
        background_tasks.add_task(process_document_background, document_request)
        
        return DocumentProcessResponse(
            success=True,
            document_id=document_request.document_id,
            processing_status=ProcessingStatus(
                status="processing",
                message="Document processing started in background"
            )
        )
        
    except Exception as e:
        logger.error(f"Failed to initiate document processing: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process document: {str(e)}"
        )

@router.get("/status/{document_id}")
async def get_document_status(document_id: str, user_id: str):
    """Get the processing status of a document"""
    try:
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT d.status, d.filename, d.file_type, d.created_at, d.updated_at,
                           COUNT(dc.id) as chunk_count
                    FROM documents d
                    LEFT JOIN document_chunks dc ON d.id = dc.document_id
                    WHERE d.id = %s AND d.user_id = %s
                    GROUP BY d.id, d.status, d.filename, d.file_type, d.created_at, d.updated_at
                """, (document_id, user_id))
                
                result = cur.fetchone()
                
                if not result:
                    raise HTTPException(status_code=404, detail="Document not found")
                
                return {
                    "document_id": document_id,
                    "status": result['status'],
                    "filename": result['filename'],
                    "file_type": result['file_type'],
                    "chunk_count": result['chunk_count'],
                    "created_at": result['created_at'],
                    "updated_at": result['updated_at']
                }
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get document status: {str(e)}"
        )

@router.get("/list")
async def list_user_documents(user_id: str, status: str = None):
    """List all documents for a user"""
    try:
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                base_query = """
                    SELECT d.id, d.filename, d.file_type, d.status, d.created_at, d.updated_at,
                           COUNT(dc.id) as chunk_count
                    FROM documents d
                    LEFT JOIN document_chunks dc ON d.id = dc.document_id
                    WHERE d.user_id = %s
                """
                
                params = [user_id]
                
                if status:
                    base_query += " AND d.status = %s"
                    params.append(status)
                
                base_query += """
                    GROUP BY d.id, d.filename, d.file_type, d.status, d.created_at, d.updated_at
                    ORDER BY d.created_at DESC
                """
                
                cur.execute(base_query, params)
                documents = cur.fetchall()
                
                return {
                    "documents": [dict(doc) for doc in documents],
                    "total_count": len(documents)
                }
                
    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list documents: {str(e)}"
        )

@router.delete("/{document_id}")
async def delete_document(document_id: str, user_id: str):
    """Delete a document and all its chunks"""
    try:
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                # Check if document exists and belongs to user
                cur.execute(
                    "SELECT id FROM documents WHERE id = %s AND user_id = %s",
                    (document_id, user_id)
                )
                
                if not cur.fetchone():
                    raise HTTPException(status_code=404, detail="Document not found")
                
                # Delete document (chunks will be deleted due to CASCADE)
                cur.execute(
                    "DELETE FROM documents WHERE id = %s AND user_id = %s",
                    (document_id, user_id)
                )
                
                return {"message": "Document deleted successfully"}
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete document: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete document: {str(e)}"
        )