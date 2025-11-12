# RoleSkills

![CI](https://github.com/ammons-datalabs/roleskills/actions/workflows/ci.yml/badge.svg?branch=main)
![License: MIT](https://img.shields.io/badge/license-MIT-blue)

**Extracts, scores, and evidences role-specific skills from GitHub repos and job descriptions using agentic pipelines.**

## Status: Feasibility Exploration

RoleSkills is in early development focused on validating the core concept: Can we reliably extract, score, and evidence role-specific skills from real-world code and job descriptions using AI agents?

## What We're Building

- **Skill Extraction Agents** - DSPy-based agents to identify skills from GitHub repositories
- **Evidence-Based Scoring** - Link skills to actual code patterns and contributions
- **Job Description Matching** - Map extracted skills to role requirements
- **Observable Pipeline** - Built on Langfuse for tracing and quality assurance

## Technology Stack

- **DSPy** - Structured LLM programming for skill extraction
- **Langfuse** - Observability and tracing
- **pytest** - Testing framework
- **GitHub Actions** - CI/CD pipeline

## Project Structure

```
src/roleskills/             # Core framework (from observable-agent-starter)
  ├── observability.py      # ObservabilityProvider with composition pattern
  ├── config.py             # LM + Langfuse configuration
  └── __init__.py

tests/                      # Framework tests
```

## Quick Start

```bash
# 1. Install dependencies
make dev

# 2. Configure (optional for now)
export OPENAI_API_KEY=...
export LANGFUSE_PUBLIC_KEY=...      # Optional
export LANGFUSE_SECRET_KEY=...      # Optional

# 3. Run tests to verify setup
make test
```

## Origin

RoleSkills is built on the [observable-agent-starter](https://github.com/ammons-datalabs/observable-agent-starter) template, providing production-ready observability and testing infrastructure from day one.

## Roadmap

### Current: Feasibility Milestones
- [ ] Validate skill extraction from sample GitHub repos
- [ ] Prove evidence linking (skill → code pattern)
- [ ] Benchmark extraction quality metrics
- [ ] Prototype job description matching

### Future
- Production skill extraction pipeline
- GitHub integration for automated skill profiling
- Job matching API
- Developer portfolio generation

## License

MIT

---

> **Ammons Data Labs** builds observable, measurable AI agents and data systems.