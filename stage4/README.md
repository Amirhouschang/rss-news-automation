# Stage 4 — English Sources and Local Model Comparison

[Project overview](../README.md)

## Objective

Use English publisher editions, preserve original English titles, and summarize without translation. Tested sources were DW, IRNA, ECNS, TASS, and Ukrinform. The final daily China source is CGTN, introduced in Stage 6.

[prepare_news.py](prepare_news.py) prepares inputs; [summarize_news_test.py](summarize_news_test.py) invokes Ollama. These files also supply helpers to Stage 6 and must remain available.

## Frozen input

The [raw snapshot](data/raw/rss_20261007_161827_481006.json) contains **396 entries**. The [prepared sample](data/prepared/prepared_20261007_161827_481006.json) has **25 records**, five per country: **15 article-based and 10 RSS-summary-based**. IRNA and TASS supplied the RSS-summary inputs.

An [earlier prepared snapshot](data/prepared/prepared_20261007_161019_676396.json) has 20 records and no Russian records. It is retained as development evidence rather than treated as the complete comparison sample.

## Saved model runs

| Saved run | Model | Attempts | Accepted | Mean request time |
|---|---|---:|---:|---:|
| [summaries_20261007_162017_072906.json](data/summaries/summaries_20261007_162017_072906.json) | `qwen3.6:35b` | 25 | 25 | 6.17 s |
| [summaries_20261007_162321_950701.json](data/summaries/summaries_20261007_162321_950701.json) | `gemma4:31b` | 5 | 5 | 29.18 s |
| [summaries_20261007_162321_950701.json](data/summaries/summaries_20261007_162321_950701.json) | `mistral-small3.1:latest` | 5 | 5 | 16.58 s |
| [summaries_20261007_163137_014229.json](data/summaries/summaries_20261007_163137_014229.json) | `mistral-small3.1:latest` | 25 | 25 | 17.02 s |
| [summaries_20261007_164817_107388.json](data/summaries/summaries_20261007_164817_107388.json) | `mistral-small3.1:latest` | 25 | 25 | 15.23 s |
| [summaries_20261007_165544_807344.json](data/summaries/summaries_20261007_165544_807344.json) | `gpt-oss:120b` | 5 | 5 | 40.51 s |

Timings are means of saved request `elapsed` values, not end-to-end automation times. `gpt-oss:120b` ran locally through Ollama; it is not the cloud ChatGPT comparison. Small five-record runs do not establish a general ranking.

The **original-prompt Mistral run, `163137_014229`,** is the retained baseline. The later `164817_107388` run tested a revised prompt. The existing development report records that this revision corrected one presentation issue but introduced other source-fidelity problems; the original prompt was retained. The currently supplied code contains that retained English prompt.

## Quality and decision

The [Mistral quality report](data/quality/quality_report_20261007_170702_468681Z.md) checks 25 outputs: **1 flagged, 24 unflagged**, plus five additional review samples. The recorded numerical warning concerns equivalent `mln`/`million` representations, not a confirmed numerical error. Automatic non-flags do not establish semantic accuracy.

The documented source comparisons found issues beyond numerical flags, including omissions, chronology, and details added beyond the supplied input. Mistral was retained as the operational local baseline, not declared universally best. Qwen was faster in the saved larger English run.

Switching to English editions also changed publishers and article selection. Stage 3 versus Stage 4 is therefore not a controlled experiment isolating translation.

## Example commands

From the repository root:

```bash
python stage4/summarize_news_test.py --input stage4/data/prepared/prepared_20261007_161827_481006.json --limit-per-country 5 --models mistral-small3.1:latest --think off
python stage3/check_summaries.py --input stage4/data/summaries/summaries_20261007_163137_014229.json --language en --output-dir stage4/data/quality
```

Generating again creates a separate result file. Archived JSON retains the prompt/settings actually used in its original run.
