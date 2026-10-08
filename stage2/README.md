# Stage 2 — Text Preparation and Fallbacks

[Project overview](../README.md)

## Objective and implementation

[prepare_news.py](prepare_news.py) fetches feeds and prepares records with original title, URL, dates, article-access diagnostics, cleaned text, and a `text_basis` label. Available article text is preferred; feed content or descriptions provide fallbacks. No language model is called during preparation.

The stage uses the original-language source configuration. Its limited selection is a preparation test, not the final uniform random daily selection introduced in Stage 6.

## Frozen evidence

The [raw snapshot](data/raw/rss_20261007_115940_871486.json) contains **265 entries**. The [prepared sample](data/prepared/prepared_20261007_115940_871486.json) contains **25 records**, five per country: **15 article-based and 10 RSS-summary-based**. This is the frozen input for Stage 3.

[Saved coding dialogue](rss_stage2_chat.txt) is an Ollama Modelfile export with embedded messages. It records prompt/code iteration, not fine-tuning.

Development included correcting optional parser attributes, variable initialization, and malformed strings. Network diagnostics indicated IPv6 timeouts and VPN-dependent connectivity on the tested machine. Those observations do not establish universal behavior for IPv6 or VPNs.

## Example command

From the repository root:

```bash
python stage2/prepare_news.py --limit-per-country 5
```

A fresh execution writes new files to [data/raw](data/raw) and [data/prepared](data/prepared). Use saved prepared input when comparing models so changing feed content does not become an additional variable.

An `article` label means text was extracted, not that every paragraph was captured. An `rss_summary` label identifies limited feed text. Publication-date filtering for daily operation belongs to Stage 6.
