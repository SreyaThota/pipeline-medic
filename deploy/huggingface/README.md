---
title: Pipeline Medic
emoji: 🩺
colorFrom: red
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
license: mit
short_description: Agent graph that diagnoses failed CI runs, with human approval
---

# Pipeline Medic demo

Interactive demo of [Pipeline Medic](https://github.com/SreyaThota/pipeline-medic):
an agent graph that diagnoses a failed CI run, rates its risk and proposes a
ticket or notification, then waits for a human before anything runs.

The demo runs the default graph on CPU (retrieval vote and rubric risk stage,
no LLM). Real actions are switched off: approved tools only record a dry run.
The retrieval index is built from the bundled, human-reviewed logs on the
first page load.

This folder is synced from `deploy/huggingface/` in the GitHub repository; see
`deploy/huggingface/DEPLOY.md` there.
