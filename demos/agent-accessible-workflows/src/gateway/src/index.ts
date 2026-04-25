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

export class DeseqMcpAgent extends McpAgent<Env> {
  server = new McpServer({
    name: "deseq-workflow",
    version: "0.1.0",
  });

  async init() {
    this.server.tool(
      "get_synthetic_dataset_info",
      "Return the bundled toy RNA-seq dataset metadata and CSV locations.",
      {},
      async () => {
        const data = await getJson(this.env, "/synthetic-dataset");
        return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] };
      },
    );

    this.server.tool(
      "run_deseq",
      "Submit a DESeq differential expression job.",
      {
        dataset: z.enum(["synthetic", "uploaded"]).default("synthetic"),
        counts_uri: z.string().optional(),
        metadata_uri: z.string().optional(),
        condition_column: z.string().default("condition"),
        reference_level: z.string().default("control"),
        treatment_level: z.string().default("treated"),
        batch_column: z.string().nullable().optional(),
        min_count: z.number().int().min(0).default(10),
      },
      async (input) => {
        const data = await postJson(this.env, "/tools/run_deseq", input);
        return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] };
      },
    );

    this.server.tool(
      "get_job_status",
      "Return DESeq job status, artifact names, and top genes.",
      { job_id: z.string() },
      async ({ job_id }) => {
        const data = await getJson(this.env, `/jobs/${job_id}`);
        return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] };
      },
    );

    this.server.tool(
      "get_deseq_results_summary",
      "Return the top significant genes and output artifact links for a completed job.",
      { job_id: z.string(), top_n: z.number().int().min(1).max(50).default(10) },
      async ({ job_id, top_n }) => {
        const job = (await getJson(this.env, `/jobs/${job_id}`)) as {
          top_genes?: unknown[];
          artifacts?: unknown[];
          status?: string;
        };
        const summary = {
          job_id,
          status: job.status,
          top_genes: (job.top_genes || []).slice(0, top_n),
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

    return DeseqMcpAgent.serve("/mcp").fetch(request, env, ctx);
  },
};
