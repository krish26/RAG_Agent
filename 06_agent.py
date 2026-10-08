"""
Step 6: the agent. Same data, but now the model decides what to do.

Run:  python 06_agent.py "How much does a rapier cost?"

The model gets three tools:
  search_rules  - meaning-based search over the text (step 3)
  list_tables   - find tables by name, e.g. "weapon" or "wizard"
  read_table    - read rows from one table, e.g. the "Rapier" row

It can call them as many times as it needs, in any order, and answers
when it has what it needs. LangGraph runs that loop for us.
"""

import importlib.util
import os
import sys

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

import tables

_spec = importlib.util.spec_from_file_location("search_step", "03_search.py")
_search_step = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_search_step)

load_dotenv()
MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
MAX_STEPS = 12  # safety limit so a confused agent can't loop forever


# ---------- 1. Tools ----------
# The docstring of each tool is what the model reads to decide when to use it.
# Writing clear tool descriptions is a big part of building agents.

@tool
def search_rules(query: str) -> str:
    """Search the D&D rules text by meaning. Best for rules written as sentences:
    conditions, actions, spells, class features, how something works."""
    hits = _search_step.search(query, k=5)
    return "\n\n".join(f"[page {h['page']}] {h['text']}" for h in hits)


@tool
def list_tables(keyword: str) -> str:
    """Find tables by name or column headers, best match first.
    Use one to three words, e.g. "weapon", "armor", "wizard spell slots"."""
    names = tables.list_tables(keyword)
    if not names:
        return f"No tables found for '{keyword}'. Try a shorter or different word."
    return "\n".join(names[:30])


@tool
def read_table(table_name: str, row_contains: str = "") -> str:
    """Read one table. table_name must come from list_tables.
    row_contains filters rows, e.g. "Longsword" or a level like "5".
    Leave row_contains empty to read the whole table."""
    result, suggestions = tables.read_table(table_name, row_contains)
    if result is None:
        hint = "\n".join(suggestions) if suggestions else "none"
        return f"Table '{table_name}' not found. Did you mean one of:\n{hint}"
    if result["rows_shown"] == 0:
        return f"No rows in '{result['name']}' match '{row_contains}'."
    return (f"{result['name']} - showing {result['rows_shown']} of "
            f"{result['rows_total']} rows:\n{result['text']}")


TOOLS = [search_rules, list_tables, read_table]

SYSTEM_PROMPT = """You answer questions about the Dungeons & Dragons rules (SRD 5.2.1).

How to work:
- Numbers in tables (weapon damage, costs, spell slots, class traits) -> use
  list_tables, then read_table. Do not rely on search_rules for these.
- Rules written as text (conditions, spells, actions) -> use search_rules.
- You may call tools several times. Check the result answers the question.

Rules for the final answer:
- Use ONLY what the tools returned, never your own memory of D&D.
- Cite the page after each fact, like [page 91].
- If the tools don't give you the answer, say exactly:
  "I couldn't find that in the SRD."
- Keep it short."""


# ---------- 2. The graph ----------
# Two nodes and a loop:
#
#   START -> agent --(wants a tool?)--> tools --+
#              ^                                |
#              +--------------------------------+
#            agent --(no tool call)--> END
#
# MessagesState is the agent's memory for one question: the list of every
# message so far (question, tool calls, tool results).

def build_agent():
    llm = ChatGroq(model=MODEL, temperature=0).bind_tools(TOOLS)

    def agent_node(state: MessagesState):
        reply = llm.invoke([SystemMessage(SYSTEM_PROMPT)] + state["messages"])
        return {"messages": [reply]}

    graph = StateGraph(MessagesState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(TOOLS))
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition)  # -> "tools" or END
    graph.add_edge("tools", "agent")
    return graph.compile()


_agent = None


def ask(question, k=None):
    """Run the agent. Returns (answer, steps) so callers can see what it did."""
    global _agent
    if _agent is None:
        _agent = build_agent()
    result = _agent.invoke(
        {"messages": [HumanMessage(question)]},
        config={"recursion_limit": MAX_STEPS * 2},
    )
    steps = []
    for m in result["messages"]:
        for call in getattr(m, "tool_calls", []) or []:
            steps.append(f"{call['name']}({', '.join(f'{k}={v!r}' for k, v in call['args'].items())})")
    return result["messages"][-1].content, steps


def main():
    if len(sys.argv) != 2:
        sys.exit('Usage: python 06_agent.py "your question"')
    question = sys.argv[1]
    answer, steps = ask(question)
    print(f"\nQuestion: {question}\n")
    print("What the agent did:")
    for i, s in enumerate(steps, 1):
        print(f"  {i}. {s}")
    print(f"\nAnswer:\n{answer}")


if __name__ == "__main__":
    main()
