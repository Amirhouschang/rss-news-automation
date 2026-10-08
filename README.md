# RSS Daily News — Local AI and Automated Email Digests

[Deutsch](README.de.md)

A local news automation project that combines RSS collection, PostgreSQL storage, random sampling, local language-model summarization, and scheduled email delivery through n8n.

The purpose is to read beyond familiar interests and publisher perspectives without a social-media recommendation system choosing the topics. The project samples news **randomly**, rather than ranking it by engagement or personal preferences. Reading a source does not imply agreeing with it.

## Final workflow

Every day at **12:30 Europe/Berlin**, the published n8n workflow:

1. Fetches the active English-language feeds and checks publication dates against the current local calendar day.
2. Archives all available eligible unique RSS entries in PostgreSQL.
3. Draws a uniform random sample of **up to five items per source**, without replacement within each source's draw.
4. Prepares text for selected items and generates short English summaries using local Ollama and **`mistral-small3.1:latest`**. Existing successful summaries can be reused.
5. Retrieves the selected successful summaries and sends **one combined email**, with original titles and article links.

If a source provides fewer than five eligible items, all available candidates are selected. The five-source configuration gives a maximum of 25 selected items. Unselected entries remain archived without generated summaries.

| Publisher country | Final source | Input language |
|---|---|---|
| Germany | DW | English |
| Iran | IRNA | English |
| China | CGTN — World | English |
| Russia | TASS | English |
| Ukraine | Ukrinform | English |

Country describes the publisher, not necessarily the subject of the story. English titles are preserved unchanged; translation is disabled in the final workflow. ECNS was used in Stage 4 and replaced by CGTN for daily operation.

## Development and evidence

| Stage | Work | Documentation |
|---|---|---|
| 1 | Multilingual RSS collection, article extraction, access diagnostics | [Stage 1](stage1/README.md) |
| 2 | Text preparation and article/RSS fallback handling | [Stage 2](stage2/README.md) |
| 3 | Local model tests with English and German output | [Stage 3](stage3/README.md) |
| 4 | English feeds and local summarization comparison | [Stage 4](stage4/README.md) |
| 5 | Optional authenticated cloud comparison on frozen English input | [Stage 5](stage5/README.md) |
| 6 | PostgreSQL archival, random selection, and n8n email automation | [Stage 6](stage6/README.md) |

Each stage retains code and timestamped experimental results. Stage 1–3 also contain saved Ollama Modelfile exports with embedded dialogue messages. These document the saved local coding sessions, not necessarily every conversation held throughout the project. No model weights were trained or fine-tuned.

Stage 3's larger Qwen run accepted 50 outputs: 25 English and 25 German. The retained Stage 4 Mistral baseline accepted 25 English outputs. The final Stage 5 Sol and Astra runs each accepted 25 outputs. Accepted output means that the script accepted the response; it does **not** establish semantic accuracy.

Heuristic checks and source-comparison observations are retained separately. Automatic flags can be false positives, while genuine source-fidelity issues can remain unflagged. The stage READMEs link to the exact saved evidence and distinguish complete runs from interrupted ones.

## Human and AI contribution

Amirhoushang Rahmannejad defined the project goal, source requirements, selection strategy, evaluation questions, and final decisions; ran the experiments; and assessed the resulting workflow and digest. Prompts were developed through dialogue with ChatGPT. ChatGPT and local models assisted with code generation, debugging, review, and documentation. Local models also generated the experimental and final summaries.

The repository documents practical use and evaluation of existing models. It does not claim independent model development, training, a blind benchmark, or fully manual coding. The final summarizer follows the supplied source text rather than independently fact-checking the publisher.

## Running the project

The final pipeline is in [stage6/daily_news.py](stage6/daily_news.py). It imports helpers from Stage 4, so retain that directory alongside Stage 6.

Use Python **3.12 or newer** for the final script. Its principal Python dependencies are `requests`, `feedparser`, `trafilatura`, and `psycopg[binary]`:

```bash
python -m pip install requests feedparser trafilatura "psycopg[binary]"
```

PostgreSQL, local Ollama with the configured model, and the database tables/source configuration must already be set up. For a manual collection and summarization run, execute from the repository root:

```bash
python stage6/daily_news.py --sample-per-source 5
```

This Python command writes to PostgreSQL; **email delivery belongs to the n8n workflow**. Unattended execution uses `--non-interactive` and an external libpq password file, not a password committed to Git.

The configured host database is `rss_news`, with `sources`, `runs`, `news`, and a `news_overview` view. DBeaver is an inspection client, not a requirement for the pipeline. A sanitized n8n workflow template is included. The PostgreSQL schema, exported source configuration, and database diagram are included. Installation still requires local services, model weights, and each user’s own credentials. See [Stage 6](stage6/README.md).

## Validation and limits

The user reported successful scheduled execution and email delivery on **8 October 2026**, with the browser page closed. A preceding full manual run took approximately ten minutes according to the user's observation. Ten to fifteen minutes is a planning estimate, not a guaranteed upper bound.

- The host must be awake, powered on, online, and running the required services at the scheduled time. Closing the browser does not stop server-side n8n execution.
- RSS feeds are changing windows, not complete daily publisher archives. A 12:30 collection excludes later publications. Entries without usable publication dates are not silently classified as today's news.
- Extracted article text is not guaranteed to contain every paragraph. RSS-summary fallbacks have less context. Random selection does not remove publisher selection or guarantee topic diversity.
- New same-day runs can select previously selected stories again. The system has no exactly-once email-delivery guarantee.
- English editions can differ from original-language editions. Stage 3 and Stage 4 changed sources and content as well as language, so they do not isolate translation performance.
- Stage 5 records account-specific cloud access observed during the experiment, not a guarantee of general subscription API entitlement or future model availability. The daily pipeline remains local.
- Long-term Gmail authorization and service availability require operational attention; one successful scheduled test does not establish indefinite reliability.

## Repository hygiene

Credentials and private notes are not part of the public project. Review chat exports, screenshots, and workflow exports before publication. Stored news and generated outputs are experimental evidence, not independently verified factual reports. Archived results describe their original prompts and inputs; rerunning today's code may not reproduce an older prompt variant or a changing feed.
