"use client";

import { useState, useRef } from "react";

const SAMPLE_INPUT = `Artificial intelligence has revolutionized education by enabling personalized learning experiences for students. In today's fast-paced world, it is important to note that AI-driven platforms can adapt to individual learning styles, thereby enhancing student engagement. Furthermore, these systems utilize sophisticated algorithms to navigate the landscape of educational content. As we delve into this topic, we discover that the implications are far-reaching and profound.`;

export default function HomePage() {
  const [input, setInput] = useState(SAMPLE_INPUT);
  const [output, setOutput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [language, setLanguage] = useState<"en" | "id" | "ms" | "zh">("en");
  const [register, setRegister] = useState<"formal" | "semi-formal" | "casual">(
    "formal",
  );
  const [tokenCount, setTokenCount] = useState(0);
  const [demoMode, setDemoMode] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  async function runSanitize() {
    if (input.trim().length < 30) {
      setError("Paste at least 30 characters to sanitize.");
      return;
    }
    setError(null);
    setOutput("");
    setStreaming(true);
    setTokenCount(0);
    setDemoMode(false);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const resp = await fetch("/api/sanitize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: input, language, register }),
        signal: controller.signal,
      });

      if (!resp.ok) {
        const txt = await resp.text();
        throw new Error(`${resp.status}: ${txt.slice(0, 200)}`);
      }
      if (!resp.body) throw new Error("no response body");

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      const isDemoMode = resp.headers.get("X-MiMo-Mode") === "demo-fallback";
      if (isDemoMode) {
        setOutput(""); // ensure clean start
      }

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const payload = line.slice(6).trim();
          if (payload === "[DONE]") continue;
          try {
            const parsed = JSON.parse(payload);
            if (parsed.meta) {
              setDemoMode(true);
            }
            if (parsed.chunk) {
              setOutput((prev) => prev + parsed.chunk);
              setTokenCount((n) => n + 1);
            }
          } catch {
            // skip
          }
        }
      }
    } catch (e: unknown) {
      if (e instanceof Error && e.name !== "AbortError") {
        setError(e.message);
      }
    } finally {
      setStreaming(false);
      abortRef.current = null;
    }
  }

  function stopStream() {
    abortRef.current?.abort();
  }

  return (
    <main className="min-h-screen px-6 py-10 md:px-12 lg:px-24">
      {/* HERO */}
      <header className="mb-12 max-w-5xl">
        <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-[var(--border)] bg-[var(--panel)] px-3 py-1 text-xs">
          <span className="h-2 w-2 rounded-full bg-[var(--accent)]" />
          <span className="text-[var(--muted)]">Powered by</span>
          <span className="font-semibold text-[var(--accent)]">
            Xiaomi MiMo V2.5 Pro
          </span>
        </div>
        <h1 className="mb-3 text-4xl font-bold leading-tight md:text-6xl">
          Hermes-MiMo{" "}
          <span className="bg-gradient-to-r from-[var(--accent)] to-[var(--accent-2)] bg-clip-text text-transparent">
            Writer
          </span>
        </h1>
        <p className="max-w-2xl text-lg text-[var(--muted)]">
          Multi-agent academic writing pipeline. Seven specialized agents
          collaborate via Hermes Agent + MiMo Token Plan API to produce
          citation-backed, style-matched, AI-detector-resistant essays.
        </p>
        <div className="mt-4 flex flex-wrap gap-3 text-xs text-[var(--muted)]">
          <a
            href="https://github.com/gnpa910/hermes-mimo-writer"
            className="rounded border border-[var(--border)] px-3 py-1 hover:border-[var(--accent)]"
          >
            GitHub →
          </a>
          <a
            href="https://platform.xiaomimimo.com/"
            className="rounded border border-[var(--border)] px-3 py-1 hover:border-[var(--accent-2)]"
          >
            MiMo Platform →
          </a>
          <span className="rounded border border-[var(--border)] px-3 py-1">
            7 agents · 54 tests · MIT
          </span>
        </div>
      </header>

      {/* PLAYGROUND */}
      <section className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-lg border border-[var(--border)] bg-[var(--panel)] p-5">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-[var(--muted)]">
              Original (AI-generated)
            </h2>
            <span className="text-xs text-[var(--muted)]">
              {input.length} chars
            </span>
          </div>
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={streaming}
            rows={12}
            className="w-full resize-none rounded border border-[var(--border)] bg-black/30 p-3 font-mono text-sm leading-relaxed outline-none focus:border-[var(--accent)]"
          />
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <select
              value={language}
              onChange={(e) =>
                setLanguage(e.target.value as "en" | "id" | "ms" | "zh")
              }
              disabled={streaming}
              className="rounded border border-[var(--border)] bg-black/30 px-2 py-1 text-xs"
            >
              <option value="en">English</option>
              <option value="id">Bahasa Indonesia</option>
              <option value="ms">Bahasa Melayu</option>
              <option value="zh">中文</option>
            </select>
            <select
              value={register}
              onChange={(e) =>
                setRegister(
                  e.target.value as "formal" | "semi-formal" | "casual",
                )
              }
              disabled={streaming}
              className="rounded border border-[var(--border)] bg-black/30 px-2 py-1 text-xs"
            >
              <option value="formal">Formal</option>
              <option value="semi-formal">Semi-formal</option>
              <option value="casual">Casual</option>
            </select>
            {!streaming ? (
              <button
                onClick={runSanitize}
                className="ml-auto rounded bg-[var(--accent)] px-4 py-1.5 text-sm font-semibold text-black glow-orange hover:opacity-90"
              >
                ▶ Sanitize
              </button>
            ) : (
              <button
                onClick={stopStream}
                className="ml-auto rounded border border-[var(--border)] px-4 py-1.5 text-sm hover:border-[var(--accent)]"
              >
                ■ Stop
              </button>
            )}
          </div>
        </div>

        <div className="rounded-lg border border-[var(--border)] bg-[var(--panel)] p-5">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-[var(--muted)]">
              Sanitized (MiMo V2.5 Pro)
            </h2>
            <span className="text-xs text-[var(--muted)]">
              {tokenCount > 0 && `${tokenCount} chunks streamed`}
            </span>
          </div>
          <div
            className={`min-h-[18rem] whitespace-pre-wrap rounded border border-[var(--border)] bg-black/30 p-3 font-mono text-sm leading-relaxed ${
              streaming ? "stream-cursor" : ""
            }`}
          >
            {output ||
              (streaming ? "" : (
                <span className="text-[var(--muted)]">
                  Output will stream here token-by-token via SSE.
                </span>
              ))}
          </div>
          {error && (
            <p className="mt-3 rounded border border-red-900 bg-red-950/40 p-2 text-xs text-red-300">
              {error}
            </p>
          )}
          {demoMode && (
            <p className="mt-3 rounded border border-amber-700/60 bg-amber-950/30 p-2 text-xs text-amber-200">
              ⚡ <strong>Demo mode</strong> — this deployment is showing a cached
              sanitization to keep the streaming UX functional. Set a real
              <code className="mx-1 rounded bg-black/40 px-1">MIMO_API_KEY</code>
              env var on your fork to call the live Token Plan API.
            </p>
          )}
        </div>
      </section>

      {/* AGENTS PANEL */}
      <section className="mt-16 max-w-5xl">
        <h2 className="mb-6 text-2xl font-bold">The Seven Agents</h2>
        <div className="grid gap-3 md:grid-cols-2">
          {AGENTS.map((a) => (
            <div
              key={a.name}
              className="fade-in rounded-lg border border-[var(--border)] bg-[var(--panel)] p-4"
            >
              <div className="mb-1 flex items-center justify-between">
                <span className="text-xs font-mono text-[var(--accent)]">
                  {a.id}
                </span>
                <span className="rounded bg-black/40 px-2 py-0.5 font-mono text-xs text-[var(--accent-2)]">
                  {a.model}
                </span>
              </div>
              <h3 className="text-base font-semibold">{a.name}</h3>
              <p className="mt-1 text-sm text-[var(--muted)]">{a.desc}</p>
              <p className="mt-2 text-xs text-[var(--muted)]">
                Typical: {a.tokens} tokens
              </p>
            </div>
          ))}
        </div>
      </section>

      <footer className="mt-20 max-w-5xl border-t border-[var(--border)] pt-8 text-sm text-[var(--muted)]">
        Built with Next.js 16 · React 19 · Hermes Agent + MiMo Token Plan API ·{" "}
        <a
          className="underline hover:text-[var(--accent)]"
          href="https://github.com/gnpa910/hermes-mimo-writer"
        >
          source
        </a>
      </footer>
    </main>
  );
}

const AGENTS = [
  {
    id: "01",
    name: "BriefParserAgent",
    model: "mimo-v2-flash",
    desc: "Extracts structured Brief from a free-form rubric. Cheap classification work.",
    tokens: "1K–3K",
  },
  {
    id: "02",
    name: "StyleProfilerAgent",
    model: "mimo-v2.5-pro",
    desc: "Builds a style fingerprint from sample texts: register, sentence length, POV, phrases to avoid.",
    tokens: "2K–8K",
  },
  {
    id: "03",
    name: "OutlineDrafterAgent",
    model: "mimo-v2.5-pro",
    desc: "Section-by-section outline with target word counts. MiMo's reasoning chain holds the structure.",
    tokens: "5K–15K",
  },
  {
    id: "04",
    name: "ContentDrafterAgent",
    model: "mimo-v2.5-pro",
    desc: "Drafts each section in parallel (semaphore=3) with [Author, YYYY] citation placeholders.",
    tokens: "30K–80K",
  },
  {
    id: "05",
    name: "AISanitizerAgent",
    model: "mimo-v2.5-pro",
    desc: "Rewrites prose to vary sentence length, replace AI giveaways, preserve citations.",
    tokens: "25K–60K",
  },
  {
    id: "06",
    name: "CitationManagerAgent",
    model: "mimo-v2.5-pro",
    desc: "Resolves [Surname_Year] markers into formatted references in the requested style.",
    tokens: "4K–12K",
  },
  {
    id: "07",
    name: "DocxAssemblerAgent",
    model: "local",
    desc: "Pure local logic: emits .docx with title page, language-aware references heading.",
    tokens: "0",
  },
];
