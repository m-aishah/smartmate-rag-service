import re
from typing import List
import logging

logger = logging.getLogger(__name__)

class TextChunker:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Sentence boundary patterns
        self.sentence_endings = re.compile(r'[.!?]+\s+')
        
    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove page numbers and common headers/footers
        text = re.sub(r'\b(page|Page)\s+\d+\b', '', text)
        text = re.sub(r'\d+\s*/\s*\d+', '', text)  # Remove page numbers like "1/10"
        
        # Clean up multiple newlines
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        return text.strip()
    
    def split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        sentences = []
        current_pos = 0
        
        for match in self.sentence_endings.finditer(text):
            sentence = text[current_pos:match.end()].strip()
            if sentence and len(sentence) > 10:  # Ignore very short sentences
                sentences.append(sentence)
            current_pos = match.end()
        
        # Add remaining text if any
        if current_pos < len(text):
            remaining = text[current_pos:].strip()
            if remaining and len(remaining) > 10:
                sentences.append(remaining)
        
        return sentences
    
    def chunk_text(self, text: str) -> List[str]:
        """
        Chunk text into overlapping segments while preserving sentence boundaries
        """
        # Clean the text first
        text = self.clean_text(text)
        
        # Split into sentences
        sentences = self.split_into_sentences(text)
        
        if not sentences:
            return []
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        i = 0
        while i < len(sentences):
            sentence = sentences[i]
            sentence_length = len(sentence)
            
            # If adding this sentence would exceed chunk size
            if current_length + sentence_length > self.chunk_size and current_chunk:
                # Finalize current chunk
                chunk_text = ' '.join(current_chunk)
                chunks.append(chunk_text)
                
                # Start new chunk with overlap
                overlap_chunk = []
                overlap_length = 0
                
                # Add sentences from the end of current chunk for overlap
                for j in range(len(current_chunk) - 1, -1, -1):
                    overlap_sentence = current_chunk[j]
                    if overlap_length + len(overlap_sentence) <= self.chunk_overlap:
                        overlap_chunk.insert(0, overlap_sentence)
                        overlap_length += len(overlap_sentence)
                    else:
                        break
                
                current_chunk = overlap_chunk
                current_length = overlap_length
            
            # Add current sentence
            current_chunk.append(sentence)
            current_length += sentence_length
            
            i += 1
        
        # Add the last chunk if it has content
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunks.append(chunk_text)
        
        # Filter out very short chunks
        chunks = [chunk for chunk in chunks if len(chunk.strip()) > 50]
        
        logger.info(f"Created {len(chunks)} chunks from {len(sentences)} sentences")
        
        return chunks
    
    def chunk_by_paragraphs(self, text: str) -> List[str]:
        """
        Alternative chunking method that preserves paragraph structure
        """
        text = self.clean_text(text)
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for paragraph in paragraphs:
            paragraph_length = len(paragraph)
            
            # If adding this paragraph would exceed chunk size
            if current_length + paragraph_length > self.chunk_size and current_chunk:
                chunk_text = '\n\n'.join(current_chunk)
                chunks.append(chunk_text)
                
                # Start new chunk with some overlap
                if len(current_chunk) > 1:
                    current_chunk = [current_chunk[-1]]  # Keep last paragraph for overlap
                    current_length = len(current_chunk[0])
                else:
                    current_chunk = []
                    current_length = 0
            
            current_chunk.append(paragraph)
            current_length += paragraph_length
        
        # Add the last chunk
        if current_chunk:
            chunk_text = '\n\n'.join(current_chunk)
            chunks.append(chunk_text)
        
        return [chunk for chunk in chunks if len(chunk.strip()) > 50]