/**
 * SSE proxy to the Xiaomi MiMo Token Plan endpoint.
 *
 * Accepts { text, language, register } and streams back token-by-token
 * sanitized output. Mirrors the server-side AISanitizerAgent's prompt
 * so the demo matches the real CLI behavior.
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

export async function POST(req: Request) {
  const apiKey = process.env.MIMO_API_KEY;
  if (!apiKey) {
    return new Response("MIMO_API_KEY not configured", { status: 500 });
  }

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
