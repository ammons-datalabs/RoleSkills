# RoleSkills

![CI](https://github.com/ammons-datalabs/roleskills/actions/workflows/ci.yml/badge.svg?branch=main)
![License: MIT](https://img.shields.io/badge/license-MIT-blue)

**Match developers to roles by extracting evidence from GitHub repositories and scoring against job description requirements.**

## Status: Work in Progress

RoleSkills is under active development. The core pipeline is functional but the project is not yet ready for production use. We're building incrementally through milestones (see Roadmap below).

## What It Does

RoleSkills analyzes job descriptions and GitHub repositories to provide evidence-based role matching:

1. **Parse Job Descriptions** - Extract structured requirements from JD text (deterministic + LLM-enhanced)
2. **Index GitHub Evidence** - Build searchable index of code contributions, commits, and file changes
3. **Retrieve & Match** - Hybrid search (lexical + semantic) to find relevant evidence for each requirement
4. **Score & Report** - Calculate requirement-level scores with supporting evidence links

## Quick Start

```bash
# 1. Install dependencies
make dev

# 2. Configure
export OPENAI_API_KEY=your_key_here

# 3. Run tests
make test

# 4. Parse a job description
python -m roleskills.cli jd-parse-llm path/to/job_description.txt

# 5. Build evidence index from your GitHub repos
python -m roleskills.cli evidence-build \
  --github-user your-username \
  --repo /path/to/repo1 \
  --repo /path/to/repo2 \
  --db-path evidence.sqlite

# 6. Score yourself against a JD
python -m roleskills.cli score \
  --jd path/to/parsed_jd.json \
  --db-path evidence.sqlite
```

## Technology Stack

- **Python 3.11+** - Core language
- **OpenAI GPT-4** - LLM-enhanced JD parsing
- **SQLite + FTS5** - Local evidence indexing with full-text search
- **pytest** - Testing framework (119 tests)
- **Langfuse** - Observability and tracing
- **GitHub Actions** - CI/CD

## Project Structure

```
src/roleskills/
  ├── jd/                    # Job description parsing (M1)
  │   ├── parser.py          # Deterministic MD parser
  │   ├── llm_parser.py      # LLM-enhanced parser
  │   └── schema.py          # JD data models
  ├── evidence/              # GitHub evidence indexing (M2)
  │   ├── builder.py         # Index builder
  │   ├── store.py           # SQLite storage
  │   └── github.py          # Git integration
  ├── retrieve/              # Evidence retrieval (M3)
  │   ├── query.py           # Hybrid search
  │   └── rank.py            # Relevance ranking
  ├── score/                 # Scoring system (M3)
  │   ├── rubric.py          # Scoring logic
  │   └── models.py          # Score schemas
  └── cli.py                 # Command-line interface

tests/                       # 119 tests across all modules
```

## Roadmap

### ✅ Completed Milestones

- **M0: Foundation** - Observable framework, CLI, testing infrastructure
- **M1: Job Description Parser** - Deterministic + LLM-enhanced JD parsing with schema validation
- **M2: Evidence Indexing** - GitHub-based evidence collection and storage
- **M3: Retrieval & Scoring** - Hybrid matching and requirement-level scoring

### 🚧 In Progress

- **Documentation** - Usage guides, API docs, architecture overview
- **Public Release Prep** - Clean up for open source publication

### 📋 Planned Milestones

- **M4: Portfolio Generation** - Auto-generate evidence-backed developer portfolios
- **M5: Web Interface** - Streamlit or FastAPI-based UI
- **M6: GitHub Integration** - Direct GitHub API integration (currently uses local repos)
- **M7: Production Hardening** - Performance optimization, error handling, rate limiting

## Example Output

```json
{
  "overall_score": 0.89,
  "requirements_met": 7,
  "requirements_total": 8,
  "requirements": [
    {
      "id": "req_1",
      "title": "Python expertise",
      "score": 0.95,
      "evidence_count": 5,
      "top_evidence": [
        {
          "path": "src/analyzer/core.py",
          "anchor": "implement_caching_decorator",
          "relevance": 0.92,
          "url": "https://github.com/user/repo/blob/abc123/src/analyzer/core.py#L45-L67"
        }
      ]
    }
  ]
}
```

## Development

```bash
# Run tests
make test

# Run with coverage
make test-coverage

# Lint and format
make lint

# Type checking
make type-check
```

## Limitations

- **Local-only**: Currently requires local git repositories (no direct GitHub API integration yet)
- **OpenAI dependency**: LLM parsing requires OpenAI API key
- **Single-user**: Designed for individual use, not multi-tenant
- **English only**: JD parsing optimized for English job descriptions

## Contributing

This project is in early development. Contributions are welcome but expect rapid changes. Please open an issue to discuss before submitting PRs.

## License

MIT

---

> **Ammons Data Labs** builds observable, measurable AI agents and data systems.