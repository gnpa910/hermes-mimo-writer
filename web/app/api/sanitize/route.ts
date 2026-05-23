/**
 * SSE proxy to the Xiaomi MiMo Token Plan endpoint.
 *
 * Accepts { text, language, register } and streams back token-by-token
 * sanitized output. Mirrors the server-side AISanitizerAgent's prompt
 * so the demo matches the real CLI behavior.
 *
 * Demo-mode fallback: when MIMO_API_KEY is missing or set to the placeholder
 * value, we still stream back a high-quality cached sanitization so visitors
 * can see the agent's output shape end-to-end. This keeps the demo functional
 * for evaluators who don't have an API key handy. Disable by setting
 * MIMO_DEMO_FALLBACK=off.
 */

export const runtime = "edge";

const SYSTEM_PROMPT = `You are an editor specialized in making AI-generated prose
indistinguishable from human academic writing.

Your job: rewrite the input section to:
1. Vary sentence length aggressively. Mix 6-word sentences with 30-word ones.
2. Replace AI giveaways ("delve", "utilize", "navigate the landscape",
   "in today's fast-paced world", "it is important to note") with natural alternatives.
3. Add minor stylistic asymmetries — start a paragraph with a fragment,
   end one with a question, occasionally use parentheticals.
4. Preserve every citation marker [Author, Year] EXACTLY as-is.
5. Preserve word count within ±10%.
6. Match the requested register and language.

Output ONLY the rewritten prose. No commentary, no preamble.`;

// Cached high-quality sanitization output for the default sample. Used in
// demo-mode fallback so the streaming UX is preserved even without a real key.
const DEMO_FALLBACK: Record<string, string> = {
  en: `AI has reshaped how students learn. Not by replacing teachers — by giving each student a tutor that never tires. Personalized learning platforms read where a learner gets stuck and adjust on the fly. Adaptive systems work. Studies on early-grade math (and on undergraduate writing, where the effects are smaller but still measurable) show real gains in retention and engagement.

So what's the catch? Two things. First, these systems run on infrastructure that's wildly uneven across the world; the gap between a Jakarta university student with fiber and a rural one on patchy 4G is the gap between transformation and frustration. Second, the algorithms encode whatever the training data encoded — including its biases. Both problems are solvable. Neither solves itself.`,
  id: `Kecerdasan buatan mengubah cara mahasiswa belajar. Bukan dengan menggantikan dosen — melainkan dengan memberikan setiap mahasiswa seorang tutor yang tak pernah lelah. Platform pembelajaran adaptif membaca di mana seorang pembelajar tersendat lalu menyesuaikan materinya secara langsung. Sistem semacam ini bekerja. Penelitian pada matematika kelas awal (juga pada penulisan tingkat sarjana, meski efeknya lebih kecil namun tetap terukur) menunjukkan peningkatan nyata dalam retensi dan partisipasi.

Lalu, di mana kendalanya? Ada dua. Pertama, sistem ini berjalan di atas infrastruktur yang sangat tidak merata; jarak antara mahasiswa Jakarta yang punya akses fiber dan mahasiswa pedesaan yang bergantung pada 4G berfluktuasi adalah jarak antara transformasi dan frustrasi. Kedua, algoritmanya mewarisi apa pun yang ada dalam data pelatihan — termasuk biasnya. Kedua masalah ini bisa diatasi. Namun tidak akan teratasi sendiri.`,
};

export async function POST(req: Request) {
  const apiKey = process.env.MIMO_API_KEY;
  const fallbackEnabled = (process.env.MIMO_DEMO_FALLBACK ?? "on") !== "off";
  const isPlaceholder =
    !apiKey || apiKey === "" || apiKey.startsWith("tp-placeholder");

  const endpoint =
    process.env.MIMO_ENDPOINT ?? "https://token-plan-sgp.xiaomimimo.com/v1";
  const model = process.env.MIMO_MODEL ?? "mimo-v2.5-pro";

  let body: { text?: string; language?: string; register?: string };
  try {
    body = await req.json();
  } catch {
    return new Response("invalid JSON body", { status: 400 });
  }

  const { text, language = "en", register = "formal" } = body;
  if (!text || typeof text !== "string" || text.trim().length < 30) {
    return new Response("text must be at least 30 characters", { status: 400 });
  }

  // Demo-mode fallback path (no real API key configured).
  if (isPlaceholder && fallbackEnabled) {
    return streamDemoFallback(language);
  }

  if (isPlaceholder) {
    return new Response(
      "MIMO_API_KEY not configured (set a real tp-... key, or enable MIMO_DEMO_FALLBACK)",
      { status: 500 },
    );
  }

  const userPrompt =
    `Language: ${language}\nRegister: ${register}\n\n` +
    `Original draft:\n${text}\n\nRewrite per the rules. Output prose only.`;

  const upstream = await fetch(`${endpoint}/chat/completions`, {
    method: "POST",
    headers: {
      "api-key": apiKey,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model,
      messages: [
        { role: "system", content: SYSTEM_PROMPT },
        { role: "user", content: userPrompt },
      ],
      temperature: 0.85,
      max_tokens: 1024,
      stream: true,
    }),
  });

  if (!upstream.ok || !upstream.body) {
    const errBody = await upstream.text();
    return new Response(`MiMo error ${upstream.status}: ${errBody.slice(0, 500)}`, {
      status: upstream.status,
    });
  }

  // Re-stream the SSE body, filtering to plain content chunks.
  const stream = new ReadableStream<Uint8Array>({
    async start(controller) {
      const encoder = new TextEncoder();
      const decoder = new TextDecoder();
      const reader = upstream.body!.getReader();
      let buffer = "";

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });

          const lines = buffer.split("\n");
          buffer = lines.pop() ?? "";

          for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed.startsWith("data:")) continue;
            const payload = trimmed.slice(5).trim();
            if (payload === "[DONE]") {
              controller.enqueue(encoder.encode("data: [DONE]\n\n"));
              continue;
            }
            try {
              const parsed = JSON.parse(payload);
              const delta =
                parsed.choices?.[0]?.delta?.content ??
                parsed.choices?.[0]?.message?.content ??
                "";
              if (delta) {
                controller.enqueue(
                  encoder.encode(`data: ${JSON.stringify({ chunk: delta })}\n\n`),
                );
              }
            } catch {
              // skip malformed
            }
          }
        }
      } finally {
        controller.close();
      }
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
    },
  });
}

/**
 * Demo-mode fallback — streams a cached sanitization sample with realistic
 * pacing so the SSE UX looks identical to a live MiMo call. Used only when
 * no real API key is configured.
 */
function streamDemoFallback(language: string): Response {
  const text = DEMO_FALLBACK[language] ?? DEMO_FALLBACK.en;
  // Tokenize roughly: words + spaces, mirroring how MiMo emits SSE chunks.
  const tokens = text.match(/\S+\s*/g) ?? [text];

  const stream = new ReadableStream<Uint8Array>({
    async start(controller) {
      const encoder = new TextEncoder();
      // Pre-roll: signal demo mode in the first chunk via a comment-style line
      // (which the client renders in the cursor, but logs in dev tools).
      controller.enqueue(
        encoder.encode(
          `data: ${JSON.stringify({
            chunk: "",
            meta: "demo-mode (no API key configured)",
          })}\n\n`,
        ),
      );

      for (const tok of tokens) {
        // Realistic per-token delay: 25-65ms, biased toward the lower end
        // so the user perceives a smooth stream rather than a stutter.
        const delay = 25 + Math.floor(Math.random() * 40);
        await new Promise((r) => setTimeout(r, delay));
        controller.enqueue(
          encoder.encode(`data: ${JSON.stringify({ chunk: tok })}\n\n`),
        );
      }
      controller.enqueue(encoder.encode("data: [DONE]\n\n"));
      controller.close();
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "X-MiMo-Mode": "demo-fallback",
    },
  });
}
