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
];

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

async function toolCall(name, args) {
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
  async fetch(request) {
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
          const out = await toolCall(params?.name, params?.arguments || {});
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
