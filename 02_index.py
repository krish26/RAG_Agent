"""
Step 2: turn every chunk into an embedding and store it in a vector database.

Run:  python 02_index.py
In:   data/chunks.json
Out:  data/chroma/   (the vector database, saved on disk)

The first run downloads the embedding model (about 130 MB) and then
takes a few minutes to embed all chunks.
"""

import json
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

CHUNKS_FILE = Path("data/chunks.json")
DB_FOLDER = "data/chroma"
COLLECTION = "srd"

# A small, free embedding model that runs on your laptop.
# It turns a piece of text into a list of 384 numbers.
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"


def main():
    chunks = json.loads(CHUNKS_FILE.read_text(encoding="utf-8"))
    print(f"Loaded {len(chunks)} chunks")

    model = SentenceTransformer(EMBEDDING_MODEL)

    # This is the slow part: every chunk goes through the model once.
    # normalize_embeddings=True makes all vectors the same length, so
    # comparing two of them only measures direction (meaning), not size.
    texts = [c["text"] for c in chunks]
    embeddings = model.encode(
        texts, batch_size=32, show_progress_bar=True, normalize_embeddings=True
    )
    print(f"Each chunk is now a list of {len(embeddings[0])} numbers")

    # Start from an empty collection every time, so re-running is safe.
    client = chromadb.PersistentClient(path=DB_FOLDER)
    if COLLECTION in [c.name for c in client.list_collections()]:
        client.delete_collection(COLLECTION)
    collection = client.create_collection(
        COLLECTION, metadata={"hnsw:space": "cosine"}  # compare by cosine similarity
    )

    # Store text + embedding + metadata together, in batches.
    for start in range(0, len(chunks), 500):
        batch = chunks[start : start + 500]
        collection.add(
            ids=[c["id"] for c in batch],
            documents=[c["text"] for c in batch],
            embeddings=embeddings[start : start + 500].tolist(),
            metadatas=[
                {"page": c["page"], "section": c["section"], "source": c["source"]}
                for c in batch
            ],
        )

    print(f"Stored {collection.count()} chunks in {DB_FOLDER}")


if __name__ == "__main__":
    main()
