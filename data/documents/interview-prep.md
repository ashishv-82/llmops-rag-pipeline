# Interview Prep - oOh!media Investor Chat

25 Q&A pairs for an Engineering Manager (AI) interview.

---

## Section 1: AI Fundamentals (grounded to this project)

### Q1. What is RAG and why did you use it here instead of fine-tuning?

- RAG = Retrieval-Augmented Generation. The LLM gets relevant document chunks at query time rather than baking knowledge into model weights.
- Fine-tuning would be wrong here because:
  - Investor data changes every reporting period - you'd need to retrain
  - You lose traceability - can't point to page numbers and source documents
  - The brief explicitly requires citations traceable to source (PRD NFR: Grounding)

### Q2. What are embeddings and how do they work in your pipeline?

- Embeddings are dense vector representations of text that capture semantic meaning.
- In this project: PDF text chunks are embedded using OpenAI `text-embedding-3-small`, stored in ChromaDB as vectors.
- At query time, the user's question is embedded with the same model, and cosine similarity finds the most relevant chunks.

### Q3. Why use a separate embedding model (OpenAI) from your reasoning model (Claude)?

- Anthropic doesn't offer an embedding API, so OpenAI `text-embedding-3-small` is the pragmatic choice.
- Embedding and reasoning are independent tasks - the embedding model just maps text to vectors, the reasoning model interprets the retrieved text.
- This is a standard pattern in production RAG systems.

### Q4. What is the tool-use (function calling) pattern and why did you choose it over a classify-then-route approach?

- Tool-use: the LLM receives tool definitions, decides which tools to call based on the question, gets results back, and synthesises an answer.
- Benefits over manual routing:
  - The model handles ambiguous queries naturally (e.g. "revenue AND share price" triggers both tools)
  - No hand-rolled classifier to maintain
  - The loop handles multi-step reasoning (call search, refine, search again)

### Q5. What is a vector database and why ChromaDB specifically?

- A vector database stores embeddings and supports similarity search (nearest-neighbour lookup).
- ChromaDB was chosen because:
  - Local/embedded - zero ops, no cloud dependency (PRD non-goal: cloud deployment)
  - Persistent client - survives restarts
  - Single-directory store - simple for a small corpus
  - Idempotent upsert - re-running ingest doesn't duplicate data

### Q6. How do you prevent the LLM from hallucinating?

Multiple layers:
- **System prompt**: explicit refusal rules - never fabricate, never invent citations
- **Empty results as refusal triggers**: if `search_documents` returns nothing, the prompt tells the model to say so, not guess
- **Citation extraction**: post-processing strips any citation markers the model invented that don't map to real tool results
- **No direct corpus access**: the model only sees chunks returned by tools, not the raw documents

### Q7. What is the difference between a chunk, a citation, and an embedding in your system?

- **Chunk**: a slice of PDF text (800 chars, 100 overlap) with metadata (source, page, period). Created at ingest time.
- **Embedding**: the vector representation of a chunk's text. Stored in ChromaDB alongside the chunk.
- **Citation**: a chunk that was selected by retrieval AND used by the LLM in its answer. Has the same metadata fields but lives in the `AnswerWithCitations` response.

---

## Section 2: Architecture & Design Decisions

### Q8. Walk me through what happens when a user asks "What was oOh!media's revenue in FY24?"

1. Streamlit captures the question, passes it with session history to `core.assistant.answer()`
2. `answer()` sends the question + system prompt + tool definitions to Claude Sonnet
3. Claude returns a `tool_use` block requesting `search_documents` with query "oOh!media revenue FY24"
4. `answer()` runs the tool: embeds the query, does cosine search in ChromaDB, gets top-k chunks
5. Chunks are formatted as numbered evidence blocks `[1]`, `[2]`, etc. and sent back as `tool_result`
6. Claude reads the evidence, writes an answer with inline citations like `[1]`, `[2]`
7. `answer()` extracts and renumbers citations, returns `AnswerWithCitations`
8. Streamlit renders the answer text + expandable sources panel

### Q9. Why is `core.assistant.answer()` the single entry point? Why not let each surface talk to the LLM directly?

- **Shared, not rebuilt** (US-07 AC3) - both Streamlit and MCP use the exact same reasoning logic
- All refusal rules, tool dispatch, citation extraction live in one place - change once, applies everywhere
- Surfaces are thin adapters: Streamlit handles UI state, MCP handles stdio protocol. Neither contains reasoning.

### Q10. Why did you separate `llm.py`, `retrieval.py`, `embeddings.py`, and `prices.py` into individual modules?

- **Import isolation**: `openai` only in `embeddings.py`, `anthropic` only in `llm.py`, `chromadb` only in `retrieval.py` and `ingest.py`
- Makes testing easier - mock one boundary without touching others
- Makes swapping providers straightforward - replace `embeddings.py` to change embedding model, replace `prices.py` to change market data source

### Q11. Explain the `PriceProvider` interface. Why not just call Marketstack directly?

- `PriceProvider` is an abstract base class with one method: `get_price_history(start, end)`
- Two implementations exist: `MarketstackProvider` (primary) and `AlphaVantageProvider` (scaffold)
- Benefits:
  - Swap providers without touching `assistant.py`
  - Factory function `get_provider()` picks based on which API key is set
  - Easy to add a third provider (e.g. Yahoo Finance) - just implement the interface

### Q12. Why Marketstack v2 and not the v1 endpoint from the Solution Design?

- The Solution Design's guidance was stale. Empirical testing during preflight:
  - v1/HTTP with `OML.AX` or `OML.XASX` returned `406 Not Acceptable`
  - Alpha Vantage returned empty `{}` for ASX symbols
  - **v2/HTTPS with `OML.AX`** returned 200 OK with real EOD data
- Documented in DECISIONS.md with the exact test results

### Q13. How does your chunking strategy work and why those parameters?

- **Sliding window**: 800 characters per chunk, 100 character overlap
- Page-aware: chunks never cross page boundaries (each page is chunked independently)
- 800 chars balances enough context for meaningful retrieval vs. not flooding the LLM context
- 100 char overlap prevents losing information at chunk boundaries
- Page number is preserved on every chunk for citation accuracy

### Q14. What makes your ingest pipeline idempotent?

- Each chunk gets a deterministic ID: `{source_id}:p{page}:c{idx}`
- ChromaDB `upsert` replaces existing chunks with the same ID
- Re-running ingest on the same corpus produces the same IDs, so it's a no-op update
- Adding a new PDF just adds new IDs without touching existing data

---

## Section 3: Implementation Details

### Q15. How do you handle the Anthropic tool-use loop? What's the stop condition?

```
while iterations < MAX_ITERATIONS (6):
    call Claude with messages
    if stop_reason == "tool_use":
        execute requested tools
        append tool_results to messages
        continue loop
    else (end_turn / max_tokens):
        extract text and citations
        return AnswerWithCitations
```
- Loop continues until Claude says `end_turn` or hits the iteration cap
- The cap (6) is defensive - normal questions resolve in 1-2 iterations

### Q16. What happens when the model cites a source that doesn't exist in your tool results?

- `_extract_and_renumber()` in `assistant.py` handles this:
  - Scans the answer for `[N]` markers
  - Only keeps markers that map to real chunks from tool results
  - Strips any markers the model invented
  - Renumbers remaining citations to a contiguous `[1], [2], [3]` sequence
- This is a safety net against hallucinated citations

### Q17. How does the Streamlit app handle errors without showing blank screens?

- `answer()` is called inside a `try/except` block
- Exceptions are caught and rendered with `st.error(f"Something went wrong: {exc}")`
- This satisfies US-01 AC4: "visible errors, not blank screens or hangs"
- The spinner (`st.spinner("Thinking...")`) gives feedback during the LLM call

### Q18. Why do you cache market data to disk?

- Marketstack free tier has a 10,000 request quota
- Same date range query returns the same data - no reason to hit the API twice
- Cache key: `{provider}_{symbol}_{function}_{start}_{end}.json`
- Read from cache first, always. Only call API on cache miss.
- Also makes the app work offline for previously fetched ranges

### Q19. How does the `$` escaping work in Streamlit and why is it needed?

- Streamlit's markdown renderer interprets `$...$` as LaTeX math
- Financial text like "$635.6m" gets parsed as inline math and renders as garbled KaTeX
- Fix: `text.replace("$", "\\$")` escapes every dollar sign before rendering
- Simple, targeted fix for a domain-specific problem

---

## Section 4: What-If Scenarios

### Q20. What if you needed to support 10,000 PDFs instead of 5?

Changes needed:
- **Chunking**: batch embedding calls (currently sends all at once) - add batching in `embed_texts()`
- **ChromaDB**: would likely hit performance limits. Migrate to a managed vector DB (Pinecone, Weaviate, pgvector)
- **Ingest**: the hard-coded `DOCS` dict doesn't scale. Replace with a metadata file or database scan
- **Retrieval**: may need hybrid search (vector + keyword) or re-ranking to maintain quality at scale
- Core architecture (single entry point, tool-use loop, citation schema) stays the same

### Q21. What if the LLM needed to answer questions across 50 different companies, not just oOh!media?

- **Retrieval**: add company metadata to chunks, filter by company at query time
- **System prompt**: generalise from "oOh!media investor assistant" to a multi-company role
- **Tools**: `search_documents` would need a `company` parameter
- **Market data**: `PriceProvider` already takes a symbol - extend to accept dynamic symbols
- **Ingest**: the corpus mapping becomes a database, not a dict

### Q22. What if the Anthropic API goes down mid-conversation?

- Currently: the `try/except` in `app.py` catches the exception and shows `st.error()`
- The conversation history in `st.session_state` is preserved - user can retry
- For production: add retry with exponential backoff in `llm.py`, circuit breaker pattern, and possibly a fallback model

### Q23. What if you had to add a "compare FY24 vs FY25" feature?

- Already partially supported: the system prompt allows up to 4 `search_documents` calls per turn
- Claude can call search twice with different period-specific queries and synthesise
- If retrieval quality is poor for comparisons: add period filtering to ChromaDB metadata queries
- The citation schema already tracks `period` per source, so the answer naturally attributes claims to the right year

### Q24. What if a competitor built this with LangChain? What's your argument for going framework-free?

- **Transparency**: every line of the tool-use loop is visible in `assistant.py` - no magic, easy to debug
- **Control**: refusal rules, citation extraction, and renumbering are custom logic that would fight a framework's abstractions
- **Fewer dependencies**: LangChain pulls in 50+ transitive deps. This project has ~10 direct deps.
- **Anthropic's own recommendation**: their docs show the raw tool-use loop, not a framework wrapper
- Trade-off acknowledged: a framework would give you chains, memory, and agents for free. But this project doesn't need them.

### Q25. You skipped US-07 (MCP server). If you had one more hour, how would you implement it?

- Create `mcp_server.py` (~30-40 lines):
  - Import `mcp` SDK and `core.assistant.answer`
  - Register one tool: `ask_oohmedia_investor_chat(question: str)`
  - The tool calls `answer(question)` and formats `AnswerWithCitations` as text
  - Stdio transport, all logging to stderr
- Add Claude Desktop config snippet to README:
  ```json
  {
    "mcpServers": {
      "oohmedia-investor": {
        "command": "uv",
        "args": ["run", "--directory", "/path/to/repo", "python", "mcp_server.py"]
      }
    }
  }
  ```
- The entire point: `core/` is already the reusable capability. The MCP server is just a transport adapter. This is why the architecture separates surfaces from reasoning.
