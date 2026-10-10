import { analyze, isAnalyzeError } from "@gform/core";

const URL_RE = /^https?:\/\/\S+$/i;

export async function POST(request: Request) {
  let url = "";

  try {
    const body: unknown = await request.json();
    if (body && typeof body === "object" && "url" in body) {
      const raw = (body as { url?: unknown }).url;
      if (typeof raw === "string") url = raw.trim();
    }
  } catch {
    return Response.json({ error: "Request body must be JSON." }, { status: 400 });
  }

  if (!url) {
    return Response.json({ error: "Enter a Google Form URL." }, { status: 400 });
  }
  if (!URL_RE.test(url)) {
    return Response.json(
      { error: "URL must start with http:// or https://" },
      { status: 400 },
    );
  }

  const result = await analyze(url, { timeoutMs: 20_000 });

  if (isAnalyzeError(result)) {
    return Response.json(result, { status: 502 });
  }
  return Response.json(result);
}
