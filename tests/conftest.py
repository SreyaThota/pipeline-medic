import hashlib
import re

import pytest


def _hash_embed(texts):
    """Deterministic bag-of-words embedder so tests never download a model."""
    dim = 256
    vectors = []
    for text in texts:
        vec = [0.0] * dim
        for token in re.findall(r"[a-z]+", text.lower()):
            vec[int(hashlib.md5(token.encode()).hexdigest(), 16) % dim] += 1.0
        norm = sum(v * v for v in vec) ** 0.5 or 1.0
        vectors.append([v / norm for v in vec])
    return vectors


@pytest.fixture
def fake_embed():
    return _hash_embed
