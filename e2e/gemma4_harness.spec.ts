import { expect, test } from "@playwright/test";

type ModelsResponse = {
  data: Array<{
    id: string;
    owned_by: string;
  }>;
};

type ChatCompletionResponse = {
  choices: Array<{
    message: {
      content: string;
    };
  }>;
};

const llamaApiBaseUrl = "http://127.0.0.1:8080/v1";

test.describe("Gemma 4 llama.cpp harness", () => {
  test("local Hugging Face GGUF model is available through the OpenAI-compatible API", async ({
    request
  }) => {
    const modelsResponse = await request.get(`${llamaApiBaseUrl}/models`);
    expect(modelsResponse.ok()).toBeTruthy();

    const models = (await modelsResponse.json()) as ModelsResponse;
    expect(models.data.map((model) => model.id)).toContain("gemma4-e4b-it");

    const completionResponse = await request.post(`${llamaApiBaseUrl}/chat/completions`, {
      data: {
        model: "gemma4-e4b-it",
        messages: [{ role: "user", content: "Reply with only: ready" }],
        max_tokens: 8,
        temperature: 0
      }
    });
    expect(completionResponse.ok()).toBeTruthy();

    const completion = (await completionResponse.json()) as ChatCompletionResponse;
    expect(completion.choices[0]?.message.content.trim().toLowerCase()).toBe("ready");
  });

  test("telemetry lab runs with DeepAgents backed by local Gemma 4 and scripted computer use", async ({
    page
  }) => {
    await page.goto("/");

    await expect(page.getByText("Harness: deepagents")).toBeVisible();
    await expect(page.getByText("Model: llamacpp/gemma4-e4b-it")).toBeVisible();
    await expect(page.getByText("Computer use: scripted")).toBeVisible();
    await expect(page.getByText("Status: completed")).toBeVisible({
      timeout: 120_000
    });
    await expect(page.getByText("succeeded").first()).toBeVisible();
    await expect(page.getByText("catalog.search")).toBeVisible();
  });
});
