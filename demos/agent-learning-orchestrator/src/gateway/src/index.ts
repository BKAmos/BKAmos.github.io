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

export class LearningLoopMcpAgent extends McpAgent<Env> {
  server = new McpServer({
    name: "rna-seq-trust-de-component",
    version: "0.1.0",
  });

  async init() {
    this.server.tool(
      "start_component",
      "Start the trust-before-expression micro-loop (contamination → DESeq → report).",
      {
        max_internal_cycles: z.number().int().min(1).max(3).default(3),
      },
      async (input) => {
        const data = await postJson(this.env, "/tools/start_component", input);
        return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] };
      },
    );

    this.server.tool(
      "get_component_status",
      "Poll component run state and cycle timeline.",
      { component_run_id: z.string() },
      async ({ component_run_id }) => {
        const data = await getJson(this.env, `/components/${component_run_id}`);
        return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] };
      },
    );

    this.server.tool(
      "get_component_summary",
      "Return component_summary.json for parent orchestrator handoff.",
      { component_run_id: z.string() },
      async ({ component_run_id }) => {
        const data = await getJson(this.env, `/components/${component_run_id}/summary`);
        return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] };
      },
    );

    this.server.tool(
      "submit_to_parent",
      "POST finalized component_summary.json to the parent orchestrator webhook.",
      {
        component_run_id: z.string(),
        parent_url: z.string().url().optional(),
      },
      async (input) => {
        const data = await postJson(this.env, "/tools/submit_to_parent", input);
        return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] };
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

    return LearningLoopMcpAgent.serve("/mcp").fetch(request, env, ctx);
  },
};
