# experiments/

One note per adopted technology, comparing it against the simpler baseline it
replaces, with a number attached.

| Note | Question | Outcome |
|---|---|---|
| `001_chunking_strategy.md` | How should CI logs be chunked for flat RAG? | Last 15 lines wins; cross-repo MRR 0.496 is the bar for v0.2.5 |
