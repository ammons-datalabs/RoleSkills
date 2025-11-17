"""RoleSkills CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .observability import create_observability


def main(argv: list[str] | None = None) -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="roleskills", description="RoleSkills - Extract and score role-specific skills"
    )
    parser.add_argument("--version", action="store_true", help="Print version and exit")

    # Add subcommands
    sub = parser.add_subparsers(dest="cmd")

    p_parse = sub.add_parser("jd-parse", help="Parse a JD markdown file to JSON (deterministic)")
    p_parse.add_argument("path", help="Path to JD .md/.txt")

    p_parse_llm = sub.add_parser("jd-parse-llm", help="Parse a JD using LLM hybrid pipeline")
    p_parse_llm.add_argument("path", help="Path to JD .md/.txt")
    p_parse_llm.add_argument("--model", default="gpt-4o-mini", help="OpenAI model to use")
    p_parse_llm.add_argument("--no-cache", action="store_true", help="Disable caching")

    p_ev_build = sub.add_parser("evidence-build", help="Build local evidence index from GitHub")
    p_ev_build.add_argument("--github-user", required=True, help="GitHub username to attribute")
    p_ev_build.add_argument("--org", action="append", default=[], help="Preferred org(s) to boost")
    p_ev_build.add_argument("--jd-tags", default="", help="Comma-separated JD terms for pickaxe search")
    p_ev_build.add_argument("--chunk-budget", type=int, default=3000, help="Max chunks to store")
    p_ev_build.add_argument("--recent-window", default="180 days", help="Recent commit window")
    p_ev_build.add_argument("--db-path", default="index.sqlite", help="SQLite database path")
    p_ev_build.add_argument("--repo", action="append", default=[], help="Repository directory path(s) to index")

    p_ev_stats = sub.add_parser("evidence-stats", help="Show evidence index statistics")
    p_ev_stats.add_argument("--db-path", default="index.sqlite", help="SQLite database path")

    p_retrieve = sub.add_parser("retrieve", help="Retrieve evidence for JD requirements")
    p_retrieve.add_argument("--jd", required=True, help="Path to JD JSON file")
    p_retrieve.add_argument("--db-path", default="index.sqlite", help="SQLite database path")
    p_retrieve.add_argument("--max-evidence", type=int, default=5, help="Max evidence per requirement")

    p_score = sub.add_parser("score", help="Score JD against evidence index")
    p_score.add_argument("--jd", required=True, help="Path to JD JSON file")
    p_score.add_argument("--db-path", default="index.sqlite", help="SQLite database path")
    p_score.add_argument("--max-evidence", type=int, default=5, help="Max evidence per requirement")

    args = parser.parse_args(argv)

    if args.version:
        print(__version__)
        return 0

    if args.cmd == "jd-parse":
        text = Path(args.path).read_text(encoding="utf-8")
        from .jd.parser import parse_jd

        jd = parse_jd(text)
        print(json.dumps(jd.model_dump(), indent=2, ensure_ascii=False))
        return 0

    if args.cmd == "jd-parse-llm":
        text = Path(args.path).read_text(encoding="utf-8")
        from .jd.llm_parser import llm_parse_jd

        try:
            jd = llm_parse_jd(text, model=args.model, use_cache=not args.no_cache)
            print(json.dumps(jd.model_dump(), indent=2, ensure_ascii=False))
            return 0
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    if args.cmd == "evidence-build":
        from .evidence import EvidenceStore, build_index

        store = EvidenceStore(args.db_path)
        jd_terms = [t.strip() for t in args.jd_tags.split(",") if t.strip()]

        # Parse repo directories
        repo_dirs = [Path(r) for r in args.repo] if args.repo else None

        print(f"Building evidence index for @{args.github_user}...")
        stats = build_index(
            author=args.github_user,
            preferred_orgs=set(args.org),
            jd_terms=jd_terms,
            chunk_budget=args.chunk_budget,
            recent_window=args.recent_window,
            store=store,
            repo_dirs=repo_dirs,
        )
        print(json.dumps(stats, indent=2))

        # Warn about unpushed commits
        if stats.get("commits_unpushed", 0) > 0:
            print(f"\n⚠️  Warning: {stats['commits_unpushed']} of {stats['commits_selected']} commits are not pushed to remote.", file=sys.stderr)
            print("   GitHub permalinks will return 404 until you push these commits.", file=sys.stderr)
            print("   Run 'git push' to make the evidence links accessible.", file=sys.stderr)

        return 0

    if args.cmd == "evidence-stats":
        from .evidence import EvidenceStore

        store = EvidenceStore(args.db_path)
        stats = store.stats()
        print(json.dumps(stats, indent=2))
        return 0

    if args.cmd == "retrieve":
        from .evidence import EvidenceStore
        from .jd.schema import JD
        from .matcher import retrieve_evidence

        # Load JD
        jd_data = json.loads(Path(args.jd).read_text(encoding="utf-8"))
        jd = JD(**jd_data)

        store = EvidenceStore(args.db_path)

        # Retrieve evidence for each requirement
        results = {"requirements": []}
        for req in jd.requirements:
            hits = retrieve_evidence(req, store, max_evidence=args.max_evidence)
            results["requirements"].append({
                "id": req.id,
                "title": req.title,
                "evidence": [
                    {
                        "evidence_id": h.evidence_id,
                        "anchor": h.anchor,
                        "path": h.path,
                        "score_relevance": h.combined_relevance,
                        "score_lexical": h.score_lexical,
                        "score_tags": h.score_tags,
                        "score_path": h.score_path,
                    }
                    for h in hits
                ],
            })

        print(json.dumps(results, indent=2))
        return 0

    if args.cmd == "score":
        from .evidence import EvidenceStore
        from .jd.schema import JD
        from .matcher import score_jd

        # Load JD
        jd_data = json.loads(Path(args.jd).read_text(encoding="utf-8"))
        jd = JD(**jd_data)

        store = EvidenceStore(args.db_path)

        # Score JD
        summary = score_jd(jd, store, max_evidence=args.max_evidence)

        print(json.dumps(summary.model_dump(), indent=2, ensure_ascii=False))
        return 0

    # Default behavior (no subcommand)
    observability = create_observability("cli", configure_lm=False)
    observability.logger.info("RoleSkills CLI")
    print("roleskills: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
