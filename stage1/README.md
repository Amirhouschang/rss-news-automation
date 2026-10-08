# Stage 1 — RSS Collection and Article Diagnostics

[Project overview](../README.md)

## Objective

Fetch multilingual RSS feeds, keep the original text and metadata, save the results, and test whether the linked articles can be extracted.

The initial publishers were Tagesschau, IRNA, Chinanews, TASS, and Ukrinform. The final daily configuration uses different sources.

## Files

- [rss_test.py](rss_test.py): feed collection and timestamped JSON snapshots.
- [article_test.py](article_test.py): one linked article per country for extraction testing.
- [source_diagnostic.py](source_diagnostic.py): additional IRNA/TASS access tests and available RSS descriptions.
- [data/raw](data/raw), [data/articles](data/articles), and [data/diagnostics](data/diagnostics): archived test evidence.
- [rss_stage1_chat.txt](rss_stage1_chat.txt): exported Ollama Modelfile containing the saved coding prompts and model responses. It records the development dialogue; no model was trained.

## Observed results

The [raw snapshot](data/raw/rss_20261007T080917933739Z.json) contains **261 entries**: Germany 71, Iran 30, China 30, Russia 100, Ukraine 30.

The three saved article tests show how the script was corrected step by step:

- [First test — 082352](data/articles/articles_test_20261007T082352600852Z.json): the 70-character IRNA interstitial was incorrectly classified as extracted article text.
- [Second test — 082951](data/articles/articles_test_20261007T082951378799Z.json): the IRNA interstitial was correctly detected, but the TASS failure was recorded as an extraction error.
- [Corrected test — 083820](data/articles/articles_test_20261007T083820504493Z.json): the TASS HTTP 403 response was correctly recorded as a download failure. This final test contains three extracted articles, one IRNA interstitial, and one TASS download failure.

Each of the two [diagnostic runs](data/diagnostics) tested three IRNA and three TASS URLs. Neither produced usable article text, but the RSS descriptions remained available. The lesson: a working feed or an HTTP 200 response does not mean the article itself can be read.

## Example commands

Run from the repository root:

```bash
python stage1/rss_test.py
python stage1/article_test.py --input stage1/data/raw/rss_20261007T080917933739Z.json
python stage1/source_diagnostic.py --previous-results stage1/data/articles/articles_test_20261007T083820504493Z.json
```

Feed requests fetch live data, so a new run will differ from the frozen 2026 snapshot. This stage delivered working collection and reliable detection of unusable article responses, which is why later stages fall back to RSS text.
