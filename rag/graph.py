"""Neo4j knowledge graph of CI failures (v0.2.5). Schema: docs/ontology.md.

    (:Run)-[:IN_REPO]->(:Repo)
    (:Run)-[:USED_TOOL]->(:Tool)
    (:Run)-[:RAISED]->(:ErrorSignature)
    (:Run)-[:MENTIONS_PACKAGE]->(:Package)
    (:Run)-[:EXITED_WITH]->(:ExitCode)

Tool, ErrorSignature, Package and ExitCode nodes also carry the :Entity label
so one query can match any of them. Every node has an `ns` (namespace)
property, which keeps test and evaluation graphs apart in the single database
that Neo4j Community provides.

Load the main graph from data/sample_logs:
    python -m rag.graph
"""

from collections.abc import Iterable, Sequence

from neo4j import GraphDatabase

from app.config import get_settings
from rag.entities import Entity, extract_entities
from rag.ingest import LogRecord, load_records
from rag.retrieve import Hit

# entity kind -> (node label, relationship type). Fixed here, never user input.
KIND_SCHEMA = {
    "tool": ("Tool", "USED_TOOL"),
    "error": ("ErrorSignature", "RAISED"),
    "package": ("Package", "MENTIONS_PACKAGE"),
    "exit_code": ("ExitCode", "EXITED_WITH"),
}

_CONSTRAINTS = [
    "CREATE CONSTRAINT run_key IF NOT EXISTS FOR (r:Run) REQUIRE (r.ns, r.log_id) IS UNIQUE",
    "CREATE CONSTRAINT repo_key IF NOT EXISTS FOR (r:Repo) REQUIRE (r.ns, r.name) IS UNIQUE",
    "CREATE CONSTRAINT entity_key IF NOT EXISTS FOR (e:Entity) REQUIRE (e.ns, e.key) IS UNIQUE",
]

_LOAD_RUNS = """
UNWIND $rows AS row
MERGE (r:Run {ns: $ns, log_id: row.log_id})
SET r.repo = row.repo, r.label = row.label
MERGE (repo:Repo {ns: $ns, name: row.repo})
MERGE (r)-[:IN_REPO]->(repo)
"""

_LOAD_ENTITIES = """
UNWIND $rows AS row
MATCH (r:Run {{ns: $ns, log_id: row.log_id}})
MERGE (e:Entity:{label} {{ns: $ns, key: row.key}})
SET e.name = row.name, e.kind = row.kind
MERGE (r)-[:{rel}]->(e)
"""

# A candidate run scores the summed rarity (IDF) of the entities it shares
# with the query. Rare entities (one specific error) count more than common
# ones (exit code 1).
_FILTER = """
  ($exclude_id IS NULL OR {var}.log_id <> $exclude_id)
  AND ($exclude_repo IS NULL OR {var}.repo <> $exclude_repo)
"""

_SEARCH_DIRECT = f"""
MATCH (e:Entity {{ns: $ns}}) WHERE e.key IN $keys
MATCH (e)<--(c:Run {{ns: $ns}})
WHERE {_FILTER.format(var="c")}
WITH c, e, COUNT {{ (e)<--(o:Run) WHERE $exclude_id IS NULL OR o.log_id <> $exclude_id }} AS df
WITH c, sum(log(1.0 + $n / toFloat(df))) AS score, collect(e.key) AS shared
RETURN c.log_id AS log_id, c.repo AS repo, c.label AS label, score, shared
"""

# Multi-hop expansion: query entity <- bridge run -> other entity <- candidate.
# A candidate that shares no entity with the query can still score if it has
# entities that often appear alongside the query's entities in other runs.
_SEARCH_EXPANDED = f"""
MATCH (q:Entity {{ns: $ns}}) WHERE q.key IN $keys
MATCH (q)<--(m:Run {{ns: $ns}})-->(x:Entity)<--(c:Run {{ns: $ns}})
WHERE NOT x.key IN $keys AND m <> c
  AND {_FILTER.format(var="m")}
  AND {_FILTER.format(var="c")}
WITH c, x, count(DISTINCT m) AS co
WITH c, x, co, COUNT {{ (x)<--(:Run) }} AS df
WITH c, sum((toFloat(co) / df) * log(1.0 + $n / toFloat(df))) AS score,
     collect(x.key) AS shared
RETURN c.log_id AS log_id, c.repo AS repo, c.label AS label, score, shared
"""


class GraphStore:
    def __init__(self, uri: str, user: str, password: str, namespace: str = "main"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.ns = namespace

    @classmethod
    def from_settings(cls, namespace: str = "main") -> GraphStore:
        s = get_settings()
        return cls(s.neo4j_uri, s.neo4j_user, s.neo4j_password.get_secret_value(), namespace)

    def close(self) -> None:
        self.driver.close()

    def _run(self, query: str, **params):
        records, _, _ = self.driver.execute_query(query, ns=self.ns, **params)
        return records

    def reset(self) -> None:
        """Delete every node in this namespace (other namespaces are untouched)."""
        self._run("MATCH (n {ns: $ns}) DETACH DELETE n")

    def load(self, records: Sequence[LogRecord]) -> dict[str, int]:
        """Replace this namespace's graph with the given runs and their entities."""
        for statement in _CONSTRAINTS:
            self.driver.execute_query(statement)
        self.reset()
        self._run(_LOAD_RUNS, rows=[
            {"log_id": r.log_id, "repo": r.repo, "label": r.label} for r in records
        ])
        by_kind: dict[str, list[dict]] = {kind: [] for kind in KIND_SCHEMA}
        for rec in records:
            for ent in extract_entities(rec.text):
                by_kind[ent.kind].append(
                    {"log_id": rec.log_id, "key": ent.key, "name": ent.name, "kind": ent.kind}
                )
        for kind, rows in by_kind.items():
            label, rel = KIND_SCHEMA[kind]
            if rows:
                self._run(_LOAD_ENTITIES.format(label=label, rel=rel), rows=rows)
        return self.counts()

    def counts(self) -> dict[str, int]:
        nodes = self._run("MATCH (n {ns: $ns}) RETURN labels(n) AS labels, count(*) AS c")
        out = {"Run": 0, "Repo": 0, "Entity": 0}
        for row in nodes:
            for label in row["labels"]:
                out[label] = out.get(label, 0) + row["c"]
        edges = self._run("MATCH ({ns: $ns})-[r]->() RETURN count(r) AS c")
        out["relationships"] = edges[0]["c"]
        return out

    def search(
        self,
        entities: Iterable[Entity],
        k: int = 5,
        exclude_log_id: str | None = None,
        exclude_repo: str | None = None,
        expand_weight: float = 0.0,
    ) -> list[Hit]:
        """Rank past runs by the entities they share with the query.

        expand_weight > 0 adds the multi-hop score, scaled by that weight.
        """
        keys = sorted({e.key for e in entities})
        if not keys:
            return []
        params = {
            "keys": keys, "exclude_id": exclude_log_id, "exclude_repo": exclude_repo,
            "n": self._run("MATCH (r:Run {ns: $ns}) RETURN count(r) AS c")[0]["c"],
        }
        hits: dict[str, Hit] = {}
        for row in self._run(_SEARCH_DIRECT, **params):
            hits[row["log_id"]] = Hit(
                row["log_id"], row["repo"], row["label"], row["score"],
                "shared: " + ", ".join(sorted(row["shared"])),
            )
        if expand_weight > 0:
            for row in self._run(_SEARCH_EXPANDED, **params):
                extra = expand_weight * row["score"]
                if row["log_id"] in hits:
                    hits[row["log_id"]].score += extra
                else:
                    hits[row["log_id"]] = Hit(
                        row["log_id"], row["repo"], row["label"], extra,
                        "related: " + ", ".join(sorted(set(row["shared"]))),
                    )
        ranked = sorted(hits.values(), key=lambda h: (-h.score, h.log_id))
        return ranked[:k]


def main() -> None:
    store = GraphStore.from_settings()
    try:
        counts = store.load(load_records(labelled_only=True))
    finally:
        store.close()
    print("graph loaded:", ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))


if __name__ == "__main__":
    main()
