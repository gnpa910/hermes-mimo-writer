/**
 * SSE proxy to the Xiaomi MiMo Token Plan endpoint.
 *
 * Accepts { text, language, register } and streams back token-by-token
 * sanitized output. Mirrors the server-side AISanitizerAgent's prompt
 * so the demo matches the real CLI behavior.
 *
 * Falls back to a canned demo stream when MIMO_API_KEY is unset or a
 * placeholder, so the public demo remains interactive without leaking
 * production credits.
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

const DEMO_RESPONSE_EN = `Artificial intelligence reshapes education in ways that surprise even its architects. Personalized pathways. That's the real shift. Adaptive platforms read each student's pace and rebuild the lesson around it, not the other way round.

Engagement climbs when the friction of "one size fits all" disappears (the data backs this up). What about the educators? They keep the work that matters most: judgment, mentorship, the unscripted Socratic moment. The algorithms handle the boilerplate.

Will every classroom benefit equally? Probably not. But the gap narrows further each semester, and that's the metric worth tracking.`;

const DEMO_RESPONSE_ID = `Kecerdasan buatan menata ulang pendidikan dengan cara yang kadang mengejutkan para perancangnya sendiri. Pembelajaran personal. Itu pergeseran sebenarnya. Platform adaptif membaca tempo setiap mahasiswa dan menyusun ulang materi mengikuti mereka, bukan sebaliknya.

Partisipasi meningkat ketika gesekan "satu ukuran untuk semua" lenyap (data mendukungnya). Lalu peran dosen? Mereka memegang pekerjaan yang paling penting: pertimbangan, pembimbingan, momen Sokratik yang tidak terskenario. Algoritma menangani sisanya.

Akankah setiap kelas terdampak setara? Mungkin belum. Tetapi jurang itu menyempit setiap semester, dan itulah metrik yang layak dilacak.`;

const DEMO_RESPONSE_MS = `Kecerdasan buatan menyusun semula pendidikan dengan cara yang kadang-kadang mengejutkan pereka asalnya. Pembelajaran peribadi. Itulah peralihan sebenar. Platform adaptif membaca rentak setiap pelajar lalu membina semula pelajaran mengikut mereka, bukan sebaliknya.

Penglibatan meningkat apabila geseran "satu saiz untuk semua" hilang (data menyokongnya). Bagaimana pula dengan pensyarah? Mereka memegang kerja yang paling bererti: pertimbangan, bimbingan, detik Sokratik yang tidak berskrip. Algoritma menguruskan yang rutin.

Adakah setiap bilik darjah mendapat manfaat setara? Mungkin tidak. Tetapi jurang itu menyempit setiap semester, dan itulah metrik yang patut dipantau.`;

const DEMO_RESPONSE_ZH = `人工智能正在以连设计者都意想不到的方式重塑教育。个性化路径。这才是真正的转折。自适应平台读取每位学生的节奏，再围绕节奏重组课程，而不是反过来。

当"千人一面"的摩擦消失，参与度便会攀升（数据支持这一点）。那教师呢？他们继续做最要紧的工作：判断、指导、未经排练的苏格拉底式时刻。算法处理样板部分。

每间教室都能等量受益吗？或许不会。但每一个学期，差距都在缩小——这才是值得追踪的指标。`;

function pickDemoResponse(language: string): string {
  switch (language) {
    case "id":
      return DEMO_RESPONSE_ID;
    case "ms":
      return DEMO_RESPONSE_MS;
    case "zh":
      return DEMO_RESPONSE_ZH;
    default:
      return DEMO_RESPONSE_EN;
  }
}

function isPlaceholderKey(key: string | undefined): boolean {
  if (!key) return true;
  if (key.startsWith("tp-placeholder")) return true;
  if (key.length < 12) return true;
  return false;
}

function makeDemoStream(language: string): ReadableStream<Uint8Array> {
  const text = pickDemoResponse(language);
  const tokens: string[] = [];
  const re = /(\s+|\S+)/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text)) !== null) tokens.push(m[1]);

  const encoder = new TextEncoder();
  return new ReadableStream<Uint8Array>({
    async start(controller) {
      const banner =
        "[DEMO MODE — Token Plan API key not configured on this deployment. " +
        "Streaming a canned MiMo-style response so you can verify the SSE flow. " +
        "Run the CLI locally with a real tp-... key for live MiMo output.]\n\n";
      for (const tok of banner.match(/(\s+|\S+)/g) ?? []) {
        controller.enqueue(
          encoder.encode(`data: ${JSON.stringify({ chunk: tok })}\n\n`),
        );
        await new Promise((r) => setTimeout(r, 18));
      }
      for (const tok of tokens) {
        controller.enqueue(
          encoder.encode(`data: ${JSON.stringify({ chunk: tok })}\n\n`),
        );
        await new Promise((r) => setTimeout(r, /\S/.test(tok) ? 32 : 14));
      }
      controller.enqueue(encoder.encode("data: [DONE]\n\n"));
      controller.close();
    },
  });
}

export async function POST(req: Request) {
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

  const apiKey = process.env.MIMO_API_KEY;
  if (isPlaceholderKey(apiKey)) {
    return new Response(makeDemoStream(language), {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache, no-transform",
        Connection: "keep-alive",
        "X-Demo-Mode": "true",
      },
    });
  }

  const endpoint =
    process.env.MIMO_ENDPOINT ?? "https://token-plan-sgp.xiaomimimo.com/v1";
  const model = process.env.MIMO_MODEL ?? "mimo-v2.5-pro";

  const userPrompt =
    `Language: ${language}\nRegister: ${register}\n\n` +
    `Original draft:\n${text}\n\nRewrite per the rules. Output prose only.`;

  const upstream = await fetch(`${endpoint}/chat/completions`, {
    method: "POST",
    headers: {
      "api-key": apiKey!,
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
    return new Response(
      `MiMo error ${upstream.status}: ${errBody.slice(0, 500)}`,
      { status: upstream.status },
    );
  }

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
                  encoder.encode(
                    `data: ${JSON.stringify({ chunk: delta })}\n\n`,
                  ),
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
