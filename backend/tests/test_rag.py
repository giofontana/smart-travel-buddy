from smart_travel_buddy.rag.embeddings import EmbeddingModel

def test_embedding_model_loads():
    model = EmbeddingModel()
    assert model.dimension == 384

def test_embedding_model_encodes():
    model = EmbeddingModel()
    embedding = model.encode("Tokyo is the capital of Japan")
    assert len(embedding) == 384
    assert isinstance(embedding[0], float)

def test_embedding_model_batch():
    model = EmbeddingModel()
    embeddings = model.encode_batch(["Hello world", "Tokyo travel guide"])
    assert len(embeddings) == 2
    assert len(embeddings[0]) == 384
