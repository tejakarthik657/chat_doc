# 13. Executive Prompt Engineering & Token Budget Expansion

> *"Prompt engineering is not about typing polite words to a chatbot. In enterprise AI, prompt engineering is systems programming: managing token budgets, constraining output entropy, enforcing structured schemas, and eliminating mid-sentence truncation bugs."*

---

## 1. The Production War Story: The Mid-Sentence Truncation Bug

During early integration testing with clinical researchers, we encountered a frustrating bug:
> *"The chatbot starts providing an amazing regulatory analysis, begins drawing a beautiful table of patient exclusion criteria, and then freezes mid-sentence right at row 4."*

When developers face this issue, they often assume the network blipped or the frontend crashed. 

### The Root Cause Analysis:
1. **The 800-Token Default Limit**: Many boilerplate API clients initialize LLM calls with `max_tokens = 800` to conserve costs.
2. **The Markdown Table Expansion Factor**: A structured Markdown table with 5 columns and 8 rows (comparing patient IDs, biomarker cutoffs, baseline values, protocol thresholds, and regulatory compliance flags) consumes approximately **450 tokens** on its own.
3. **The `finish_reason: "length"` Cutoff**: Combined with introductory clinical reasoning and remediation advice, the total token count easily hit 801 tokens. Groq's LPU halted generation mid-word because the token budget was exhausted.

---

## 2. The Architectural Fix: Expanding to 3,500 Tokens

We addressed this across the codebase in [`rag-backend/app/core/llm_groq.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/core/llm_groq.py):

```python
# rag-backend/app/core/llm_groq.py (Production Token Budget Expansion)

async def stream_groq_completion(messages: list, ...):
    response = await client.chat.completions.create(
        model=active_model,
        messages=messages,
        temperature=0.1,         # Low entropy for deterministic clinical auditing
        max_tokens=3500,         # Expanded from 800 to 3500 for exhaustive answers
        top_p=0.9,               # Nucleus sampling bound
        stream=True
    )
```

By expanding the output budget to **3,500 tokens**:
- The model has room to generate multi-page regulatory comparison matrices without artificial truncation.
- Markdown tables close their syntax cleanly (`|---|---|`), preventing UI rendering breaks in the frontend markdown parser.
- Comprehensive remediation steps under FDA 21 CFR and ICH GCP guidelines can be articulated in full.

---

## 3. The Clinical Auditor System Prompt Specification

An ordinary AI prompt produces wordy, apologetic, and robotic answers (*"Sure, I would be happy to help you with that! Based on the provided context..."*). 

In high-stakes enterprise compliance, clinicians and executives need direct, authoritative, and data-dense answers.

Here is the exact System Prompt engineered in [`rag-backend/app/core/llm_groq.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/core/llm_groq.py):

```python
SYSTEM_PROMPT = """You are an elite, executive-grade AI research assistant and clinical/regulatory document intelligence specialist.

Your objective is to provide exhaustive, precise, beautifully articulated, and authoritative answers based strictly on the Document Context and Live Database records provided below.

### Presentation & Style Guidelines:
1. **Executive Tone & Clinical Rigor**:
   - Deliver clear, direct, and authoritative insights.
   - Never start with conversational filler or robotic boilerplate like "Based on the provided documents...". Dive straight into the core clinical or regulatory finding.
2. **Visual Hierarchy & Formatting**:
   - Use clean Markdown headers (##, ###) to structure multi-part answers.
   - Use bold highlights (**concept**) to emphasize key biomedical entities, dosages, lab thresholds, and patient IDs.
   - Use bullet points (- ) or numbered lists for sequential protocol steps.
3. **Structured Markdown Tables**:
   - Whenever presenting patient cohort comparisons, biomarker lab values, inclusion/exclusion criteria, or dosage schedules, ALWAYS format them in clean, responsive Markdown tables with column headers.
4. **Source & Regulatory Citations**:
   - Integrate elegant, precise citations at the end of relevant points: [Source: filename, Page X] or [Live Database: Patient #ID].
5. **Completeness & Depth (3,500 Token Budget)**:
   - Provide exhaustive answers without cutting off mid-sentence.
6. **Constructive Compliance Guidance**:
   - If a protocol contradiction is detected, explicitly highlight the regulatory risk (e.g. FDA 21 CFR 312, ICH GCP E6) and recommend harmonized corrective actions."""
```

---

## 4. Temperature & Sampling Parameter Calibration

In clinical regulatory auditing, creativity is a liability. You want deterministic factual retrieval, not creative storytelling.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      HYPERPARAMETER TUNING SPECS                            │
├─────────────────┬───────────┬───────────────────────────────────────────────┤
│ Hyperparameter  │ Value     │ Technical Rationale                           │
├─────────────────┼───────────┼───────────────────────────────────────────────┤
│ **Temperature** │ **0.1**   │ Sharpens the probability distribution over     │
│                 │           │ vocabulary tokens. Enforces factual citations │
│                 │           │ and prevents creative hallucination of numbers│
├─────────────────┼───────────┼───────────────────────────────────────────────┤
│ **Top-P**       │ **0.90**  │ Limits cumulative probability nucleus to top  │
│                 │           │ 90% of candidates, eliminating low-probability│
│                 │           │ vocabulary noise while preserving fluid prose. │
├─────────────────┼───────────┼───────────────────────────────────────────────┤
│ **Max Tokens**  │ **3,500** │ Allocates sufficient token budget for large   │
│                 │           │ tabular Markdown matrices and multi-page audits│
└─────────────────┴───────────┴───────────────────────────────────────────────┘
```

---

## 5. CTO Interview Defense: Prompt Engineering

When an interviewer asks: *"How do you prevent your LLM from hallucinating dosages or generating vague corporate speak?"*, explain your methodology:

> *"We treat prompt engineering as a strict systems constraint problem rather than creative writing:
> 
> 1. **Zero-Boilerplate Executive Framing**: We forbid conversational preamble ('As an AI, I found...'). The system prompt commands the model to lead with the core regulatory finding and format all cohort comparisons, biomarker cutoffs, and dosing rules into structured Markdown tables.
> 
> 2. **Token Budget Optimization**: Early RAG systems frequently suffer from mid-sentence cutoffs because default client SDKs cap responses at 800 tokens. We expanded our budget to 3,500 tokens and tuned our low-entropy sampling (`temperature=0.1`) to ensure exhaustive, deterministic output.
> 
> 3. **Dual Grounding Anchors**: Every factual assertion must be anchored to either an extracted document chunk with page citations (`[Source: Protocol.pdf, Page 14]`) or a live Inbound EHR record (`[Live Database: Patient #104]`). If evidence is missing, our system prompt and CRAG layer mandate explicit regulatory abstention rather than speculation."*
