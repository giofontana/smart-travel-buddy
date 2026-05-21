"""Knowledge base seeding utilities for loading and embedding markdown files."""

import argparse
from pathlib import Path

from sqlalchemy import create_engine, text

from smart_travel_buddy.config import settings
from smart_travel_buddy.rag.embeddings import EmbeddingModel


def chunk_text(text_content: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """
    Split text into word-based chunks with overlap.

    Args:
        text_content: Text to chunk
        chunk_size: Target number of characters per chunk
        overlap: Number of characters to overlap between chunks

    Returns:
        List of text chunks
    """
    # Split into words
    words = text_content.split()
    chunks = []

    # Approximate words per chunk (assuming average word length ~5 chars + 1 space)
    words_per_chunk = chunk_size // 6
    overlap_words = overlap // 6

    i = 0
    while i < len(words):
        # Take chunk of words
        chunk_words = words[i : i + words_per_chunk]
        chunk = " ".join(chunk_words)
        chunks.append(chunk)

        # Move forward by chunk size minus overlap
        i += words_per_chunk - overlap_words

        # Avoid infinite loop on small texts
        if len(chunk_words) < words_per_chunk:
            break

    return chunks


def seed_knowledge(knowledge_dir: str) -> None:
    """
    Load markdown files from knowledge directory and seed database.

    This function is idempotent - it clears existing chunks and reloads.

    Args:
        knowledge_dir: Path to directory containing .md files
    """
    knowledge_path = Path(knowledge_dir)

    if not knowledge_path.exists():
        print(f"Error: Knowledge directory '{knowledge_dir}' does not exist")
        return

    # Initialize embedding model
    print("Loading embedding model...")
    model = EmbeddingModel()

    # Create synchronous database engine
    engine = create_engine(settings.database_url_sync)

    # Collect all markdown files
    md_files = list(knowledge_path.rglob("*.md"))
    print(f"Found {len(md_files)} markdown files")

    if not md_files:
        print("No markdown files found to seed")
        return

    # Clear existing knowledge chunks and insert new ones
    with engine.connect() as conn:
        print("Clearing existing knowledge chunks...")
        conn.execute(text("DELETE FROM knowledge_chunks"))
        conn.commit()

        total_chunks = 0

        for md_file in md_files:
            print(f"Processing: {md_file.name}")

            # Read file content
            content = md_file.read_text(encoding="utf-8")

            # Skip empty files
            if not content.strip():
                print(f"  Skipping empty file: {md_file.name}")
                continue

            # Chunk the content
            chunks = chunk_text(content)
            print(f"  Created {len(chunks)} chunks")

            # Embed and insert chunks
            for idx, chunk in enumerate(chunks):
                # Generate embedding
                embedding = model.encode(chunk)

                # Get relative path for source_file
                try:
                    source_file = str(md_file.relative_to(knowledge_path))
                except ValueError:
                    source_file = md_file.name

                # Prepare metadata
                metadata = {
                    "chunk_index": idx,
                    "total_chunks": len(chunks),
                    "file_name": md_file.name,
                }

                # Insert into database using raw SQL with vector cast
                insert_sql = text("""
                    INSERT INTO knowledge_chunks (source_file, chunk_text, metadata, embedding)
                    VALUES (:source_file, :chunk_text, :metadata, :embedding::vector)
                """)

                conn.execute(
                    insert_sql,
                    {
                        "source_file": source_file,
                        "chunk_text": chunk,
                        "metadata": metadata,
                        "embedding": embedding,
                    },
                )

            total_chunks += len(chunks)

        conn.commit()

    print(f"\nSeeding complete! Inserted {total_chunks} knowledge chunks from {len(md_files)} files")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed knowledge base from markdown files")
    parser.add_argument(
        "knowledge_dir",
        nargs="?",
        default="../../knowledge",
        help="Path to knowledge directory (default: ../../knowledge)",
    )

    args = parser.parse_args()
    seed_knowledge(args.knowledge_dir)
