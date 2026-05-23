# Hermes-MiMo Writer

<h3 align="center">Multi-agent academic writing pipeline powered by Xiaomi MiMo V2.5 Pro + Hermes Agent</h3>

<p align="center">
  Seven specialized agents collaborate to take a free-form assignment brief and<br/>
  produce a citation-backed, style-matched, AI-detector-resistant DOCX in one pass.
</p>

<p align="center">
  <a href="https://hermes-mimo-writer.vercel.app">🔗 Live Demo</a> ·
  <a href="https://github.com/gnpa910/hermes-mimo-writer">📦 GitHub</a> ·
  <a href="#getting-started">🚀 Getting Started</a> ·
  <a href="#web-demo">▶ Try the Sanitizer</a>
</p>

---

<p align="center">
  <img src="https://img.shields.io/badge/PYTHON-3.10+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.10+"/>
  <img src="https://img.shields.io/badge/NEXT.JS-16-black?style=flat-square&logo=next.js" alt="Next.js 16"/>
  <img src="https://img.shields.io/badge/TYPESCRIPT-5-3178C6?style=flat-square&logo=typescript" alt="TypeScript 5"/>
  <img src="https://img.shields.io/badge/AI_ENGINE-MiMo_V2.5_Pro-FF6900?style=flat-square&logo=xiaomi" alt="MiMo V2.5 Pro"/>
  <img src="https://img.shields.io/badge/ORCHESTRATION-Hermes_Agent-00FFD5?style=flat-square" alt="Hermes Agent"/>
  <img src="https://img.shields.io/badge/STREAMING-SSE-blue?style=flat-square" alt="SSE Streaming"/>
  <img src="https://img.shields.io/badge/TESTS-54_passing-green?style=flat-square" alt="54 tests"/>
  <img src="https://img.shields.io/badge/LICENSE-MIT-green?style=flat-square" alt="MIT"/>
</p>

---

## Table of Contents

- [Overview](#overview)
- [Why MiMo?](#why-mimo)
- [Architecture](#architecture)
- [The Seven Agents](#the-seven-agents)
- [Token Consumption](#token-consumption)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [CLI Usage](#cli-usage)
- [Web Demo](#web-demo)
- [Project Structure](#project-structure)
- [API Reference](#api-reference)
- [Environment Variables](#environment-variables)
- [Testing](#testing)
- [License](#license)

---

## Overview

**Hermes-MiMo Writer** automates the end-to-end production of academic essays through a coordinated pipeline of seven specialized agents, all backed by **Xiaomi MiMo V2.5 Pro** through the Token Plan API. Drop in a free-form rubric or assignment brief; receive a structured, cited, style-matched DOCX.

**The Problem:** Generating long-form academic work with a single LLM call collapses voice consistency, fabricates citations, and leaves obvious AI-detector signatures. Manual chaining loses traceability of which step did what. Existing tools either lock to a single LLM, hide their internals, or charge per-essay rates that don't scale.

**The Approach:** Decompose the workflow into seven small, typed agents — each with one job, each verifiable in isolation. Orchestrate them through Hermes Agent's `delegate_task` pattern. Run heavy reasoning (outline architecture, sanitization, citation resolution) on **MiMo V2.5 Pro** for its long-chain coherence; run cheap classification work (brief parsing) on **MiMo V2 Flash** to control cost. Track every token in a per-agent ledger so cost is fully transparent.

A typical 1,000-word essay run consumes 80K–150K tokens across the seven agents (~$0.12–$0.22 at MiMo overseas pricing — roughly 6× cheaper than the equivalent Claude Opus pipeline).

---

## Why MiMo?

We deliberately picked **Xiaomi MiMo V2.5 Pro** over Claude/GPT/Gemini after benchmarking on three properties that matter for this pipeline:

| Property | Why it matters here | MiMo's edge |
|---|---|---|
| **Long-chain reasoning** | Outline + multi-section coherence requires holding ~2K tokens of structure in working memory | `reasoning_content` returned alongside content; observable thought trace in agent logs |
| **Multilingual quality (id/ms/zh)** | Indonesian and Malay are core target languages; most Western models produce stilted academic prose in them | Native Chinese training corpus + strong Bahasa coverage; idiomatic output without paraphrasing telltales |
| **1M context length** | Style profiling against a corpus of past student work; loading 50+ sample essays into one analysis call | 1M context on Pro tier vs Claude's 200K; eliminates chunking complexity |
| **Cost per quality unit** | Pipeline runs are heavy; cost-per-essay determines whether this is a research toy or a deployable tool | $1.00/M input cache-miss + $3.00/M output overseas; ~6× cheaper than Claude Opus equivalent |
| **Streaming SSE** | Web demo needs token-by-token feedback during draft generation for usable UX | First-class SSE support, low time-to-first-token |

The pipeline degrades gracefully with smaller models (V2-Flash for cheap classification), so a single account covers the full workload without juggling provider keys.

---

## Architecture

```
┌──────────────┐
│  Brief.md    │
│  + samples   │
└──────┬───────┘
       │
       ▼
┌──────────────────┐    ┌──────────────────┐
│ 1. BriefParser   │───▶│ 2. StyleProfiler │
│   (V2-Flash)     │    │   (V2.5-Pro)     │
└──────────────────┘    └──────┬───────────┘
                               │
                               ▼
                       ┌──────────────────┐
                       │ 3. OutlineDrafter│
                       │   (V2.5-Pro)     │
                       └──────┬───────────┘
                              │
                              ▼
                      ┌──────────────────┐    ┌──────────────────┐
                      │ 4. ContentDrafter│───▶│ 5. AISanitizer   │
                      │   (V2.5-Pro,     │    │   (V2.5-Pro,     │
                      │    parallel x3)  │    │    parallel x3)  │
                      └──────────────────┘    └──────┬───────────┘
                                                     │
                                                     ▼
                                            ┌──────────────────┐
                                            │ 6. CitationMgr   │
                                            │   (V2.5-Pro)     │
                                            └──────┬───────────┘
                                                   │
                                                   ▼
                                          ┌──────────────────┐
                                          │ 7. DocxAssembler │
                                          │   (local, no LLM)│
                                          └──────┬───────────┘
                                                 │
                                                 ▼
                                          ┌──────────────┐
                                          │  essay.docx  │
                                          └──────────────┘
```

Every agent is a typed `Agent[InputT, OutputT]` instance. The orchestrator (`pipeline.py`) wires them in dependency order and threads a shared `TokenLedger` through, so the final report shows exactly where each token went.

---

## The Seven Agents

| # | Agent | Model | Role | Typical tokens/run |
|---|-------|-------|------|--------------------|
| 1 | **BriefParserAgent** | V2-Flash | Extract structured `Brief` (title, word_count, language, citation_style, rubric) from a free-form prompt | 1K–3K |
| 2 | **StyleProfilerAgent** | V2.5-Pro | Build a `StyleProfile` fingerprint from sample texts — register, sentence length, POV, discourse markers, phrases to avoid | 2K–8K |
| 3 | **OutlineDrafterAgent** | V2.5-Pro | Produce a section-by-section `Outline` with target word counts, bullet points, and source hints. Uses MiMo's reasoning chain for coherence | 5K–15K |
| 4 | **ContentDrafterAgent** | V2.5-Pro | Draft each section in parallel (semaphore=3), with [Author, YYYY] citation placeholders. Heaviest token consumer | 30K–80K |
| 5 | **AISanitizerAgent** | V2.5-Pro | Rewrite each section to vary sentence length, replace AI giveaways ("delve", "utilize"), preserve citations. High temp (0.85) for variation | 25K–60K |
| 6 | **CitationManagerAgent** | V2.5-Pro | Resolve all `[Surname_Year]` markers into a properly formatted references list in the requested style (APA/MLA/Chicago/Harvard) | 4K–12K |
| 7 | **DocxAssemblerAgent** | local | Pure local logic: emit a properly formatted `.docx` with title page, sections, language-appropriate references heading | 0 |

Agents 1, 2, 3, 6 are sequential (each depends on the previous). Agent 4 fans out per section. Agent 5 fans out over agent 4's output. Agent 7 is local-only.

---

## Token Consumption

Per-essay numbers from real runs against the MiMo Token Plan endpoint (1,000-word target, 3 style samples, APA citations):

| Metric | Value |
|--------|-------|
| Total tokens per essay | **80K–150K** |
| Daily total (typical batch) | **3M–8M tokens** |
| Per-agent breakdown (avg) | Parser 2K · Style 5K · Outline 10K · Drafter 55K · Sanitizer 45K · Citations 8K · Assembler 0 |
| API endpoint | `https://token-plan-sgp.xiaomimimo.com/v1` |
| Auth method | `api-key` header (Token Plan format, not Bearer) |
| Models used | `mimo-v2.5-pro` (heavy) + `mimo-v2-flash` (cheap parsing) |
| Estimated cost per essay | **$0.12–$0.22** (overseas pricing, mixed cache hit/miss) |

The CLI's `hermes-writer estimate --brief brief.md` command predicts token cost before you commit a run.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.10+, asyncio, httpx, pydantic v2 |
| Orchestration | Hermes Agent (`delegate_task` pattern) |
| AI Engine | Xiaomi MiMo V2.5 Pro + V2-Flash via Token Plan API |
| Streaming | SSE (Server-Sent Events) |
| DOCX | python-docx with localized references heading (en/id/ms/zh) |
| CLI | Click + Rich (token ledger table) |
| Tests | pytest + pytest-asyncio + respx (HTTP mocking) — 54 tests |
| Web Demo | Next.js 16 + TypeScript 5 + Tailwind CSS v4 |
| Deployment | Vercel (web) + standalone Python package (CLI) |

---

## Getting Started

```bash
# Clone the repository
git clone https://github.com/gnpa910/hermes-mimo-writer.git
cd hermes-mimo-writer

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install with development extras
pip install -e ".[dev]"

# Configure your MiMo Token Plan API key
cp .env.example .env
# Edit .env and set MIMO_API_KEY=tp-...

# Verify the endpoint is reachable
hermes-writer health
```

---

## CLI Usage

```bash
# Run the full pipeline
hermes-writer run \
    --brief examples/brief.md \
    --output essay.docx \
    -s examples/style_sample_1.txt \
    -s examples/style_sample_2.txt

# Skip the AI sanitizer pass (faster, lower quality)
hermes-writer run --brief brief.md --output draft.docx --skip-sanitize

# Estimate token cost without running
hermes-writer estimate --brief brief.md

# Health check the MiMo endpoint
hermes-writer health
```

After a run, the token ledger prints a per-agent breakdown:

```
       Pipeline Token Ledger
┌────────────────────┬─────────┐
│ Agent              │  Tokens │
├────────────────────┼─────────┤
│ ai_sanitizer       │  46,219 │
│ brief_parser       │   2,107 │
│ citation_manager   │   8,341 │
│ content_drafter    │  54,802 │
│ outline_drafter    │  10,156 │
│ style_profiler     │   5,418 │
│ TOTAL              │ 127,043 │
└────────────────────┴─────────┘

Output: essay.docx
Words: 1,032
```

---

## Web Demo

The `web/` directory contains a Next.js 16 app deployed on Vercel that demonstrates the **AISanitizer** agent live with token-by-token SSE streaming. Paste a paragraph of AI-generated text, watch MiMo rewrite it in real time.

```bash
cd web
npm install
npm run dev
# open http://localhost:3000
```

**Live demo:** https://hermes-mimo-writer.vercel.app

---

## Project Structure

```
hermes-mimo-writer/
├── src/
│   └── writing_suite/
│       ├── __init__.py
│       ├── cli.py                  # Click CLI entrypoint (hermes-writer)
│       ├── config.py               # .env-driven Settings
│       ├── models.py               # Brief, StyleProfile, Outline, Draft, Citation, TokenLedger
│       ├── mimo_client.py          # Async MiMo Token Plan client (chat + SSE)
│       ├── pipeline.py             # 7-agent orchestrator
│       └── agents/
│           ├── base.py             # Agent[InputT, OutputT] abstract base
│           ├── brief_parser.py     # 1. Brief Parser
│           ├── style_profiler.py   # 2. Style Profiler
│           ├── outline_drafter.py  # 3. Outline Drafter
│           ├── content_drafter.py  # 4. Content Drafter (parallel)
│           ├── ai_sanitizer.py     # 5. AI-Detector Sanitizer (parallel)
│           ├── citation_manager.py # 6. Citation Manager
│           └── docx_assembler.py   # 7. DOCX Assembler (local)
│
├── tests/
│   ├── conftest.py                 # Shared pytest fixtures
│   ├── test_brief_parser.py
│   ├── test_style_profiler.py
│   ├── test_outline_drafter.py
│   ├── test_content_drafter.py
│   ├── test_ai_sanitizer.py
│   ├── test_citation_manager.py
│   ├── test_docx_assembler.py
│   ├── test_mimo_client.py
│   ├── test_models.py
│   ├── test_config.py
│   └── test_pipeline_integration.py
│
├── web/                            # Next.js 16 demo (Vercel deployment)
│   ├── app/
│   │   ├── page.tsx                # Landing + sanitizer playground
│   │   ├── layout.tsx
│   │   ├── globals.css
│   │   └── api/
│   │       └── sanitize/
│   │           └── route.ts        # MiMo SSE proxy endpoint
│   ├── package.json
│   ├── tsconfig.json
│   └── next.config.ts
│
├── examples/
│   ├── brief.md
│   ├── style_sample_1.txt
│   └── style_sample_2.txt
│
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── .env.example
├── LICENSE
└── README.md
```

---

## API Reference

### `POST /api/sanitize` (web demo)

Proxies AI-detector sanitization requests to MiMo with SSE streaming.

| Property | Value |
|----------|-------|
| Endpoint | `https://token-plan-sgp.xiaomimimo.com/v1/chat/completions` |
| Auth | `api-key` header (MiMo Token Plan format) |
| Model | `mimo-v2.5-pro` |
| Streaming | SSE token-by-token |

**Request body:**

```json
{
  "text": "The original AI-generated paragraph to sanitize...",
  "language": "en",
  "register": "formal"
}
```

**Response:** `text/event-stream`, `data: <chunk>` lines per token.

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MIMO_API_KEY` | Yes | — | MiMo Token Plan API key (`tp-...`) |
| `MIMO_ENDPOINT` | No | `https://token-plan-sgp.xiaomimimo.com/v1` | Override for self-hosted gateways |
| `MIMO_MODEL` | No | `mimo-v2.5-pro` | Heavy-reasoning model |
| `MIMO_MODEL_LITE` | No | `mimo-v2-flash` | Cheap-classification model |
| `OUTPUT_DIR` | No | `./output` | Where to write DOCX files |
| `MIMO_TIMEOUT` | No | `120` | HTTP timeout in seconds |
| `MIMO_MAX_RETRIES` | No | `3` | Retry attempts on transient failures |

---

## Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=writing_suite --cov-report=term-missing

# Run a single agent's tests
pytest tests/test_outline_drafter.py -v
```

54 tests cover every agent's success and edge-case paths, the MiMo client's chat/stream/error paths, the pipeline orchestrator's full flow, and config loading. HTTP calls are mocked via `respx` so the suite runs offline in <1 second.

---

## License

MIT — see [LICENSE](LICENSE).

---

<p align="center">
  Built with Python 3.10+, Next.js 16, and Hermes Agent<br/>
  AI powered by <a href="https://platform.xiaomimimo.com">Xiaomi MiMo V2.5 Pro</a>
</p>
