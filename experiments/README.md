# experiments/

One note per adopted technology, comparing it against the simpler baseline it
replaces, with a number attached.

| Note | Question | Outcome |
|---|---|---|
| `001_chunking_strategy.md` | How should CI logs be chunked for flat RAG? | Last 15 lines wins; cross-repo MRR 0.496 is the bar for v0.2.5 |
| `002_graphrag_vs_flat.md` | Does a knowledge graph beat flat RAG on held-out logs? | No proven gain (+0.028 MRR, interval includes zero); flat stays default |
| `003_lora_risk_classifier.md` | Does a LoRA classifier beat the prompted LLM on risk? | Gain not proven (+0.047 acc); prompted LLM misses every high-risk log; not adopted |
