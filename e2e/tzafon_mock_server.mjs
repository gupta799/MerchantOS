import http from "node:http";

const port = Number.parseInt(process.env.TZAFON_MOCK_PORT ?? "9091", 10);
const requests = [];

function readBody(request) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    request.on("data", (chunk) => chunks.push(chunk));
    request.on("end", () => resolve(Buffer.concat(chunks).toString("utf8")));
    request.on("error", reject);
  });
}

function writeJson(response, statusCode, body) {
  response.writeHead(statusCode, {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS"
  });
  response.end(JSON.stringify(body));
}

const server = http.createServer(async (request, response) => {
  if (request.method === "OPTIONS") {
    writeJson(response, 200, { ok: true });
    return;
  }

  if (request.method === "GET" && request.url === "/health") {
    writeJson(response, 200, { ok: true });
    return;
  }

  if (request.method === "POST" && request.url === "/reset") {
    requests.length = 0;
    writeJson(response, 200, { ok: true });
    return;
  }

  if (request.method === "GET" && request.url === "/requests") {
    writeJson(response, 200, { requests });
    return;
  }

  if (request.method === "POST" && request.url === "/agent/tasks/stream") {
    const rawBody = await readBody(request);
    const body = JSON.parse(rawBody);
    const authorization = request.headers.authorization ?? "";
    requests.push({
      method: request.method,
      path: request.url,
      authorization_scheme: authorization.startsWith("Bearer ") ? "Bearer" : "missing",
      body
    });
    response.writeHead(200, {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive"
    });
    response.write(`data: ${JSON.stringify({ event: "accepted", mode: body.mode })}\n\n`);
    response.end();
    return;
  }

  writeJson(response, 404, { ok: false });
});

server.listen(port, "127.0.0.1", () => {
  process.stdout.write(`Tzafon mock server listening on http://127.0.0.1:${port}\n`);
});
