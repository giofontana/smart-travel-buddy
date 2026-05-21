from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"

class EmbeddingModel:
    def __init__(self):
        self._model = SentenceTransformer(MODEL_NAME)
        self.dimension = 384

    def encode(self, text: str) -> list[float]:
        return self._model.encode(text).tolist()

    def encode_batch(self, texts: list[str]) -> list[list[float]]:
        return self._model.encode(texts).tolist()
