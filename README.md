# Transcript Studio — European Robotic Surgery Interviews

A local **Streamlit** app for analyzing three expert interview transcripts (France, Germany, UK). It answers a fixed **interview guide**, compares experts, and supports **free-form chat** — with answers grounded in the source text and **timestamped quotes** you can trust.

**LLM:** [OpenRouter](https://openrouter.ai/) (any compatible model slug).  
**Search:** Runs on your machine (embeddings + vector DB). No API key needed to browse the UI or build the index.

---

## What you can do

| Tab | Name | What it does |
|-----|------|----------------|
| **1 — Per expert** | Interview guide | Pick one of 6 guide questions → get **three answers** (one per market/expert) with quotes. |
| **2 — Synthesis** | Themes & disagreements | Pick the **same style** of question → see **agreements and disagreements** across the three experts. |
| **3 — Chat** | Ask across transcripts | Type any question → one answer drawn from the **best-matching excerpts** across all experts. |

Nothing calls the LLM until you click **Generate answers** (Tab 1) or **Run synthesis** (Tab 2), or send a chat message (Tab 3). That keeps usage predictable and fast.

---

## Quick start

### 1. Prerequisites

- **Python 3.11+** (3.12 / 3.13 / 3.14 work in practice)
- An [OpenRouter API key](https://openrouter.ai/keys) for generation (optional for loading the app and index)

### 2. Install

```bash
cd hasamex-case
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

On first run, the app downloads the embedding model `sentence-transformers/all-MiniLM-L6-v2` (~90 MB). Tests do the same.

### 3. Configure the API key

Create a file named `.env` in the project root (never commit this file):

```bash
OPENROUTER_API_KEY=your_key_here

# Optional — pick any model from https://openrouter.ai/models
# LLM_MODEL=openrouter/free

# Optional tuning (see Configuration below)
# LLM_MAX_TOKENS=8192
# LLM_REASONING_EFFORT=low
# LLM_STRICT_JSON=true
```

The app loads `.env` automatically when Streamlit starts.

### 4. Run

```bash
streamlit run app.py
```

Open the URL shown in the terminal (usually `http://localhost:8501`).

### 5. Tests (optional)

```bash
PYTHONPATH=. pytest tests/ -q
```

---

## How the app is built (simple picture)

Think of two layers: **local search** (always) and **cloud LLM** (when you generate).

```text
  Files/  (transcripts + interview guide)
      │
      ▼
  parser.py          →  turns each speaker turn into a Segment (text + timestamp + expert/market)
      │
      ▼
  retrieval.py       →  embeds segments with MiniLM, stores in Chroma (.cache/chroma)
      │
      ├──────────────────────────────────────┐
      ▼                                      ▼
  qa_per_expert.py                    chat.py
  (Tab 1 & input to Tab 2)            (Tab 3)
      │                                      │
      │  retrieve top-k excerpts             │  retrieve top-k (all experts)
      │  per expert + market filter          │
      ▼                                      ▼
  llm.py  ────────── OpenRouter (JSON answers) ──────────
      │
      ▼
  verify.py          →  quotes must appear verbatim in segment text
      │
      ▼
  synthesis.py       →  Tab 2 only: compare the three grounded answers
      │
      ▼
  app.py + ui.py     →  Streamlit tabs and layout
```

**Important idea:** The model never sees full transcripts. It only sees **small retrieved excerpts**. Synthesis (Tab 2) does **not** re-read raw transcripts; it only compares the **already grounded** per-expert answers from Tab 1’s pipeline.

---

## End-to-end flows

### Tab 1 — Per expert

1. You choose a **guide question** from the dropdown.
2. You click **Generate answers**.
3. For **each of the three experts**, the app:
   - Searches that expert’s segments for the question (top **6** chunks by default).
   - Sends those excerpts to OpenRouter with strict JSON instructions.
   - **Verifies** each quote against the original segment text.
   - Retries **once** if quotes fail verification.
4. Results are **cached** per question and model. Changing the dropdown does not re-run until you click generate again for that selection.

**Typical cost:** **3 LLM calls** per guide question (one per expert).

### Tab 2 — Synthesis

1. You choose a **guide question** (same dropdown pattern as Tab 1).
2. You click **Run synthesis**.
3. The app loads **per-expert answers** for that question (from cache if you already ran Tab 1; otherwise it runs those 3 calls first).
4. One more LLM call produces **agreements** and **disagreements** with expert names and timestamps tied to the grounded quotes.

**Typical cost:** **1** synthesis call if Tab 1 already ran for that question; **4** calls total if not (3 + 1).

### Tab 3 — Chat

1. You type a question in the chat box.
2. The app retrieves the **top 8** segments across **all** transcripts.
3. If nothing is relevant enough, it answers that the topic is **not covered** — without calling the LLM.
4. Otherwise: **1 LLM call**, verified quotes, shown in the thread.

Tab 1 and 2 use a cache. Tab 3 Chat is not cached; each message is a new request. 

---

## Project layout

```text
hasamex-case/
├── app.py                 # Streamlit entrypoint, caching, tabs
├── requirements.txt
├── .streamlit/config.toml # Theme; fileWatcherType=none (avoids transformers scan noise)
├── Files/
│   ├── Interview_Guide.txt    # 6 guide questions
│   └── Transcript_*.txt       # France, Germany, UK expert calls
├── src/
│   ├── parser.py          # Parse transcripts and guide
│   ├── retrieval.py       # MiniLM + Chroma
│   ├── qa_per_expert.py   # Tab 1 (+ feeds Tab 2)
│   ├── synthesis.py       # Tab 2 cross-expert themes
│   ├── chat.py            # Tab 3
│   ├── verify.py          # Quote verification
│   ├── llm.py             # OpenRouter via LangChain ChatOpenAI
│   ├── step_log.py        # Pipeline timing logs (terminal)
│   └── ui.py              # CSS and HTML components
└── tests/                 # Parser, retrieval, verify, LLM config, integration
```

---

## Logging and performance

- **Terminal:** Steps log as `hasamex.pipeline` (`START` / `DONE` with duration). Useful when a run feels slow.
- **Embeddings:** Persisted under `.cache/chroma` so restarts skip re-encoding when data unchanged.
- **Streamlit cache:** `@st.cache_resource` for the retriever; `@st.cache_data` for per-question QA and synthesis.

