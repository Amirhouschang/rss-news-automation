# Stage 2 — Text Preparation and Fallbacks

[Project overview](../README.md)

## Objective and implementation

[prepare_news.py](prepare_news.py) fetches feeds and prepares records with original title, URL, dates, article-access diagnostics, cleaned text, and a `text_basis` label. It prefers article text and falls back to feed content or descriptions when the article is unavailable. This stage does not call a language model.

The stage uses the original-language source configuration. It takes a limited number of entries per country to test preparation; the uniform random daily selection comes later, in Stage 6.

## Frozen evidence

The [raw snapshot](data/raw/rss_20261007_115940_871486.json) contains **265 entries**. The [prepared sample](data/prepared/prepared_20261007_115940_871486.json) contains **25 records**, five per country: **15 article-based and 10 RSS-summary-based**. This is the frozen input for Stage 3.

[Saved coding dialogue](rss_stage2_chat.txt) is an Ollama Modelfile export with embedded messages. It records the prompt and code iterations; no model was fine-tuned.

During development I corrected optional parser attributes, variable initialization, and malformed strings. Network diagnostics on my machine showed IPv6 timeouts and connectivity that depended on the VPN. Other machines and networks may behave differently.

## Example command

From the repository root:

```bash
python stage2/prepare_news.py --limit-per-country 5
```

A fresh execution writes new files to [data/raw](data/raw) and [data/prepared](data/prepared). Use the saved prepared input when comparing models, so that changing feed content does not become an additional variable.

An `article` label means text was extracted; some paragraphs may still be missing. An `rss_summary` label marks short feed text. Publication-date filtering for daily operation belongs to Stage 6.
