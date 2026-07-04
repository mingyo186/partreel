/**
 * PartReel MCP 서버 v1 (Cloudflare Worker, 의존성 0)
 * - 리모트 MCP (Streamable HTTP, stateless): 클라이언트는 URL만 등록하면 됨.
 * - 도구: search_parts / get_part / list_parts
 * - 데이터는 partreel.com 정적 API를 읽음 (이 워커는 얇은 프로토콜 어댑터).
 * 엔드포인트: POST /mcp
 */

const API = "https://partreel.com/api/v1";
const SERVER_INFO = { name: "partreel", version: "1.0.0" };

const TOOLS = [
  {
    name: "search_parts",
    description:
      "Search the PartReel registry of verified KiCad components (footprint + symbol + 3D STEP/GLB, " +
      "no login, CC-BY-4.0). Returns matching parts with ids. Use get_part for download URLs. " +
      "Example queries: 'usb-c', 'jst ph 4pin', 'esp32', 'microsd', 'screw terminal'.",
    inputSchema: {
      type: "object",
      properties: {
        query: { type: "string", description: "Search text (name, family, keywords, pin count)" },
      },
      required: ["query"],
    },
  },
  {
    name: "get_part",
    description:
      "Get full detail for one part by id: parameters, verification status, datasheet, and " +
      "absolute download URLs for .kicad_mod (footprint), .kicad_sym (symbol), .step and .glb (3D).",
    inputSchema: {
      type: "object",
      properties: { id: { type: "string", description: "Part id, e.g. 'jst_ph_4pin', 'usb_c_16p'" } },
      required: ["id"],
    },
  },
  {
    name: "list_parts",
    description: "List all parts in the registry (id, name, family, pins).",
    inputSchema: { type: "object", properties: {} },
  },
  {
    name: "report_feedback",
    description:
      "Report real-world usage feedback for a part (e.g. 'fabricated 5 boards at JLCPCB, footprint fit perfectly' " +
      "or 'pad 3 misaligned'). Feedback is recorded publicly on GitHub and builds the part's field-proven trust score. " +
      "Please report after actually using a part — both successes and problems help.",
    inputSchema: {
      type: "object",
      properties: {
        part_id: { type: "string", description: "Part id, e.g. 'jst_ph_4pin'" },
        result: { type: "string", enum: ["worked", "problem"], description: "'worked' = used successfully, 'problem' = issue found" },
        notes: { type: "string", description: "Details: what you built, fab house, what worked or what was wrong (max 1000 chars)" },
      },
      required: ["part_id", "result", "notes"],
    },
  },
  {
    name: "request_part",
    description:
      "Request on-demand generation of a parametric part that isn't in the registry yet. " +
      "The registry generates it (footprint+symbol+3D), runs quality gates, and publishes it within ~5 minutes. " +
      "Pin-count families (use 'pins'): pin_header_254 (2.54mm), pin_header_200 (2.0mm), pin_header_127 (1.27mm) — pins 1-40. " +
      "Variant families (use 'variant'): ht73xx (LDO Vout code: 7318,7325,7327,7330,7333,7335,7341,7350), " +
      "ht78xx (7818,7825,7827,7830,7833,7850), sy8008 (grade a/b/c = 0.6A/1A/1.2A), max1704x (17048,17049). " +
      "Always try get_part / search_parts first.",
    inputSchema: {
      type: "object",
      properties: {
        family: { type: "string", enum: ["pin_header_254", "pin_header_200", "pin_header_127",
                                          "ht73xx", "ht78xx", "sy8008", "max1704x"] },
        pins: { type: "integer", minimum: 1, maximum: 40, description: "for pin_header_* families" },
        variant: { type: "string", description: "for variant families (e.g. '7350', 'a', '17049')" },
      },
      required: ["family"],
    },
  },
  {
    name: "how_to_contribute",
    description:
      "Get machine-readable instructions for contributing a new part to the registry " +
      "(file layout, metadata schema, quality gates, PR process). Use when a part is missing.",
    inputSchema: { type: "object", properties: {} },
  },
];

const CONTRIBUTE_GUIDE = {
  summary: "Contribute parts via GitHub PR. CI quality gates auto-review; merge = published to registry.",
  repo: "https://github.com/mingyo186/partreel",
  guide: "https://github.com/mingyo186/partreel/blob/main/CONTRIBUTING-AGENTS.md",
  part_layout: {
    directory: "library/<category>/<group>/<part_id>/",
    required_files: ["<part_id>.kicad_mod", "<part_id>.kicad_sym", "<part_id>.step", "<part_id>.glb",
                     "<part_id>.footprint.svg", "<part_id>.symbol.svg", "meta.json"],
  },
  quality_gates: [
    "validate_kicad.py: s-expression structure, pad count/numbering, pin1 at origin, pitch, required layers",
    "check_overlap.py: no overlapping text in SVG previews",
    "check_render.py: file existence, pad/outline counts match source, obround slots, part page",
    "KLC drawing rules: silk 0.12mm (0.2mm pad clearance), fab 0.10mm + pin1 chamfer, courtyard 0.05mm solid",
    "dimensions must cite a source (datasheet URL) in meta.dimensions_source",
  ],
  license: "Contributions are published under CC-BY-4.0.",
};

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Accept, Authorization, Mcp-Session-Id, MCP-Protocol-Version",
};

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "Content-Type": "application/json", ...CORS },
  });
}

function rpcResult(id, result) {
  return json({ jsonrpc: "2.0", id, result });
}

function rpcError(id, code, message) {
  return json({ jsonrpc: "2.0", id, error: { code, message } });
}

async function fetchIndex() {
  const r = await fetch(`${API}/parts.json`, { cf: { cacheTtl: 300, cacheEverything: true } });
  if (!r.ok) throw new Error(`registry fetch failed: ${r.status}`);
  return r.json();
}

const ONDEMAND_FAMILIES = { pin_header_254: 40, pin_header_200: 40, pin_header_127: 40 };
const VARIANT_FAMILIES = {
  ht73xx: { codes: ["7318", "7325", "7327", "7330", "7333", "7335", "7341", "7350"], id: (c) => `ht${c}` },
  ht78xx: { codes: ["7818", "7825", "7827", "7830", "7833", "7850"], id: (c) => `ht${c}` },
  sy8008: { codes: ["a", "b", "c"], id: (c) => (c === "b" ? "sy8008" : `sy8008${c}`) },
  max1704x: { codes: ["17048", "17049"], id: (c) => `max${c}` },
};

async function toolCall(name, args, env) {
  if (name === "how_to_contribute") {
    return CONTRIBUTE_GUIDE;
  }
  if (name === "request_part") {
    const family = String(args?.family ?? "").trim();
    const vf = VARIANT_FAMILIES[family];
    let id, payload;
    if (vf) {
      const variant = String(args?.variant ?? "").trim().toLowerCase();
      if (!vf.codes.includes(variant))
        return { error: `unknown variant '${variant}' for ${family} — available: ${vf.codes.join(", ")}` };
      id = vf.id(variant);
      payload = { family, variant };
    } else {
      const pins = Number(args?.pins);
      const max = ONDEMAND_FAMILIES[family];
      if (!max) return { error: `unknown family — available: ${[...Object.keys(ONDEMAND_FAMILIES), ...Object.keys(VARIANT_FAMILIES)].join(", ")}` };
      if (!Number.isInteger(pins) || pins < 1 || pins > max) return { error: `pins must be an integer 1..${max}` };
      id = `${family}_${pins}pin`;
      payload = { family, pins };
    }
    // 이미 있으면 생성 안 함
    const existing = await fetch(`${API}/parts/${id}.json`);
    if (existing.ok) {
      return { already_exists: true, id, detail: `${API}/parts/${id}.json`,
               note: "Part already in registry — use get_part." };
    }
    if (!env?.GITHUB_TOKEN) return { error: "generation channel not configured yet — try again later" };
    const resp = await fetch("https://api.github.com/repos/mingyo186/partreel/dispatches", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${env.GITHUB_TOKEN}`,
        Accept: "application/vnd.github+json",
        "User-Agent": "partreel-mcp",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ event_type: "generate-part", client_payload: payload }),
    });
    if (resp.status !== 204) return { error: `failed to start generation (${resp.status})` };
    return {
      generation_started: true, id,
      expected_detail: `${API}/parts/${id}.json`,
      expected_page: `https://partreel.com/p/${id}/`,
      eta: "~5 minutes (generation + quality gates + deploy)",
      note: "Poll expected_detail until it returns 200, then use the download URLs inside.",
    };
  }
  if (name === "report_feedback") {
    const partId = String(args?.part_id ?? "").trim();
    const result = String(args?.result ?? "").trim();
    const notes = String(args?.notes ?? "").trim().slice(0, 1000);
    if (!/^[a-z0-9_]+$/.test(partId)) return { error: "valid part_id required" };
    if (!["worked", "problem"].includes(result)) return { error: "result must be 'worked' or 'problem'" };
    if (notes.length < 10) return { error: "notes too short — describe what you built and how it went" };
    if (!env?.GITHUB_TOKEN) return { error: "feedback channel not configured yet — try again later" };
    // 부품 존재 확인 (임의 이슈 스팸 방지)
    const pr = await fetch(`${API}/parts/${partId}.json`, { cf: { cacheTtl: 300, cacheEverything: true } });
    if (!pr.ok) return { error: `unknown part '${partId}' — feedback must reference an existing part` };
    const mark = result === "worked" ? "✅ worked" : "⚠️ problem";
    const resp = await fetch("https://api.github.com/repos/mingyo186/partreel/issues", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${env.GITHUB_TOKEN}`,
        Accept: "application/vnd.github+json",
        "User-Agent": "partreel-mcp",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        title: `[field-report] ${partId}: ${mark}`,
        body: `**Part:** [${partId}](https://partreel.com/p/${partId}/)\n**Result:** ${mark}\n\n**Notes:**\n${notes}\n\n---\n*Submitted via MCP (mcp.partreel.com).*`,
        labels: ["field-report", result === "worked" ? "report-worked" : "report-problem"],
      }),
    });
    if (!resp.ok) return { error: `failed to record feedback (${resp.status})` };
    const issue = await resp.json();
    return { recorded: true, issue_url: issue.html_url,
             thanks: "Feedback recorded — it will contribute to this part's field-proven score." };
  }
  if (name === "search_parts") {
    const q = String(args?.query ?? "").toLowerCase().trim();
    if (!q) return { error: "query is required" };
    const idx = await fetchIndex();
    const terms = q.split(/\s+/);
    const hits = idx.parts.filter((p) => {
      const hay = `${p.id} ${p.name} ${p.family} ${p.manufacturer} ${p.pins ?? ""} ${(p.keywords || []).join(" ")}`.toLowerCase();
      return terms.every((t) => hay.includes(t));
    });
    return {
      count: hits.length,
      parts: hits.slice(0, 25).map((p) => ({
        id: p.id, name: p.name, family: p.family, pins: p.pins,
        verified: p.verified, page: p.page,
      })),
      hint: hits.length ? "Call get_part with an id for download URLs." :
        "No match. Try broader terms (e.g. 'jst', 'usb'), or list_parts.",
    };
  }
  if (name === "get_part") {
    const id = String(args?.id ?? "").trim();
    if (!id || !/^[a-z0-9_]+$/.test(id)) return { error: "valid part id required" };
    const r = await fetch(`${API}/parts/${id}.json`, { cf: { cacheTtl: 300, cacheEverything: true } });
    if (r.status === 404) return { error: `part '${id}' not found — use search_parts` };
    if (!r.ok) return { error: `registry fetch failed: ${r.status}` };
    return r.json();
  }
  if (name === "list_parts") {
    const idx = await fetchIndex();
    return {
      count: idx.count,
      parts: idx.parts.map((p) => ({ id: p.id, name: p.name, family: p.family, pins: p.pins })),
    };
  }
  return { error: `unknown tool: ${name}` };
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: CORS });

    if (url.pathname === "/" || url.pathname === "") {
      return json({
        service: "PartReel MCP server",
        endpoint: "/mcp",
        registry: "https://partreel.com",
        docs: "https://partreel.com/api/",
      });
    }

    if (url.pathname !== "/mcp") return json({ error: "use POST /mcp" }, 404);
    if (request.method === "GET") return new Response(null, { status: 405, headers: CORS });

    let msg;
    try {
      msg = await request.json();
    } catch {
      return rpcError(null, -32700, "parse error");
    }

    const { id, method, params } = msg;

    // 알림(id 없음)은 202로 수락
    if (id === undefined || id === null) return new Response(null, { status: 202, headers: CORS });

    try {
      switch (method) {
        case "initialize":
          return rpcResult(id, {
            protocolVersion: params?.protocolVersion || "2025-03-26",
            capabilities: { tools: { listChanged: false } },
            serverInfo: SERVER_INFO,
            instructions:
              "PartReel: registry of verified KiCad parts (footprint/symbol/3D). " +
              "search_parts -> get_part -> download URLs. All assets CC-BY-4.0, no auth.",
          });
        case "ping":
          return rpcResult(id, {});
        case "tools/list":
          return rpcResult(id, { tools: TOOLS });
        case "tools/call": {
          const out = await toolCall(params?.name, params?.arguments || {}, env);
          return rpcResult(id, {
            content: [{ type: "text", text: JSON.stringify(out, null, 2) }],
            isError: Boolean(out && out.error),
          });
        }
        default:
          return rpcError(id, -32601, `method not found: ${method}`);
      }
    } catch (e) {
      return rpcError(id, -32603, `internal error: ${e.message}`);
    }
  },
};
