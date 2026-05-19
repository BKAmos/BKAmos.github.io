import { McpAgent } from "agents/mcp";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";

type Env = {
  API_BASE_URL: string;
  API_JWT?: string;
  MCP_OBJECT: DurableObjectNamespace;
};

function apiHeaders(env: Env, extra: HeadersInit = {}): Headers {
  const headers = new Headers(extra);
  if (env.API_JWT) headers.set("Authorization", `Bearer ${env.API_JWT}`);
  return headers;
}

async function proxyApi(request: Request, env: Env): Promise<Response> {
  const incoming = new URL(request.url);
  const apiBase = new URL(env.API_BASE_URL);
  const proxied = new URL(incoming.pathname.replace(/^\/api/, ""), apiBase);
  proxied.search = incoming.search;

  const headers = apiHeaders(env, request.headers);
  headers.delete("host");

  const response = await fetch(proxied, {
    method: request.method,
    headers,
    body: request.method === "GET" || request.method === "HEAD" ? undefined : request.body,
  });

  const outHeaders = new Headers(response.headers);
  outHeaders.set("Access-Control-Allow-Origin", "*");
  outHeaders.set("Access-Control-Allow-Headers", "authorization,content-type");
  outHeaders.set("Access-Control-Allow-Methods", "GET,POST,OPTIONS");
  return new Response(response.body, { status: response.status, headers: outHeaders });
}

async function postJson(env: Env, path: string, payload: unknown): Promise<unknown> {
  const response = await fetch(new URL(path, env.API_BASE_URL), {
    method: "POST",
    headers: apiHeaders(env, { "Content-Type": "application/json" }),
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(`API ${response.status}: ${await response.text()}`);
  }
  return response.json();
}

async function getJson(env: Env, path: string): Promise<unknown> {
  const response = await fetch(new URL(path, env.API_BASE_URL), {
    headers: apiHeaders(env),
  });
  if (!response.ok) {
    throw new Error(`API ${response.status}: ${await response.text()}`);
  }
  return response.json();
}

export class ContaminationMcpAgent extends McpAgent<Env> {
  server = new McpServer({
    name: "contamination-investigation-workflow",
    version: "0.1.0",
  });

  async init() {
    this.server.tool(
      "list_profiles",
      "Return available synthetic contamination profiles.",
      {},
      async () => {
        const data = await getJson(this.env, "/synthetic-dataset");
        return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] };
      },
    );

    this.server.tool(
      "run_investigation",
      "Submit a contamination investigation run.",
      {
        dataset: z.literal("synthetic").default("synthetic"),
        profile: z.enum(["clean", "low_contam", "high_contam", "edge_case"]).default("low_contam"),
        sample_count: z.number().int().min(6).max(128).default(24),
        synthetic_seed: z.number().int().min(0).max(2147483647).default(42),
        strictness: z.number().min(0.1).max(1.0).default(0.6),
        max_iterations: z.number().int().min(1).max(3).default(2),
      },
      async (input) => {
        const data = await postJson(this.env, "/tools/run_investigation", input);
        return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] };
      },
    );

    this.server.tool(
      "get_status",
      "Return investigation status and manifest payload.",
      { job_id: z.string() },
      async ({ job_id }) => {
        const data = await getJson(this.env, `/jobs/${job_id}`);
        return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] };
      },
    );

    this.server.tool(
      "get_summary",
      "Return verdict, confidence, and key signals for a completed run.",
      { job_id: z.string() },
      async ({ job_id }) => {
        const job = (await getJson(this.env, `/jobs/${job_id}`)) as {
          signals?: unknown[];
          verdict?: unknown;
          artifacts?: unknown[];
          status?: string;
        };
        const summary = {
          job_id,
          status: job.status,
          verdict: job.verdict || null,
          signals: job.signals || [],
          artifacts: job.artifacts || [],
        };
        return { content: [{ type: "text", text: JSON.stringify(summary, null, 2) }] };
      },
    );
  }
}

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);
    if (request.method === "OPTIONS") {
      return new Response(null, {
        headers: {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Headers": "authorization,content-type",
          "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
        },
      });
    }

    if (url.pathname.startsWith("/api/")) {
      return proxyApi(request, env);
    }

    if (url.pathname === "/" || url.pathname === "/healthz") {
      return Response.json({
        status: "ok",
        api_proxy: "/api/*",
        mcp_endpoint: "/mcp",
      });
    }

    return ContaminationMcpAgent.serve("/mcp").fetch(request, env, ctx);
  },
};
