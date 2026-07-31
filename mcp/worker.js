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
      "Get machine-readable instructions for adding a new part to the registry " +
      "(file layout, metadata schema, quality gates, PR process). Use when a part is missing.",
    inputSchema: { type: "object", properties: {} },
  },
];

const CONTRIBUTE_GUIDE = {
  summary: "Your AI builds the part, our CI gates verify it, everyone reuses it. Add it to the registry via GitHub PR; gates auto-review, merge = published (site + API + MCP).",
  one_prompt: "Fetch https://github.com/mingyo186/partreel/blob/main/CONTRIBUTING-AGENTS.md and follow it to create a part for <MPN> from its datasheet, then open a PR.",
  repo: "https://github.com/mingyo186/partreel",
  guide: "https://github.com/mingyo186/partreel/blob/main/CONTRIBUTING-AGENTS.md",
  part_layout: {
    directory: "library/<category>/<group>/<part_id>/",
    required_files: ["<part_id>.kicad_mod", "<part_id>.kicad_sym", "meta.json"],
    optional_files: ["<part_id>.step + <part_id>.glb (without them set meta.tier='verified-2d' — ~40% of the catalog is 2D)"],
    note: "SVG previews / site page / index / API entries are built by CI — do not include them.",
  },
  quality_gates: [
    "validate_kicad.py: s-expression structure, pad count/numbering, pin1 at origin, pitch, required layers",
    "check_overlap.py: no overlapping text in SVG previews",
    "check_render.py: file existence, pad/outline counts match source, obround slots, part page",
    "check_provenance.py: pad-geometry compared against all 15,447 official KiCad footprints — copies of the official (CC-BY-SA) library are rejected automatically",
    "KLC drawing rules: silk 0.12mm (0.2mm pad clearance), fab 0.10mm + pin1 chamfer, courtyard 0.05mm solid",
    "dimensions must cite a source (datasheet URL) in meta.dimensions_source",
  ],
  license: "Original work: CC-BY-4.0. Imports from permissive libraries (MIT/Apache-2.0/CERN-OHL-P/CC-BY) welcome — keep original license in meta.license and record meta.import provenance.",
  credit: "Merged contributors appear in the GitHub contributors graph; report-driven fixes are credited in CREDITS.md and commit trailers.",
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

// === KiCad HTTP 라이브러리 어댑터 (REQUIREMENTS §18-A) ===
// KiCad 8+ 심볼 선택 패널이 호출하는 REST 형태로 카탈로그를 번역.
// 규칙(dev-docs): 모든 값은 문자열, HTTP 200만 처리, 불리언은 "True"/"False" 문자열.
// 심볼 파일 자체는 스펙상 전달 불가(로컬 라이브러리 참조) → PartReel:PLACEHOLDER
// + fields에 실파일 URL 노출 (assets/PartReel.kicad_sym 설치 가이드 참조).
const KICAD_TTL = { categories: 3600, list: 1800, part: 600 };

function kicadJson(obj, ttl) {
  return new Response(JSON.stringify(obj), {
    status: 200,
    headers: {
      "Content-Type": "application/json",
      "Cache-Control": `public, max-age=${ttl}`,
      ...CORS,
    },
  });
}

async function kicadRoute(url) {
  // 관용 파싱: /kicad/v1/..., /kicadv1/... (root_url 끝 슬래시 유무),
  // 이중 슬래시까지 허용 — 클라이언트별 URL 조합 방식 차이 흡수.
  let rest = url.pathname.replace(/^\/kicad/, "").replace(/^\/+/, "");
  rest = rest.replace(/^v1/, "").replace(/^\/+/, "");
  const path = "/" + rest;
  if (path === "/") return kicadJson({ categories: "", parts: "" }, KICAD_TTL.categories);

  // KiCad 10은 선택창을 열 때 부품 상세를 1건씩 전부 선주입한다 (실측 1-2건/초)
  // — 2.1만 전체를 서빙하면 첫 로딩이 수 시간. HTTP lib에는 자체 제작·엄선
  // 부품만 노출 (수입 물결 antmicro_/cern_ 제외, ~500개 = 첫 동기화 수 분).
  // 풀 카탈로그 접근은 사이트 검색·API·MCP가 담당.
  const curated = (parts) =>
    parts.filter((p) => !/^(antmicro_|cern_)/.test(p.id || ""));

  if (path === "/categories.json") {
    const idx = await fetchIndex();
    const cats = [...new Set(curated(idx.parts).map((p) => p.category).filter(Boolean))].sort();
    return kicadJson(
      cats.map((c) => ({ id: String(c), name: String(c) })),
      KICAD_TTL.categories
    );
  }

  let m = path.match(/^\/parts\/category\/([a-z0-9_-]+)\.json$/);
  if (m) {
    const idx = await fetchIndex();
    const items = curated(idx.parts)
      .filter((p) => p.category === m[1])
      .map((p) => ({
        id: String(p.id),
        name: String(p.name || p.id),
        description: String(p.family || ""),
        keywords: (p.keywords || []).join(" "),
      }));
    return kicadJson(items, KICAD_TTL.list);
  }

  m = path.match(/^\/parts\/([a-z0-9_-]+)\.json$/);
  if (m) {
    const r = await fetch(`${API}/parts/${m[1]}.json`, {
      cf: { cacheTtl: KICAD_TTL.part, cacheEverything: true },
    });
    if (!r.ok) return new Response("not found", { status: 404, headers: CORS });
    const p = await r.json();
    const files = p.files || {};
    // 번들 manifest에 있으면 진짜 심볼/풋프린트(PartReel.kicad_sym /
    // PartReel.pretty)를 가리키고, 번들보다 새 부품이면 PLACEHOLDER 폴백.
    let bundled = false;
    try {
      const mf = await fetch("https://partreel.com/assets/kicad-bundle-manifest.json",
                             { cf: { cacheTtl: 1800, cacheEverything: true } });
      if (mf.ok) bundled = ((await mf.json()).symbols || []).includes(p.id);
    } catch (e) { /* manifest 불가 시 폴백 유지 */ }
    return kicadJson(
      {
        id: String(p.id),
        name: String(p.name || p.id),
        symbolIdStr: bundled ? `PartReel:${p.id}` : "PartReel:PLACEHOLDER",
        description: String(p.description || ""),
        keywords: (p.keywords || []).join(" "),
        exclude_from_bom: "False",
        exclude_from_board: "False",
        exclude_from_sim: "True",
        fields: {
          Footprint: {
            value: bundled ? `PartReel:${p.id}` : "",
            visible: "False",
          },
          Datasheet: { value: String(p.datasheet || ""), visible: "False" },
          PartReel: { value: String(p.page || `https://partreel.com/p/${p.id}/`), visible: "False" },
          Footprint_URL: { value: String(files.footprint || ""), visible: "False" },
          Symbol_URL: { value: String(files.symbol || ""), visible: "False" },
          Manufacturer: { value: String(p.manufacturer || ""), visible: "False" },
          MPN: { value: String(p.mpn_pattern || p.name || ""), visible: "False" },
          License: { value: String(p.license || ""), visible: "False" },
          Tier: { value: String(p.tier || (p.verified ? "verified" : "")), visible: "False" },
        },
      },
      KICAD_TTL.part
    );
  }
  return new Response("not found", { status: 404, headers: CORS });
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

    // KiCad HTTP 라이브러리 어댑터 (§18-A): GET /kicad/v1/... (/kicadv1/... 포함)
    if (url.pathname.startsWith("/kicad")) {
      try {
        return await kicadRoute(url);
      } catch (e) {
        return new Response(`error: ${e.message}`, { status: 500, headers: CORS });
      }
    }

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
