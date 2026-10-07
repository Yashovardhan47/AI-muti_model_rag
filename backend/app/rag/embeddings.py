"""Selected text embedding backend. Hash vectors are explicit offline demo mode."""
from functools import lru_cache
import hashlib
import math
import re
import httpx
from app.core.config import get_settings


class Embedder:
    def __init__(self):
        self.cfg = get_settings()
        self.kind = self.cfg.embedding_provider
        self.model = None
        if self.kind in {"bge", "e5", "multilingual-e5", "sentence-transformers"}:
            from sentence_transformers import SentenceTransformer
            name = self.cfg.embedding_model
            if self.kind == "e5" and name == "BAAI/bge-small-en-v1.5":
                name = "intfloat/e5-small-v2"
            if self.kind == "multilingual-e5" and name == "BAAI/bge-small-en-v1.5":
                name = "intfloat/multilingual-e5-small"
            self.model = SentenceTransformer(name)

    def embed(self, texts: list[str], query: bool = False) -> list[list[float]]:
        if not texts: return []
        if not self.cfg.redis_url:
            return self._compute(texts, query)
        import json
        import redis
        client = redis.Redis.from_url(self.cfg.redis_url, socket_timeout=2)
        keys = ["embed:" + hashlib.sha256((self.kind + ":" + self.cfg.embedding_model + ":" + str(query) + ":" + t).encode()).hexdigest() for t in texts]
        try:
            cached = client.mget(keys)
        except redis.RedisError:
            return self._compute(texts, query)
        vectors = [json.loads(v) if v else None for v in cached]
        missing = [i for i, v in enumerate(vectors) if v is None]
        if missing:
            fresh = self._compute([texts[i] for i in missing], query)
            try:
                pipe = client.pipeline()
                for i, v in zip(missing, fresh):
                    vectors[i] = v
                    pipe.setex(keys[i], 7 * 24 * 3600, json.dumps(v))
                pipe.execute()
            except redis.RedisError:
                pass
        return vectors

    def _compute(self, texts: list[str], query: bool) -> list[list[float]]:
        if self.kind == "hash":
            output = []
            for text in texts:
                v = [0.0] * 384
                for word in re.findall(r"\w+", text.lower()):
                    digest = hashlib.sha256(word.encode()).digest()
                    v[int.from_bytes(digest[:4], "big") % 384] += 1 if digest[4] % 2 else -1
                length = math.sqrt(sum(x*x for x in v)) or 1
                output.append([x/length for x in v])
            return output
        if self.kind == "openai":
            if not self.cfg.openai_api_key: raise ValueError("OPENAI_API_KEY is required")
            response = httpx.post("https://api.openai.com/v1/embeddings", headers={"Authorization": f"Bearer {self.cfg.openai_api_key}"}, json={"model": self.cfg.embedding_model if self.cfg.embedding_model != "BAAI/bge-small-en-v1.5" else "text-embedding-3-small", "input": texts}, timeout=90)
            response.raise_for_status()
            return [item["embedding"] for item in sorted(response.json()["data"], key=lambda x: x["index"])]
        if self.kind in {"e5", "multilingual-e5"}: texts = [("query: " if query else "passage: ") + x for x in texts]
        return self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False).tolist()


@lru_cache
def embedder() -> Embedder:
    return Embedder()


def clip_vectors(image: bytes | None = None, text: str | None = None) -> list[float]:
    from io import BytesIO
    from PIL import Image
    from transformers import CLIPModel, CLIPProcessor
    import torch
    if not hasattr(clip_vectors, "model"):
        clip_vectors.model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        clip_vectors.processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    values = clip_vectors.processor(images=Image.open(BytesIO(image)).convert("RGB") if image else None, text=text, return_tensors="pt", padding=True)
    with torch.no_grad():
        v = clip_vectors.model.get_image_features(**values) if image else clip_vectors.model.get_text_features(**values)
    v = v / v.norm(dim=-1, keepdim=True)
    return v[0].tolist()
