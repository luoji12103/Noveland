# Provider Lab Worktree

## Purpose

The provider lab is the opt-in workflow for testing real LLM, image, TTS, ASR, and ComfyUI providers without spending quota in Noveland's default local gate.

Default tests use fake, dry-run, or mocked providers. Real provider tests run only when an operator explicitly opts in.

## Worktree Setup

Create a separate worktree from a clean local branch:

```sh
git worktree add ../Noveland-provider-lab main
cd ../Noveland-provider-lab
git checkout -b lab/provider-smoke
```

Use the lab worktree for provider configuration experiments and quota-consuming checks. Do not commit `.env` files, real API keys, provider output payloads, generated media bytes, or provider logs that may include raw prompts or credentials.

## Opt-in Gate

Real provider tests require:

```sh
export NOVELAND_RUN_REAL_PROVIDER_TESTS=1
```

Each provider family also requires its own lab configuration. Missing provider-specific variables must skip the related tests.

Suggested variables:

```sh
export NOVELAND_PROVIDER_LAB_OPENAI_BASE_URL="https://gateway.example/v1"
export NOVELAND_PROVIDER_LAB_OPENAI_AUTH_REF="env:OPENAI_API_KEY"
export NOVELAND_PROVIDER_LAB_OPENAI_MODEL="text-model"

export NOVELAND_PROVIDER_LAB_ANTHROPIC_BASE_URL="https://gateway.example"
export NOVELAND_PROVIDER_LAB_ANTHROPIC_AUTH_REF="env:ANTHROPIC_API_KEY"
export NOVELAND_PROVIDER_LAB_ANTHROPIC_MODEL="text-model"

export NOVELAND_PROVIDER_LAB_MIMO_BASE_URL="https://gateway.example"
export NOVELAND_PROVIDER_LAB_MIMO_TTS_MODEL="mimo-tts-model"
export NOVELAND_PROVIDER_LAB_MIMO_ASR_AUTH_REF="env:MIMO_API_KEY"
export NOVELAND_PROVIDER_LAB_MIMO_ASR_MODEL="mimo-asr-model"
export NOVELAND_PROVIDER_LAB_MIMO_ASR_ENDPOINT="/v1/chat/completions"
export NOVELAND_PROVIDER_LAB_MIMO_ASR_REQUEST_FORMAT="chat_completions"
export NOVELAND_PROVIDER_LAB_MIMO_ASR_LANGUAGE="auto"
export NOVELAND_PROVIDER_LAB_MIMO_ASR_AUDIO_PATH="/path/to/sample.wav"

export NOVELAND_PROVIDER_LAB_IMAGE_BASE_URL="https://gateway.example/v1"
export NOVELAND_PROVIDER_LAB_IMAGE_AUTH_REF="env:IMAGE_API_KEY"
export NOVELAND_PROVIDER_LAB_IMAGE_MODEL="image-model"

export NOVELAND_PROVIDER_LAB_COMFYUI_BASE_URL="http://127.0.0.1:8188"
```

The values above are examples. Presets must allow custom `base_url`, `auth_ref`, and `model_name`; do not force official vendor endpoints.

## Commands

Default gate, no real calls:

```sh
cd backend
uv run pytest tests/test_provider_lab_harness.py
uv run pytest
```

Opt-in provider lab examples:

```sh
cd backend
NOVELAND_RUN_REAL_PROVIDER_TESTS=1 uv run pytest -m real_provider tests/test_provider_lab_harness.py
```

Run a single provider family by adding a keyword:

```sh
NOVELAND_RUN_REAL_PROVIDER_TESTS=1 uv run pytest -m real_provider -k openai tests/test_provider_lab_harness.py
```

## Evidence Rules

Provider lab output may record:

- provider family;
- provider kind;
- adapter kind;
- capability key;
- model name;
- safe status;
- safe error class.

Provider lab output must not record:

- resolved secrets or Authorization headers;
- API keys, bearer tokens, passwords, or private keys;
- raw prompts or raw outputs;
- storage URIs, filesystem paths, object storage paths, bytes, or base64;
- prompt snapshot internals;
- local ComfyUI model paths or custom node paths.

## Boundaries

- Real provider tests are never part of the default gate.
- Real provider tests must use `ProviderExecutionService`, model discovery contracts, and visual generation dry-run/mapping boundaries where applicable.
- ComfyUI tests must use registered workflow/template-slot assumptions. Runtime agents must never submit arbitrary workflow JSON.
- Provider failures must be reported as safe metadata, not stack traces with request bodies.
- The provider lab is not a deployment profile, public readiness gate, or source of committed fixture media.
