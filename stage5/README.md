# Stage 5 — Optional Cloud Comparison

[Project overview](../README.md)

## Purpose and access method

[summarize_news_cloud.py](summarize_news_cloud.py) tested cloud summarization using the same [frozen Stage 4 input](../stage4/data/prepared/prepared_20261007_161827_481006.json) and retained English prompt. Original titles remain unchanged; translation is disabled.

Saved metadata records `sign_in_with_chatgpt_plan` as the access method. This was observed to work for the account/application during the experiment. It is not a conventional API-key billing experiment or a promise that every subscription supports these requests. Model slugs and account capabilities are recorded historical observations. Local inference remains the daily project's main approach.

## Saved runs

| Saved run | Model | Attempts | Accepted | Mean request time |
|---|---|---:|---:|---:|
| [summaries_20261007_173009_467695Z.json](data/summaries/summaries_20261007_173009_467695Z.json) | `gpt-5.6-sol` | 5 | 5 | 3.99 s |
| [summaries_20261007_173234_262887Z.json](data/summaries/summaries_20261007_173234_262887Z.json) | `gpt-5.6-sol` | 10 | 9 | 4.03 s |
| [summaries_20261007_173408_673609Z.json](data/summaries/summaries_20261007_173408_673609Z.json) | `gpt-6-astra` | 25 | 25 | 11.06 s |
| [summaries_20261007_174007_180201Z.json](data/summaries/summaries_20261007_174007_180201Z.json) | `gpt-5.6-sol` | 25 | 25 | 4.42 s |

The interrupted Sol run selected 25 records but attempted only 10: nine were accepted, one returned HTTP 503, and fifteen were not attempted. It is excluded from the final complete-run comparison. Its diagnostic does not establish the underlying service cause or content-based rejection.

The final runs use `174007_180201Z` for Sol and `173408_673609Z` for Astra. Each accepted 25 outputs. Request means include service/network effects and do not establish a general speed ranking.

## Quality evidence

- [Sol quality report](data/quality/sol/quality_report_20261007_175233_419718Z.md): 25 checked, 2 flagged, 23 unflagged.
- [Astra quality report](data/quality/astra/quality_report_20261007_175233_497896Z.md): 25 checked, 1 flagged, 24 unflagged.
- [Supplementary source-comparison report](../stage5_quality_checks/stage5_cloud_comparison.md): archived manual observations and earlier checker copies. Its literal file references describe the review context; use this README for repository navigation.

The supplementary review records all three numerical flags as false positives: `mln` versus `million`, and `Thirty-five` versus `35`. It also identifies two Sol deviations not caught by the checker: EU concern narrowed to the EC and a first name added beyond the permitted input. It reports no clear content errors in the 25 Astra outputs reviewed. Those are findings for this sample, not guarantees for future generation or independent verification of the news.

## Offline reproduction

No cloud account is required to inspect the saved outputs or rerun the existing heuristic checker:

```bash
python stage3/check_summaries.py --input stage5/data/summaries/summaries_20261007_174007_180201Z.json --language en --output-dir stage5/data/quality/sol --report-all
python stage3/check_summaries.py --input stage5/data/summaries/summaries_20261007_173408_673609Z.json --language en --output-dir stage5/data/quality/astra --report-all
```

Commands run from the repository root. Live cloud reproduction depends on current authorized service capabilities; the recorded login experiment is preserved as historical code. Authentication data belongs outside the repository.
