"""RAG retrieval functions for querying knowledge chunks."""

from functools import lru_cache

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from smart_travel_buddy.rag.embeddings import EmbeddingModel


@lru_cache(maxsize=1)
def get_embedding_model() -> EmbeddingModel:
    """Get or create singleton embedding model instance."""
    return EmbeddingModel()


async def retrieve_chunks(
    session: AsyncSession,
    query: str,
    top_k: int = 5,
) -> list[dict]:
    """
    Retrieve top-k knowledge chunks most similar to the query.

    Args:
        session: Async database session
        query: Search query text
        top_k: Number of top results to return

    Returns:
        List of dicts with id, source_file, chunk_text, metadata, similarity
    """
    # Encode query to embedding
    model = get_embedding_model()
    query_embedding = model.encode(query)

    # Execute vector similarity search using pgvector
    sql_query = text("""
        SELECT
            id,
            source_file,
            chunk_text,
            metadata,
            1 - (embedding <=> CAST(:embedding AS vector)) AS similarity
        FROM knowledge_chunks
        ORDER BY embedding <=> CAST(:embedding AS vector)
        LIMIT :top_k
    """)

    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

    result = await session.execute(
        sql_query,
        {"embedding": embedding_str, "top_k": top_k},
    )

    rows = result.fetchall()

    return [
        {
            "id": row[0],
            "source_file": row[1],
            "chunk_text": row[2],
            "metadata": row[3],
            "similarity": float(row[4]),
        }
        for row in rows
    ]
