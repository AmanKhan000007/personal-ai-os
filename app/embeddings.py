import hashlib, math, re
from collections import Counter

# Dependency-free local semantic-ish embeddings for the MVP.
# This uses hashed word + character n-gram features so memory retrieval works
# without another paid API. It can later be replaced by a transformer model.
DIM = 768
WORD_RE = re.compile(r"[\w@.+-]+", re.UNICODE)

def _features(text: str):
    text = text.lower().strip()
    words = WORD_RE.findall(text)
    feats = list(words)
    for word in words:
        padded = f"^{word}$"
        feats.extend(padded[i:i+3] for i in range(max(0, len(padded)-2)))
    return feats

def embed(text: str):
    vec = [0.0] * DIM
    counts = Counter(_features(text))
    for token, count in counts.items():
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        n = int.from_bytes(digest, "big")
        idx = n % DIM
        sign = -1.0 if (n >> 10) & 1 else 1.0
        vec[idx] += sign * (1.0 + math.log(count))
    norm = math.sqrt(sum(v*v for v in vec)) or 1.0
    return [v/norm for v in vec]

def cosine(a, b):
    return sum(x*y for x,y in zip(a,b))

def pack(vec):
    return ",".join(f"{v:.7g}" for v in vec)

def unpack(value):
    if not value: return []
    return [float(x) for x in value.split(",")]
