"""
Step 5: measure how good the system is, with a fixed set of test questions.

Run everything (retrieval + answers, uses the Groq API):
      python 05_eval.py
Run only the retrieval check (free and fast, no API calls):
      python 05_eval.py --retrieval-only
Test the agent from step 6 instead of the plain pipeline:
      python 05_eval.py --agent

Questions live in evals/questions.json. Each one has:
  page   - the PDF page that holds the answer (null if the SRD doesn't cover it)
  expect - words the answer must contain. "a|b" means a OR b.
           "REFUSE" means the system should say it couldn't find it.
"""

import importlib.util
import json
import sys
import time
from pathlib import Path


def load(step_file, name):
    spec = importlib.util.spec_from_file_location(name, step_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


QUESTIONS = Path("evals/questions.json")
RESULTS = Path("evals/last_run.json")
REFUSAL = "couldn't find that in the srd"
TOP_K = 5


def answer_is_correct(answer, expect):
    # Models often use special spaces (e.g. "8\u202fhours"). Turn every kind
    # of space into a normal one before comparing.
    text = " ".join(answer.lower().replace("’", "'").split())
    if expect == ["REFUSE"]:
        return REFUSAL in text
    if REFUSAL in text:
        return False
    return all(any(option.lower() in text for option in item.split("|")) for item in expect)


def main():
    retrieval_only = "--retrieval-only" in sys.argv
    search_step = load("03_search.py", "search_step")
    use_agent = "--agent" in sys.argv
    pipeline = "06_agent.py" if use_agent else "04_ask.py"
    ask_step = None if retrieval_only else load(pipeline, "ask_step")
    print(f"Testing: {'retrieval only' if retrieval_only else pipeline}\n")

    questions = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    rows = []

    for q in questions:
        hits = search_step.search(q["question"], k=TOP_K)
        pages = [h["page"] for h in hits]
        found = None if q["page"] is None else q["page"] in pages
        row = {"question": q["question"], "expected_page": q["page"],
               "retrieved_pages": pages, "retrieval_hit": found}

        if not retrieval_only:
            answer, extra = ask_step.ask(q["question"], k=TOP_K)
            row["answer"] = answer
            if use_agent:
                row["agent_steps"] = extra
            row["answer_correct"] = answer_is_correct(answer, q["expect"])
            time.sleep(2)  # stay well under the free rate limit

        rows.append(row)
        r = {None: "  - ", True: " yes", False: "  NO"}[found]
        a = "" if retrieval_only else ("   answer OK" if row["answer_correct"] else "   answer WRONG")
        print(f"retrieved{r}{a}   {q['question']}")

    scored = [r for r in rows if r["retrieval_hit"] is not None]
    hits = sum(r["retrieval_hit"] for r in scored)
    print(f"\nRetrieval: right page in top {TOP_K} for {hits}/{len(scored)} questions")
    if not retrieval_only:
        correct = sum(r["answer_correct"] for r in rows)
        print(f"Answers:   {correct}/{len(rows)} correct")

    out = RESULTS.with_name("last_run_agent.json") if "--agent" in sys.argv else RESULTS
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Details saved to {out}")


if __name__ == "__main__":
    main()
