# Swarm TinyFish Tools (`sidecar/tools`)

TinyFish integration package providing live web search, document fetching, and browser agent automation.

---

## Purpose
- Connect Swarm agents directly to the live web and a real browser to guarantee freshness and verification.
- **Research Bee:** Executes `search(query)` and `fetch(url)` before construction to extract modern documentation, patterns, and API signatures.
- **QA Bee:** Executes `run_browser_task(url, goal)` after construction to navigate, click, fill forms, and return pass/fail verdicts with attached screenshot evidence on the Honeycomb Whiteboard.

---

## Public Interface

### `TinyFishClient`
```python
from sidecar.tools import TinyFishClient

client = TinyFishClient(api_key=None)  # Reads TINYFISH_API_KEY from environment

# 1. Search the web
results = await client.search(query="modern react form validation")

# 2. Fetch page content
content = await client.fetch(url="https://docs.tinyfish.ai")

# 3. Automated browser workflow
task = await client.run_browser_task(
    url="http://localhost:5173",
    goal="Fill waitlist form with test data and verify confirmation toast",
)
```

### Agents
- `ResearchBee(bus)`: Gathers live web documentation and emits `card-research`.
- `QABee(bus)`: Runs automated browser sessions and emits `card-qa-verify` with evidence.

---

## Configuration & Feature Flags

| Variable | Description |
|---|---|
| `TINYFISH_API_KEY` | API key for TinyFish Search, Fetch, and Browser Agent. |
| `SWARM_TINYFISH_MODE` | Set to `"mock"` to force deterministic offline results even if key is present. |
| `ENABLE_TINYFISH_BEES` | Set to `"true"` to enable `ResearchBee` and `QABee` in the live multi-agent execution pipeline (off by default). |

---

## Endpoints & Implementation Notes

- **Search API:** `GET https://api.search.tinyfish.ai` (verified against official TinyFish documentation).
- **Fetch API:** `POST https://api.fetch.tinyfish.ai` (verified against official TinyFish documentation).
- **Browser Agent API:** `POST https://agent.tinyfish.ai/v1/run` (marked `TODO(verify-docs)` for exact JSON parameter schema on live endpoint).
- **Offline Mocking:** Fully supported without keys, returning realistic search snippets, page texts, and pass verdicts with screenshot evidence.
