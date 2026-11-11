"""Pipeline Medic interactive demo.

    streamlit run demo/app.py

Runs the real default graph on a CI log: redact → parse → diagnose (flat-RAG
vote) → risk (rubric v1, no LLM) → propose actions → pause for a human →
execute as a dry run. Nothing in the demo can create a real ticket or send a
real notification: actions are disabled in its settings.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from agents.diagnosis_agent import build_retriever
from app.errors import LogTooLarge
from app.graph import Approval, PipelineMedicState
from app.graph_orchestrator import PipelineMedicGraph
from demo.helpers import (
    EXPERIMENTS_URL,
    FLOW_DIAGRAM,
    REPO_URL,
    Example,
    demo_settings,
    evidence_window,
    load_examples,
    redaction_example,
    redaction_summary,
    rubric_reason,
    stage_latency,
)

REDACTION_CHOICE = "Synthetic log with fake credentials (shows redaction)"
PASTE_CHOICE = "Paste your own log"
RISK_COLOURS = {"high": "red", "medium": "orange", "low": "green"}
FORMAT_NAMES = {"github_actions": "GitHub Actions", "jenkins": "Jenkins", "text": "plain text"}

st.set_page_config(page_title="Pipeline Medic demo", page_icon=":material/healing:",
                   layout="wide")


@st.cache_resource(show_spinner="Building the retrieval index (first load only)…")
def get_graph() -> PipelineMedicGraph:
    """One graph and retriever per server process, shared by all sessions.
    Each run has its own id, so sessions never see each other's runs."""
    return PipelineMedicGraph.default(demo_settings(), retriever=build_retriever(),
                                      risk="rubric")


@st.cache_data
def get_examples() -> list[Example]:
    return load_examples()


def latency_caption(latency: dict[str, float], *stages: str) -> None:
    total = sum(latency.get(s, 0.0) for s in stages)
    st.caption(f":material/timer: {total:,.1f} ms")


def run_pipeline(log_text: str, source_log_id: str | None, workflow: str | None) -> None:
    st.session_state.original = log_text
    st.session_state.final = None
    try:
        st.session_state.state = get_graph().start(
            log_text, source_log_id=source_log_id, workflow=workflow)
        st.session_state.error = None
    except LogTooLarge as exc:
        st.session_state.state = None
        st.session_state.error = str(exc)


def decide(approved: bool) -> None:
    state = st.session_state.state
    approval = Approval(approved=approved, approver="demo visitor",
                        note="decision made in the public demo")
    st.session_state.final = get_graph().resume(state["run_id"], approval)


for key in ("state", "final", "original", "error"):
    st.session_state.setdefault(key, None)

# --- sidebar ---------------------------------------------------------------

with st.sidebar:
    st.header("How it works")
    st.mermaid_chart(FLOW_DIAGRAM, alt="Pipeline Medic flow: redact, parse, diagnose, "
                     "risk, propose, human approval, then dry-run tools")
    st.markdown(
        "- Log text is **untrusted**: it never chooses a tool.\n"
        "- Secrets are redacted **before** anything else sees the log.\n"
        "- **Nothing runs without approval**, and this demo only ever dry-runs."
    )
    st.link_button("Source on GitHub", REPO_URL, icon=":material/code:", width="stretch")

# --- input -----------------------------------------------------------------

st.title("Pipeline Medic")
st.markdown("An agent graph that diagnoses a failed CI run, rates its risk and proposes "
            "a ticket or notification, then **waits for a human** before anything runs.")

with st.expander("Honest numbers", icon=":material/analytics:"):
    st.markdown(
        "Measured on held-out logs from real public repositories; details in "
        f"[`experiments/`]({EXPERIMENTS_URL}).\n\n"
        "- The full graph is fully correct on **27.8%** of 72 held-out runs (rubric risk "
        "stage) against 11.1% with a prompted LLM.\n"
        "- Diagnosis is the first stage to go wrong in **48 of 72** runs, so expect "
        "some wrong categories below.\n"
        "- The rubric risk stage scores 0.609 accuracy; a LoRA classifier (0.52–0.59) "
        "and a prompted LLM (0.500) did worse, so neither is used.\n"
        "- Safety invariants (redaction, no tool choice from log text, approval before "
        "execution) held in every run."
    )

examples = get_examples()
choices = [e.title for e in examples] + [REDACTION_CHOICE, PASTE_CHOICE]
choice = st.selectbox("CI log", choices, key="choice")
example = next((e for e in examples if e.title == choice), None)
source_id: str | None = None
workflow: str | None = None

if example is not None:
    st.caption(f"Real failed run from **{example.repo}** · [original run]({example.run_url}) · "
               f"reviewed label `{example.label}` · this log is left out of the knowledge "
               "base for this run")
    log_text, source_id, workflow = example.text(), example.log_id, example.workflow
elif choice == REDACTION_CHOICE:
    log_text, source_id, workflow = redaction_example(), None, "Release"
    st.code(log_text, language=None, wrap_lines=True)
else:
    log_text = st.text_area("Paste a CI log", height=200, key="pasted",
                            placeholder="Paste the output of a failed CI job…")

get_graph()  # build the retrieval index on first page load, not on the first run

if st.button("Run the pipeline", type="primary", icon=":material/play_arrow:",
             disabled=not log_text.strip(), key="run"):
    with st.spinner("Running the graph…"):
        run_pipeline(log_text, source_id, workflow)

if st.session_state.error:
    st.error(st.session_state.error, title="Log not accepted")

state: PipelineMedicState | None = st.session_state.state
if state is None:
    st.stop()

final: PipelineMedicState | None = st.session_state.final
latency = stage_latency((final or state)["trace"])
parsed, diagnosis, risk = state["parsed"], state["diagnosis"], state["risk"]

# --- 1. parse and redact ---------------------------------------------------

with st.container(border=True):
    st.subheader(":material/description: 1. Parse and redact")
    latency_caption(latency, "parse")
    redacted = redaction_summary(st.session_state.original)
    cols = st.columns(3)
    cols[0].metric("Lines", f"{parsed.line_count:,}")
    cols[1].metric("Failure regions", len(parsed.regions))
    cols[2].metric("Secrets redacted", sum(redacted.values()))
    st.caption(f"Detected format: {FORMAT_NAMES[parsed.format]}")
    if redacted:
        st.info(", ".join(f"{n} × `[REDACTED:{kind}]`" for kind, n in redacted.items()),
                title="Redacted before parsing, storage or any model call")
    st.markdown("**Evidence** (`>` marks the cited line; numbers are the original log's)")
    st.code(evidence_window(state["log_text"], [e.line for e in diagnosis.evidence],
                            parsed.format), language=None, wrap_lines=True)

# --- 2. diagnosis ----------------------------------------------------------

with st.container(border=True):
    st.subheader(":material/troubleshoot: 2. Diagnosis")
    latency_caption(latency, "diagnose")
    st.markdown(f"Category: **`{diagnosis.category or 'unknown'}`** · "
                f"{diagnosis.confidence:.0%} of the retrieval vote")
    if example is not None:
        if diagnosis.category == example.label:
            st.success("Matches the reviewed label.", icon=":material/check:")
        else:
            st.warning(f"The reviewed label is `{example.label}`: the diagnosis is wrong here.",
                       icon=":material/error:")
    st.markdown("**Most similar past failures**")
    st.dataframe(
        [{"log": s.log_id, "repo": s.repo, "category": s.label, "similarity": s.score}
         for s in diagnosis.similar[:3]],
        hide_index=True, alt="Top three similar past failures",
        column_config={"similarity": st.column_config.NumberColumn(format="%.3f")},
    )

# --- 3. risk ---------------------------------------------------------------

with st.container(border=True):
    st.subheader(":material/warning: 3. Risk")
    latency_caption(latency, "classify_risk")
    st.markdown(f":{RISK_COLOURS[risk.level]}-badge[{risk.level}] {rubric_reason(state)}")

# --- 4. proposed actions ---------------------------------------------------

with st.container(border=True):
    st.subheader(":material/assignment: 4. Proposed actions")
    latency_caption(latency, "propose_actions")
    actions = state["proposed_actions"]
    if not actions:
        st.success("Low risk and a confident diagnosis: no action proposed, nothing to approve.",
                   icon=":material/done_all:")
    for action in actions:
        st.markdown(f"**`{action.tool}`**: {action.reason}")
        st.json(action.arguments, expanded=False)

# --- 5. approval and execution ---------------------------------------------

if actions:
    with st.container(border=True):
        st.subheader(":material/how_to_reg: 5. Human approval")
        if final is None:
            st.markdown("The graph is **paused**. Nothing runs until you decide.")
            row = st.container(horizontal=True)
            row.button("Approve", type="primary", icon=":material/check:",
                       on_click=decide, args=(True,), key="approve")
            row.button("Reject", icon=":material/close:", on_click=decide, args=(False,), key="reject")
        else:
            latency_caption(latency, "human_approval", "execute_actions")
            graph = get_graph()
            decision = "approved" if final["approval"].approved else "rejected"
            st.markdown(f"Decision: **{decision}** · run status `{final['status']}`")
            for result in final["action_results"]:
                st.markdown(f"**`{result.tool}`** → `{result.status}`")
            if final["approval"].approved:
                st.caption("Real actions are switched off in this demo, so approved tools "
                           "validate their input and record a dry run instead of acting.")
            st.markdown("**Audit log entries**")
            st.dataframe(
                [{"time": e["ts"], "tool": e["tool"], "phase": e["phase"],
                  "action": e["action_id"][:8]}
                 for r in final["action_results"]
                 for e in graph.actor.audit.entries(r.action_id)],
                hide_index=True, alt="Audit log entries for this run",
            )
