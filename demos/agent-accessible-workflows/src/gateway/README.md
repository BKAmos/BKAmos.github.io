 # Cloudflare Worker MCP gateway

 This Worker is the public front door for the DESeq workflow API. It exposes:

 - `/api/*` proxy routes for the browser UI and power users.
 - `/mcp` JSON-RPC style tool calls for AI agents.

 ## Configure

 ```bash
 npm install
 npx wrangler secret put API_JWT
 npx wrangler secret put API_BASE_URL
 ```

`API_BASE_URL` should point at the backend HTTP API:

- **Local Docker:** `http://localhost:8000`
- **AWS serverless:** the `api_base_url` Terraform output (HTTP API Gateway, no trailing slash), e.g. `https://xxxx.execute-api.us-east-1.amazonaws.com`

Set `API_JWT` to the same bearer token as `API_TOKEN` / Terraform `api_token`.

 ## Deploy

 ```bash
 npm run deploy
 ```

 ## MCP tool calls

 The lightweight endpoint accepts JSON-RPC-style calls:

 ```bash
 curl https://YOUR-WORKER.workers.dev/mcp \
   -H "Content-Type: application/json" \
   -d '{"method":"tools/list"}'
 ```

 Run the bundled synthetic dataset:

 ```bash
 curl https://YOUR-WORKER.workers.dev/mcp \
   -H "Content-Type: application/json" \
   -d '{
     "method": "tools/call",
     "params": {
       "name": "run_deseq",
       "arguments": {
         "dataset": "synthetic",
         "condition_column": "condition",
         "reference_level": "control",
         "treatment_level": "treated",
         "min_count": 10
       }
     }
   }'
 ```
