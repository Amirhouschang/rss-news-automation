# Stage 3 — Local Multilingual Summarization

[Project overview](../README.md)

## Objective

Compare existing local Ollama models on frozen multilingual news input, producing English and German summaries. This combines translation and summarization rather than testing translation alone.

## Files and inputs

- [summarize_news_test.py](summarize_news_test.py): generation, response validation, prompts, model identity, timing, JSON results, and Markdown reports.
- [check_summaries.py](check_summaries.py): offline heuristic review and review-sample selection.
- [Stage 2 prepared input](../stage2/data/prepared/prepared_20261007_115940_871486.json): 25 records, with mixed article and RSS-summary bases.
- [rss_stage3_chat.txt](rss_stage3_chat.txt): saved local coding dialogue within an Ollama Modelfile export.

## Saved runs

| Saved run | Model | Attempts | Accepted | Mean request time |
|---|---|---:|---:|---:|
| [summaries_20261007_124847_662402.json](data/summaries/summaries_20261007_124847_662402.json) | `gemma4:31b` | 10 | 10 | 264.36 s |
| [summaries_20261007_124847_662402.json](data/summaries/summaries_20261007_124847_662402.json) | `mistral-small3.1:latest` | 10 | 10 | 25.59 s |
| [summaries_20261007_124847_662402.json](data/summaries/summaries_20261007_124847_662402.json) | `qwen3.6:35b` | 10 | 5 | 65.83 s |
| [summaries_20261007_135428_400898.json](data/summaries/summaries_20261007_135428_400898.json) | `aya-expanse:32b` | 10 | 10 | 36.83 s |
| [summaries_20261007_141154_295166.json](data/summaries/summaries_20261007_141154_295166.json) | `qwen3.6:35b` | 10 | 10 | 7.66 s |
| [summaries_20261007_142738_408595.json](data/summaries/summaries_20261007_142738_408595.json) | `qwen3.6:35b` | 10 | 10 | 7.86 s |
| [summaries_20261007_143304_261130.json](data/summaries/summaries_20261007_143304_261130.json) | `gemma4:31b` | 10 | 10 | 47.59 s |
| [summaries_20261007_151313_799927.json](data/summaries/summaries_20261007_151313_799927.json) | `gemma4:31b` | 10 | 10 | 48.05 s |
| [summaries_20261007_151313_799927.json](data/summaries/summaries_20261007_151313_799927.json) | `qwen3.6:35b` | 10 | 10 | 8.16 s |
| [summaries_20261007_152729_414957.json](data/summaries/summaries_20261007_152729_414957.json) | `qwen3.6:35b` | 50 | 50 | 7.14 s |

Mean request times are computed from the saved `elapsed` fields, include loading/request overhead, and are not total workflow runtimes. The early mixed-model run used a different configuration; its Qwen errors must not be hidden by later successful runs. Prompt and thinking changes are recorded in the individual JSON files.

The larger Qwen run accepted **50 outputs**, 25 English and 25 German. This is technical response acceptance, not proof of translation or summary quality.

## Quality check

The [quality report](data/quality/quality_report_20261007_154526_295540Z.md) checks the 25 English outputs from the larger Qwen run: **2 need review, 23 are unflagged**, with five additional unflagged review samples. The [JSON check](data/quality/quality_20261007_154526_295540Z.json) preserves the results.

The checker is not a semantic fact checker or reliable language detector. Matching numbers can still describe the wrong event. These counts do not establish that English is generally better than German.

## Reproduce a generation or check

From the repository root, with the named model installed in Ollama:

```bash
python stage3/summarize_news_test.py --input stage2/data/prepared/prepared_20261007_115940_871486.json --limit-per-country 5 --models qwen3.6:35b --think off
python stage3/check_summaries.py --input stage3/data/summaries/summaries_20261007_152729_414957.json --language en
```

Current code represents a saved final version, not every historic prompt variant. Read each run's recorded prompt and settings when interpreting earlier results.
