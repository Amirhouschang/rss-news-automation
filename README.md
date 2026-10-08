# RSS Daily News — Local AI and Automated Email Digests

[Deutsch](README.de.md)

A local news automation project that combines RSS collection, PostgreSQL storage, random sampling, local language-model summarization, and scheduled email delivery through n8n.

I built it to read beyond my usual interests and beyond a single publisher's perspective, without a social-media recommendation system choosing the topics for me. The project samples news **randomly** instead of ranking it by engagement or personal preferences. Reading a source does not mean agreeing with it.

## Final workflow

Every day at **12:30 Europe/Berlin**, the published n8n workflow:

1. Fetches the active English-language feeds and checks publication dates against the current local calendar day.
2. Archives all available eligible unique RSS entries in PostgreSQL.
3. Draws a uniform random sample of **up to five items per source**, without replacement within each source's draw.
4. Prepares text for selected items and generates short English summaries using local Ollama and **`mistral-small3.1:latest`**. Existing successful summaries can be reused.
5. Retrieves the selected successful summaries and sends **one combined email**, with original titles and article links.

If a source provides fewer than five eligible items, all available candidates are selected. With five sources, a digest contains at most 25 items. Newly archived entries that are not selected receive no summary during that run. Summaries saved in earlier runs remain available.

| Publisher country | Final source | Input language |
|---|---|---|
| Germany | DW | English |
| Iran | IRNA | English |
| China | CGTN — World | English |
| Russia | TASS | English |
| Ukraine | Ukrinform | English |

The country is the publisher's country, which is often different from the subject of the story. English titles are kept unchanged, and the final workflow does not translate. ECNS was used in Stage 4 and replaced by CGTN for daily operation.

## Development and evidence

| Stage | Work | Documentation |
|---|---|---|
| 1 | Multilingual RSS collection, article extraction, access diagnostics | [Stage 1](stage1/README.md) |
| 2 | Text preparation and article/RSS fallback handling | [Stage 2](stage2/README.md) |
| 3 | Local model tests with English and German output | [Stage 3](stage3/README.md) |
| 4 | English feeds and local summarization comparison | [Stage 4](stage4/README.md) |
| 5 | Optional authenticated cloud comparison on frozen English input | [Stage 5](stage5/README.md) |
| 6 | PostgreSQL archival, random selection, and n8n email automation | [Stage 6](stage6/README.md) |

The [development report for Stages 1–5](RSS_Project_Stages_1_to_5.md) records the experiments and manual source-comparison observations from **7 October 2026**, including the choice of the original Mistral prompt. Its final section describes the next step planned at that time; the resulting automation is documented in [Stage 6](stage6/README.md).

Each stage keeps its code and timestamped results. Stages 1–3 also contain saved Ollama Modelfile exports with the coding dialogue from the local sessions. I used existing models throughout; no model weights were trained or fine-tuned.

The main runs in numbers:

- Stage 3: the larger Qwen run accepted 50 outputs, 25 English and 25 German.
- Stage 4: the retained Mistral baseline accepted 25 English outputs.
- Stage 5: the final Sol and Astra runs each accepted 25 outputs.

"Accepted" means the script received a valid response. Whether a summary is faithful to its source is a separate question, which I checked in two ways: an automatic heuristic check and a manual comparison with the source text. The automatic check produced false positives and also missed real deviations, so the two are reported separately. The stage READMEs link to the saved evidence and mark which runs were complete and which were interrupted.

## Human and AI contribution

I defined the project goal, source requirements, selection strategy, evaluation questions, and final decisions; ran the experiments; and assessed the resulting workflow and digest. Prompts were developed through dialogue with ChatGPT. ChatGPT and local models assisted with code generation, debugging, review, and documentation. Local models also generated the experimental and final summaries.

This is a project about using and evaluating existing models in practice. The code was written with AI assistance, and the comparison is a practical one, not a blind benchmark. The summarizer follows the supplied source text; it does not fact-check the publisher.

## Running the project

The final pipeline is in [stage6/daily_news.py](stage6/daily_news.py). It imports helpers from Stage 4, so keep that directory alongside Stage 6.

Use Python **3.12 or newer** for the final script. Its principal Python dependencies are `requests`, `feedparser`, `trafilatura`, and `psycopg[binary]`:

```bash
python -m pip install requests feedparser trafilatura "psycopg[binary]"
```

PostgreSQL, local Ollama with the configured model, and the database tables/source configuration must already be set up. For a manual collection and summarization run, execute from the repository root:

```bash
python stage6/daily_news.py --sample-per-source 5
```

This Python command writes to PostgreSQL; **email delivery belongs to the n8n workflow**. Unattended execution uses `--non-interactive` and an external libpq password file, so no password is stored in Git.

The database is called `rss_news` and contains `sources`, `runs`, `news`, and a `news_overview` view. I use DBeaver to inspect it; the pipeline does not need it. The repository includes a sanitized n8n workflow template, the PostgreSQL schema, the exported source configuration, and a database diagram. To install it, you need your own local services, model weights, and credentials. See [Stage 6](stage6/README.md).

## Validation and limits

I confirmed successful scheduled execution and email delivery on **8 October 2026**, with the browser page closed. A preceding full manual run took approximately ten minutes. Based on this test, I estimate ten to fifteen minutes for a run; this range is not a guaranteed upper bound.

- The host must be awake, powered on, online, and running the required services at the scheduled time. Closing the browser does not stop server-side n8n execution.
- An RSS feed shows a changing window of entries, not a publisher's full daily archive. A 12:30 collection misses later publications. Entries without a usable publication date are left out instead of being counted as today's news.
- Extracted article text can be incomplete, and RSS-summary fallbacks have less context. Random selection still depends on what each publisher puts in its feed, and it does not guarantee topic diversity.
- A second run on the same day can select stories that were already selected. The system does not guarantee that each story is emailed only once.
- English editions can differ from original-language editions. Between Stage 3 and Stage 4, the sources and content changed along with the language, so the two stages cannot be compared as a pure translation test.
- Stage 5 records the cloud access that worked for my account during the experiment. Other subscriptions and future model availability may differ. The daily pipeline remains local.
- Gmail authorization and service availability need attention for long-term operation. One successful scheduled test does not show how reliable the system is over months.

## Repository hygiene

Credentials and private notes are not part of the public project. The published files were reviewed before publication, and personal credential references were removed from the workflow export. Stored news and generated outputs are experimental evidence, not independently verified factual reports. Archived results belong to their original prompts and inputs; rerunning today's code may not reproduce an older prompt variant or a changing feed.

## Copyright

© 2026 Amirhoushang Rahmannejad. All rights reserved.

Unless otherwise stated, the code and documentation created for this project may not be reused, modified, or redistributed without my permission. Third-party news content, software, and models remain subject to their respective rights and licenses.
