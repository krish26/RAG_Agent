"""
Step 3: search the vector database with a question.

Run:  python 03_search.py "How many spell slots does a level 5 wizard have?"

This is the "retrieval" half of RAG. No language model is involved yet.
"""

import sys

import chromadb
from sentence_transformers import SentenceTransformer

DB_FOLDER = "data/chroma"
COLLECTION = "srd"
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"  # must be the same model as in 02_index.py
TOP_K = 5

# This model was trained to expect this sentence in front of a question
# (not in front of the documents).
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


_model = None


def get_model():
    """Load the embedding model once and reuse it (loading takes a few seconds)."""
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def search(question, k=TOP_K):
    """Return the k chunks whose meaning is closest to the question."""
    model = get_model()
    query_embedding = model.encode(QUERY_PREFIX + question, normalize_embeddings=True)

    collection = chromadb.PersistentClient(path=DB_FOLDER).get_collection(COLLECTION)
    result = collection.query(query_embeddings=[query_embedding.tolist()], n_results=k)

    hits = []
    for text, meta, distance in zip(
        result["documents"][0], result["metadatas"][0], result["distances"][0]
    ):
        hits.append(
            {
                "text": text,
                "page": meta["page"],
                "section": meta["section"],
                "score": round(1 - distance, 3),  # 1.0 = same meaning, 0 = unrelated
            }
        )
    return hits


def main():
    if len(sys.argv) != 2:
        sys.exit('Usage: python 03_search.py "your question"')

    question = sys.argv[1]
    print(f"Question: {question}\n")
    for rank, hit in enumerate(search(question), start=1):
        preview = hit["text"][:400]
        print(f"#{rank}  score {hit['score']}  page {hit['page']}  [{hit['section']}]")
        print(preview + ("..." if len(hit["text"]) > 400 else ""))
        print()


if __name__ == "__main__":
    main()
