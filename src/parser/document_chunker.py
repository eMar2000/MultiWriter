"""Document Chunker - Split large documents into semantic chunks for LLM processing"""

from typing import List, Dict, Any
import re


class DocumentChunk:
    """Represents a semantically coherent chunk of a document"""

    def __init__(self, content: str, metadata: Dict[str, Any] = None):
        self.content = content
        self.metadata = metadata or {}
        self.token_count = self._estimate_tokens(content)

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation: ~0.75 tokens per word"""
        words = len(text.split())
        return int(words * 0.75)

    def __repr__(self):
        return f"DocumentChunk({self.token_count} tokens, {len(self.content)} chars)"


class DocumentChunker:
    """
    Utility to split large documents into smaller, semantically coherent chunks.

    Designed to prevent LLM context overload by:
    - Keeping chunks under target token limit
    - Preserving semantic boundaries (headings, paragraphs, list items)
    - Adding overlap for context continuity
    """

    def __init__(
        self,
        chunk_size: int = 800,  # Target tokens per chunk
        overlap: int = 100,      # Overlap tokens between chunks
        min_chunk_size: int = 200  # Minimum chunk size
    ):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.min_chunk_size = min_chunk_size

    def chunk_markdown(self, content: str, source_doc: str = None) -> List[DocumentChunk]:
        """
        Chunk markdown document by semantic boundaries.

        Strategy:
        1. Split by top-level headings (##, ###)
        2. If sections are too large, split by paragraphs
        3. Add overlap between chunks for context

        Args:
            content: Markdown content
            source_doc: Source document name (for metadata)

        Returns:
            List of DocumentChunk objects
        """
        chunks = []

        # Split by headings (## or ###)
        sections = self._split_by_headings(content)

        for section in sections:
            section_chunks = self._chunk_section(section)
            for i, chunk_content in enumerate(section_chunks):
                chunk = DocumentChunk(
                    content=chunk_content,
                    metadata={
                        "source_doc": source_doc,
                        "section_index": len(chunks),
                        "is_continuation": i > 0
                    }
                )
                chunks.append(chunk)

        return chunks

    def _split_by_headings(self, content: str) -> List[str]:
        """Split content by markdown headings (## or ###)"""
        # Pattern to match ## Heading or ### Heading
        pattern = r'^(#{2,3}\s+.+)$'

        sections = []
        current_section = []

        for line in content.split('\n'):
            if re.match(pattern, line):
                # Save previous section
                if current_section:
                    sections.append('\n'.join(current_section))
                # Start new section with heading
                current_section = [line]
            else:
                current_section.append(line)

        # Add last section
        if current_section:
            sections.append('\n'.join(current_section))

        return sections

    def _chunk_section(self, section: str) -> List[str]:
        """
        Chunk a section if it's too large.

        If section exceeds chunk_size, split by paragraphs.
        """
        estimated_tokens = self._estimate_tokens(section)

        # Section is small enough
        if estimated_tokens <= self.chunk_size:
            return [section]

        # Split by paragraphs (double newline)
        paragraphs = section.split('\n\n')

        chunks = []
        current_chunk = []
        current_tokens = 0

        for para in paragraphs:
            para_tokens = self._estimate_tokens(para)

            # Paragraph alone exceeds chunk size - split by sentences
            if para_tokens > self.chunk_size:
                # Save current chunk if exists
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                    current_chunk = []
                    current_tokens = 0

                # Split large paragraph by sentences
                sentences = self._split_by_sentences(para)
                sent_chunk = []
                sent_tokens = 0

                for sent in sentences:
                    sent_tok = self._estimate_tokens(sent)
                    if sent_tokens + sent_tok > self.chunk_size and sent_chunk:
                        chunks.append(' '.join(sent_chunk))
                        # Keep last sentence for overlap
                        sent_chunk = [sent_chunk[-1]] if self.overlap > 0 else []
                        sent_tokens = self._estimate_tokens(sent_chunk[0]) if sent_chunk else 0

                    sent_chunk.append(sent)
                    sent_tokens += sent_tok

                if sent_chunk:
                    chunks.append(' '.join(sent_chunk))

            # Adding paragraph would exceed limit
            elif current_tokens + para_tokens > self.chunk_size:
                # Save current chunk
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))

                # Start new chunk with overlap
                if self.overlap > 0 and current_chunk:
                    # Keep last paragraph for overlap
                    current_chunk = [current_chunk[-1], para]
                    current_tokens = self._estimate_tokens(current_chunk[0]) + para_tokens
                else:
                    current_chunk = [para]
                    current_tokens = para_tokens

            # Add paragraph to current chunk
            else:
                current_chunk.append(para)
                current_tokens += para_tokens

        # Add final chunk
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))

        return chunks

    def _split_by_sentences(self, text: str) -> List[str]:
        """Split text by sentences (rough heuristic)"""
        # Split on . ! ? followed by space/newline
        sentences = re.split(r'([.!?]+[\s\n]+)', text)

        # Recombine sentence with punctuation
        result = []
        for i in range(0, len(sentences) - 1, 2):
            if i + 1 < len(sentences):
                result.append(sentences[i] + sentences[i + 1])
            else:
                result.append(sentences[i])

        return result

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation: ~0.75 tokens per word"""
        if not text:
            return 0
        words = len(text.split())
        return int(words * 0.75)

    def chunk_entity_list(self, entities: List[Any], batch_size: int = 15) -> List[List[Any]]:
        """
        Batch a list of entities for processing.

        Args:
            entities: List of Entity objects
            batch_size: Max entities per batch

        Returns:
            List of entity batches
        """
        batches = []
        for i in range(0, len(entities), batch_size):
            batches.append(entities[i:i + batch_size])
        return batches
