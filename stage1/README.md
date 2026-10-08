# Stage 1 — RSS Collection and Article Diagnostics

[Project overview](../README.md)

## Objective

Fetch multilingual RSS feeds, preserve original text and metadata, save results, and test whether linked articles can be extracted.

The initial publishers were Tagesschau, IRNA, Chinanews, TASS, and Ukrinform. These differ from the final daily configuration.

## Files

- [rss_test.py](rss_test.py): feed collection and timestamped JSON snapshots.
- [article_test.py](article_test.py): one linked article per country for extraction testing.
- [source_diagnostic.py](source_diagnostic.py): additional IRNA/TASS access tests and available RSS descriptions.
- [data/raw](data/raw), [data/articles](data/articles), and [data/diagnostics](data/diagnostics): archived test evidence.
- [rss_stage1_chat.txt](rss_stage1_chat.txt): exported Ollama Modelfile containing the saved coding prompts and model responses. It documents development dialogue, not model training.

## Observed results

The [raw snapshot](data/raw/rss_20261007T080917933739Z.json) contains **261 entries**: Germany 71, Iran 30, China 30, Russia 100, Ukraine 30.

The three saved article tests document successive corrections:

- [First test — 082352](data/articles/articles_test_20261007T082352600852Z.json): the 70-character IRNA interstitial was incorrectly classified as extracted article text.
- [Second test — 082951](data/articles/articles_test_20261007T082951378799Z.json): the IRNA interstitial was correctly detected, but the TASS failure was recorded as an extraction error.
- [Corrected test — 083820](data/articles/articles_test_20261007T083820504493Z.json): the TASS HTTP 403 response was correctly recorded as a download failure. This final test contains three extracted articles, one IRNA interstitial, and one TASS download failure.

Each of the two [diagnostic runs](data/diagnostics) tested three IRNA and three TASS URLs. Neither produced usable article text. RSS descriptions remained available. A successful feed response or HTTP 200 does not certify article access.

## Example commands

Run from the repository root:

```bash
python stage1/rss_test.py
python stage1/article_test.py --input stage1/data/raw/rss_20261007T080917933739Z.json
python stage1/source_diagnostic.py --previous-results stage1/data/articles/articles_test_20261007T083820504493Z.json
```

Feed requests obtain live data; they do not reproduce the frozen 2026 snapshot exactly. This stage established collection and explicit detection of unusable article responses, supporting RSS fallbacks in later stages.
