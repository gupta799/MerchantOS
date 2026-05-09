import { expect, test } from "@playwright/test";

type TzafonTaskBody = {
  agent_type: "harness";
  instruction: string;
  stream_delta: true;
  mode: string;
};

type RecordedTzafonRequest = {
  method: "POST";
  path: string;
  authorization_scheme: "Bearer" | "missing";
  body: TzafonTaskBody;
};

type RecordedTzafonResponse = {
  requests: RecordedTzafonRequest[];
};

const tzafonMockBaseUrl = "http://127.0.0.1:9091";

test.beforeEach(async ({ request }) => {
  await request.post(`${tzafonMockBaseUrl}/reset`);
});

test("automated telemetry lab uses the Tzafon Northstar computer provider", async ({ page, request }) => {
  await page.goto("/");

  await expect(
    page.getByRole("heading", { name: "Automated computer-use telemetry for agent-ready commerce" })
  ).toBeVisible();
  await expect(page.getByText("Computer use: tzafon")).toBeVisible();
  await expect(page.getByText("Status: completed")).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText("succeeded").first()).toBeVisible();
  await expect(page.getByText("catalog.search")).toBeVisible();

  const response = await request.get(`${tzafonMockBaseUrl}/requests`);
  const recorded = (await response.json()) as RecordedTzafonResponse;
  expect(recorded.requests.length).toBeGreaterThanOrEqual(2);
  expect(recorded.requests[0].authorization_scheme).toBe("Bearer");
  expect(recorded.requests[0].path).toBe("/agent/tasks/stream");
  expect(recorded.requests[0].body.agent_type).toBe("harness");
  expect(recorded.requests[0].body.stream_delta).toBe(true);
  expect(recorded.requests[0].body.mode).toBe("tzafon.northstar-cua-fast-1.6");
  expect(recorded.requests[0].body.instruction).toContain("StormRunner GTX");
});
