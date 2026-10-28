# GetRightCover Local Chatbot — V1

## What this version does

This is a local-first chatbot for GetRightCover using:

- Ollama
- Qwen3 4B Instruct
- FastAPI
- Local Markdown knowledge base
- Simple intent-based retrieval
- Browser chat UI

No Google scraping, social scraping, Gemini, MongoDB, or cloud LLM is used.

## Knowledge source

`knowledge/memberships.md` was prepared from the supplied `Company Overview GetRightCover.txt` document.

## Setup

```bash
cd getrightcover_local_chatbot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Make sure the model exists:

```bash
ollama pull qwen3:4b-instruct
```

Run:

```bash
python run.py
```

Open:

`http://127.0.0.1:8000`

## Test retrieval before running the UI

```bash
python -c "from app.knowledge_base import retrieve; c,s=retrieve('What membership plans are available?'); print(s); print(c)"
```

Expected source:

`['Membership Plans']`

## Test Ollama connectivity

```bash
python tests/test_ollama.py
```

## Example questions

- hello
- tell me something about grc
- What membership plans are available?
- 2 wheeler membership kitne ka hai?
- Tell me about membership benefits
- How does renewal work?
- How can I contact GetRightCover?

## Customer-facing output rules

The UI intentionally does not show model name, Ollama, retrieval sources, or internal reasoning.

Casual greetings are handled directly by the application.
Company questions are answered from the relevant section of the local knowledge base.

## Important source-status handling

The supplied company document contains some information marked as proposed, unverified,
or requiring confirmation. The chatbot must not convert those statements into confirmed facts.
For example, the renewal workflow is explicitly described as proposed and requiring validation.
