"""
The Rules Lawyer - a small web page for the D&D rules agent.

Run:  streamlit run app.py
"""

import base64
import html
import importlib.util
import re
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="The Rules Lawyer", page_icon="assets/d20.svg", layout="centered")

EXAMPLES = [
    "How much does a rapier cost?",
    "What happens when I'm grappled?",
    "How many spell slots does a level 5 Wizard have?",
    "How many hit points does an owlbear have?",
]

AGENT = "Agent: picks its own tools"
PLAIN = "Simple search: one search, then answer"


# ---------- loading the two pipelines (once per server) ----------

def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@st.cache_resource(show_spinner="Opening the rulebook...")
def pipelines():
    return {AGENT: _load("06_agent.py", "agent_step"), PLAIN: _load("04_ask.py", "ask_step")}


# ---------- look ----------

D20 = base64.b64encode(Path("assets/d20.svg").read_bytes()).decode()

ICONS = {
    "search_rules": '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="10" cy="10" r="6"/><path d="M15 15l6 6"/></svg>',
    "list_tables": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5h7a2 2 0 0 1 2 2v12a2 2 0 0 0-2-2H4z"/><path d="M20 5h-7a2 2 0 0 0-2 2v12a2 2 0 0 1 2-2h7z"/></svg>',
    "read_table": '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="4" width="18" height="16" rx="1"/><path d="M3 9h18M3 14h18M9 9v11"/></svg>',
}
TOOL_NAMES = {
    "search_rules": "Searched the rules text",
    "list_tables": "Looked for a table",
    "read_table": "Read rows from a table",
}

st.markdown(
    f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=IM+Fell+English:ital@0;1&family=Alegreya:wght@400;700&family=Alegreya+Sans:wght@400;500;700&display=swap');

:root {{
  --felt: #1E3328;
  --felt-deep: #172820;
  --vellum: #EFE4C8;
  --ink: #2B2118;
  --brass: #C9A24A;
  --oxblood: #7A2E2A;
  --mist: #A9B8A9;
}}

.stApp p, .stApp li, .stApp label, .stApp button, .stApp input, .stApp textarea,
.stApp summary, .stApp span:not([data-testid="stIconMaterial"]) {{
  font-family: 'Alegreya Sans', 'Segoe UI', sans-serif;
}}
.stApp {{
  background:
    radial-gradient(ellipse at 50% -10%, rgba(201,162,74,.10), transparent 55%),
    radial-gradient(ellipse at 50% 120%, rgba(0,0,0,.35), transparent 60%),
    var(--felt);
}}
.block-container {{ max-width: 760px; padding-top: 2.5rem; }}

/* hero */
.hero {{ display: flex; gap: 1.4rem; align-items: center; margin-bottom: .4rem; }}
.hero img {{ width: 92px; height: 92px; flex: none;
  filter: drop-shadow(0 6px 10px rgba(0,0,0,.45));
  animation: roll 1.1s cubic-bezier(.2,.8,.2,1) both; }}
@keyframes roll {{
  0% {{ transform: translate(-60px,-30px) rotate(-260deg) scale(.7); opacity: 0; }}
  70% {{ transform: translate(4px,2px) rotate(12deg) scale(1.03); opacity: 1; }}
  100% {{ transform: none; }}
}}
@media (prefers-reduced-motion: reduce) {{ .hero img {{ animation: none; }} }}
.stApp .hero h1, .stApp .hero h1 span {{
  font-family: 'IM Fell English', Georgia, serif; font-weight: 400;
  font-size: clamp(2.4rem, 7vw, 3.6rem); line-height: 1; letter-spacing: -.01em;
  color: var(--vellum); margin: 0; padding: 0;
}}
.hero p {{ color: var(--mist); font-size: 1.12rem; line-height: 1.5; margin: .5rem 0 0; max-width: 34em; }}
@media (max-width: 640px) {{
  .block-container {{ padding-top: 3.5rem; }}
  .hero {{ gap: .9rem; align-items: flex-start; }}
  .hero img {{ width: 60px; height: 60px; margin-top: .3rem; }}
  .hero p {{ font-size: 1.02rem; }}
}}

/* example questions */
div[data-testid="stHorizontalBlock"] button, .stButton button {{
  background: transparent; border: 1px solid rgba(201,162,74,.45); color: var(--vellum);
  border-radius: 999px; font-size: .95rem; padding: .35rem .9rem; text-align: left;
}}
.stButton button:hover {{ border-color: var(--brass); color: var(--brass); background: rgba(201,162,74,.06); }}
.stButton button:focus-visible {{ outline: 2px solid var(--brass); outline-offset: 2px; }}

/* chat */
[data-testid="stChatMessage"] {{ background: transparent; padding: .25rem 0; }}
.stApp .question {{ font-family: 'IM Fell English', Georgia, serif; font-style: italic;
  font-size: 1.35rem; color: var(--vellum); line-height: 1.35; }}
.slip {{
  background: linear-gradient(180deg, #F3EAD2, var(--vellum));
  color: var(--ink); border-radius: 3px; padding: 1.1rem 1.3rem 1rem;
  font-family: 'Alegreya', Georgia, serif;
  font-size: 1.08rem; line-height: 1.6;
  box-shadow: 0 1px 0 rgba(255,255,255,.4) inset, 0 10px 24px rgba(0,0,0,.35);
  border-left: 4px solid var(--oxblood);
}}
.slip strong {{ color: #1A130D; }}
.page {{
  display: inline-block; font-size: .8rem; font-weight: 700; color: var(--vellum);
  background: var(--oxblood); border-radius: 3px; padding: 0 .4rem; margin: 0 .1rem;
  vertical-align: .1em; white-space: nowrap;
}}
.refusal {{ border-left-color: #6B6B5A; color: #4A4436; font-style: italic; }}

/* the agent's trail */
.trail {{ list-style: none; padding: 0; margin: .3rem 0 0; counter-reset: step; }}
.trail li {{ display: grid; grid-template-columns: 1.6rem 1.2rem 1fr; gap: .55rem; align-items: start;
  padding: .45rem 0; border-bottom: 1px dashed rgba(169,184,169,.25); color: var(--mist); }}
.trail li:last-child {{ border-bottom: 0; }}
.trail li::before {{ counter-increment: step; content: counter(step);
  font-family: 'IM Fell English', Georgia, serif; color: var(--brass); font-size: 1.1rem; }}
.trail svg {{ width: 1.1rem; height: 1.1rem; margin-top: .2rem; fill: none; stroke: var(--brass); stroke-width: 1.8; }}
.trail b {{ color: var(--vellum); font-weight: 500; }}
.trail code {{ background: rgba(0,0,0,.25); color: var(--vellum); font-size: .85rem; padding: 0 .3rem; border-radius: 2px; }}

[data-testid="stSidebar"] {{ background: var(--felt-deep); }}
.stApp [data-testid="stSidebar"] h3, .stApp [data-testid="stSidebar"] h3 span {{ font-family: 'IM Fell English', Georgia, serif; font-weight: 400; color: var(--vellum); }}
.small {{ color: var(--mist); font-size: .88rem; line-height: 1.5; }}
.small a {{ color: var(--brass); }}
</style>
""",
    unsafe_allow_html=True,
)


# ---------- helpers ----------

PAGE_REF = re.compile(r"[\[【]\s*(?:page|p\.)\s*(\d+)\s*[\]】]", re.IGNORECASE)
REFUSAL = "couldn't find that in the srd"


def render_answer(answer):
    """Escape the model's text, keep **bold**, and turn [page 91] into a badge."""
    text = " ".join(answer.replace(" ", " ").split())
    text = html.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = PAGE_REF.sub(lambda m: f'<span class="page" title="SRD page {m.group(1)}">p.&nbsp;{m.group(1)}</span>', text)
    refused = REFUSAL in answer.lower().replace("’", "'")
    return f'<div class="slip{" refusal" if refused else ""}">{text}</div>'


def render_trail(steps):
    items = []
    for step in steps:
        name, _, args = step.partition("(")
        args = args.rstrip(")")
        icon = ICONS.get(name, ICONS["search_rules"])
        label = TOOL_NAMES.get(name, name)
        items.append(f"<li>{icon}<span><b>{label}</b><br><code>{html.escape(args)}</code></span></li>")
    if not items:
        return '<p class="small">It answered without looking anything up.</p>'
    return f'<ol class="trail">{"".join(items)}</ol>'


def render_sources(hits):
    pages = sorted({h["page"] for h in hits})
    badges = " ".join(f'<span class="page">p.&nbsp;{p}</span>' for p in pages)
    return f'<p class="small">Searched once and read these pages: {badges}</p>'


def show(entry):
    with st.chat_message("user", avatar="assets/quill.svg"):
        st.markdown(f'<div class="question">{html.escape(entry["question"])}</div>', unsafe_allow_html=True)
    with st.chat_message("assistant", avatar="assets/d20.svg"):
        if entry.get("error"):
            st.error(entry["error"])
            return
        st.markdown(render_answer(entry["answer"]), unsafe_allow_html=True)
        if entry["mode"] == AGENT and not entry["extra"]:
            st.markdown('<p class="small">Answered without looking anything up.</p>', unsafe_allow_html=True)
        elif entry["mode"] == AGENT:
            with st.expander(f"How it found this ({len(entry['extra'])} steps)"):
                st.markdown(render_trail(entry["extra"]), unsafe_allow_html=True)
        else:
            st.markdown(render_sources(entry["extra"]), unsafe_allow_html=True)


def run(question, mode):
    entry = {"question": question, "mode": mode}
    try:
        with st.spinner("Checking the rules..."):
            answer, extra = pipelines()[mode].ask(question)
        entry.update(answer=answer, extra=extra)
    except Exception as err:  # show a useful message instead of a stack trace
        message = str(err)
        if "api_key" in message.lower() or "GROQ_API_KEY" in message:
            entry["error"] = "No working Groq API key. Add GROQ_API_KEY to the .env file and restart."
        elif "rate" in message.lower() and "limit" in message.lower():
            entry["error"] = "The free Groq limit was reached. Wait a minute and ask again."
        else:
            entry["error"] = f"Something went wrong: {message[:300]}"
    st.session_state.history.append(entry)


# ---------- page ----------

if "history" not in st.session_state:
    st.session_state.history = []

with st.sidebar:
    st.markdown("### How should it answer?")
    mode = st.radio("Mode", [AGENT, PLAIN], label_visibility="collapsed")
    st.markdown(
        '<p class="small">The agent decides for itself whether to search the text, '
        "open a table, or both. Simple search always does one search and answers from "
        "the top five results. Try a table question in both modes to see the difference.</p>",
        unsafe_allow_html=True,
    )
    if st.session_state.history and st.button("Clear the table"):
        st.session_state.history = []
        st.rerun()
    st.markdown("### About")
    st.markdown(
        '<p class="small">Built with retrieval-augmented generation and a LangGraph agent. '
        "Answers come only from the SRD and cite the page.</p>"
        '<p class="small">This work includes material from the System Reference Document 5.2.1 '
        '("SRD 5.2.1") by Wizards of the Coast LLC, available at '
        '<a href="https://www.dndbeyond.com/srd">dndbeyond.com/srd</a>. '
        'The SRD 5.2.1 is licensed under the '
        '<a href="https://creativecommons.org/licenses/by/4.0/legalcode">Creative Commons '
        "Attribution 4.0 International License</a>.</p>",
        unsafe_allow_html=True,
    )

st.markdown(
    f"""<div class="hero">
  <img src="data:image/svg+xml;base64,{D20}" alt="">
  <div><h1>The Rules Lawyer</h1>
  <p>Ask about any rule in the free fifth-edition rulebook. Every answer comes with the page it's from.</p></div>
</div>""",
    unsafe_allow_html=True,
)

picked = None
if not st.session_state.history:
    st.write("")
    cols = st.columns(2)
    for i, example in enumerate(EXAMPLES):
        if cols[i % 2].button(example, key=f"ex{i}", use_container_width=True):
            picked = example

for entry in st.session_state.history:
    show(entry)

typed = st.chat_input("Ask a rules question, like “How does cover work?”")
question = typed or picked
if question:
    run(question, mode)
    st.rerun()
