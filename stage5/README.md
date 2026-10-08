# Stage 5 — Optional Cloud Comparison

[Project overview](../README.md)

## Purpose and access method

[summarize_news_cloud.py](summarize_news_cloud.py) tested cloud summarization using the same [frozen Stage 4 input](../stage4/data/prepared/prepared_20261007_161827_481006.json) and the retained English prompt. Original titles remain unchanged; translation is disabled.

The saved metadata records `sign_in_with_chatgpt_plan` as the access method: the script signs in with a ChatGPT plan instead of using a paid API key. This worked for my account and application during the experiment. Other subscriptions may behave differently, and the model slugs and account capabilities are recorded as they were on that day. Local inference remains the main approach of the daily project.

## Saved runs

| Saved run | Model | Attempts | Accepted | Mean request time |
|---|---|---:|---:|---:|
| [summaries_20261007_173009_467695Z.json](data/summaries/summaries_20261007_173009_467695Z.json) | `gpt-5.6-sol` | 5 | 5 | 3.99 s |
| [summaries_20261007_173234_262887Z.json](data/summaries/summaries_20261007_173234_262887Z.json) | `gpt-5.6-sol` | 10 | 9 | 4.03 s |
| [summaries_20261007_173408_673609Z.json](data/summaries/summaries_20261007_173408_673609Z.json) | `gpt-6-astra` | 25 | 25 | 11.06 s |
| [summaries_20261007_174007_180201Z.json](data/summaries/summaries_20261007_174007_180201Z.json) | `gpt-5.6-sol` | 25 | 25 | 4.42 s |

The interrupted Sol run selected 25 records but attempted only 10: nine were accepted, one returned HTTP 503, and fifteen were not attempted. I left it out of the final comparison. The saved error gives no cause, so it is no evidence that the content was rejected.

The final runs are `174007_180201Z` for Sol and `173408_673609Z` for Astra. Each accepted 25 outputs. The request times include service and network delays, so they describe these two runs and are not a general speed ranking.

## Quality evidence

- [Sol quality report](data/quality/sol/quality_report_20261007_175233_419718Z.md): 25 checked, 2 flagged, 23 unflagged.
- [Astra quality report](data/quality/astra/quality_report_20261007_175233_497896Z.md): 25 checked, 1 flagged, 24 unflagged.
- [Supplementary source-comparison report](../stage5_quality_checks/stage5_cloud_comparison.md): my manual observations and earlier copies of the checker output.

The manual review found that all three numerical flags are false positives: `mln` versus `million`, and `Thirty-five` versus `35`. It also found two Sol deviations that the checker missed: the EU's concern was narrowed to the EC, and a first name was added that is absent from the input. In the 25 Astra outputs I found no clear content errors. These findings apply to this sample; they do not predict future outputs and do not verify the news itself.

## Offline reproduction

You can inspect the saved outputs and rerun the heuristic checker without a cloud account:

```bash
python stage3/check_summaries.py --input stage5/data/summaries/summaries_20261007_174007_180201Z.json --language en --output-dir stage5/data/quality/sol --report-all
python stage3/check_summaries.py --input stage5/data/summaries/summaries_20261007_173408_673609Z.json --language en --output-dir stage5/data/quality/astra --report-all
```

Run the commands from the repository root. A live cloud run depends on what the service currently allows for your account; the login code is kept as a record of the experiment. Keep authentication data outside the repository.
