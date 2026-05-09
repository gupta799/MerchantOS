#!/usr/bin/env bash
set -euo pipefail

model_repo="${AGENTREADY_HF_GGUF_REPO:-ggml-org/gemma-4-E4B-it-GGUF}"
model_quant="${AGENTREADY_HF_GGUF_QUANT:-Q4_K_M}"
model_alias="${AGENTREADY_HARNESS_MODEL:-gemma4-e4b-it}"
host="${AGENTREADY_LLAMACPP_HOST:-127.0.0.1}"
port="${AGENTREADY_LLAMACPP_PORT:-8080}"
ctx_size="${AGENTREADY_LLAMACPP_CTX_SIZE:-8192}"

if ! command -v llama-server >/dev/null 2>&1; then
  echo "llama-server was not found."
  echo "Install llama.cpp first:"
  echo "  brew install llama.cpp"
  exit 127
fi

echo "Starting llama.cpp OpenAI-compatible server"
echo "Model: ${model_repo}:${model_quant}"
echo "Alias: ${model_alias}"
echo "API: http://${host}:${port}/v1"
echo "UI: http://${host}:${port}"

exec llama-server \
  -hf "${model_repo}:${model_quant}" \
  --alias "${model_alias}" \
  --host "${host}" \
  --port "${port}" \
  --ctx-size "${ctx_size}"
