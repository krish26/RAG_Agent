"""
Step 4: the full RAG pipeline. Retrieve chunks, then let a language model
answer from them, with page citations.

Run:  python 04_ask.py "How many hit points does an owlbear have?"
See the exact prompt the model receives:
      python 04_ask.py "How many hit points does an owlbear have?" --show-prompt

Needs GROQ_API_KEY in your .env file.
"""

import importlib.util
import os
import sys

from dotenv import load_dotenv
from groq import Groq

# Load search() from 03_search.py. (A file name that starts with a digit
# can't be imported the normal way, so we load it by path.)
_spec = importlib.util.spec_from_file_location("search_step", "03_search.py")
_search_step = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_search_step)
search = _search_step.search

load_dotenv()
MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
TOP_K = 5

# The instructions that turn a general chatbot into a grounded one.
SYSTEM_PROMPT = """You answer questions about the Dungeons & Dragons rules.

Rules you must follow:
- Use ONLY the numbered sources below. Do not use anything you remember about D&D.
- After every fact, cite the page it came from, like this: [page 313].
- If the sources do not contain the answer, say exactly:
  "I couldn't find that in the SRD." Do not guess.
- Keep the answer short and direct."""


def build_prompt(question, hits):
    """Put the retrieved chunks and the question into one message."""
    sources = "\n\n".join(
        f"Source {i} (page {h['page']}, section: {h['section']}):\n{h['text']}"
        for i, h in enumerate(hits, start=1)
    )
    return f"Sources:\n\n{sources}\n\nQuestion: {question}"


def ask(question, k=TOP_K):
    hits = search(question, k=k)
    prompt = build_prompt(question, hits)

    client = Groq()  # reads GROQ_API_KEY from the environment
    response = client.chat.completions.create(
        model=MODEL,
        temperature=0,  # same question, same answer: easier to test
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content, hits


def main():
    args = [a for a in sys.argv[1:] if a != "--show-prompt"]
    if len(args) != 1:
        sys.exit('Usage: python 04_ask.py "your question" [--show-prompt]')
    question = args[0]

    if "--show-prompt" in sys.argv:
        hits = search(question)
        print("=== SYSTEM ===\n" + SYSTEM_PROMPT)
        print("\n=== USER ===\n" + build_prompt(question, hits))
        return

    answer, hits = ask(question)
    print(f"\nQuestion: {question}\n")
    print(answer)
    print("\nRetrieved from:")
    for h in hits:
        print(f"  page {h['page']:>3}  score {h['score']}  [{h['section']}]")


if __name__ == "__main__":
    main()
