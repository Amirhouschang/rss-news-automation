# Stage 4 — English Sources and Local Model Comparison

[Project overview](../README.md)

## Objective

Use English publisher editions, keep the original English titles, and summarize without translation. Tested sources were DW, IRNA, ECNS, TASS, and Ukrinform. The final daily China source is CGTN, introduced in Stage 6.

[prepare_news.py](prepare_news.py) prepares inputs; [summarize_news_test.py](summarize_news_test.py) invokes Ollama. Stage 6 imports helpers from both files, so they must remain available.

## Frozen input

The [raw snapshot](data/raw/rss_20261007_161827_481006.json) contains **396 entries**. The [prepared sample](data/prepared/prepared_20261007_161827_481006.json) has **25 records**, five per country: **15 article-based and 10 RSS-summary-based**. IRNA and TASS supplied the RSS-summary inputs.

An [earlier prepared snapshot](data/prepared/prepared_20261007_161019_676396.json) has 20 records and no Russian records. I kept it as development evidence; the comparison uses the complete 25-record sample.

## Saved model runs

| Saved run | Model | Attempts | Accepted | Mean request time |
|---|---|---:|---:|---:|
| [summaries_20261007_162017_072906.json](data/summaries/summaries_20261007_162017_072906.json) | `qwen3.6:35b` | 25 | 25 | 6.17 s |
| [summaries_20261007_162321_950701.json](data/summaries/summaries_20261007_162321_950701.json) | `gemma4:31b` | 5 | 5 | 29.18 s |
| [summaries_20261007_162321_950701.json](data/summaries/summaries_20261007_162321_950701.json) | `mistral-small3.1:latest` | 5 | 5 | 16.58 s |
| [summaries_20261007_163137_014229.json](data/summaries/summaries_20261007_163137_014229.json) | `mistral-small3.1:latest` | 25 | 25 | 17.02 s |
| [summaries_20261007_164817_107388.json](data/summaries/summaries_20261007_164817_107388.json) | `mistral-small3.1:latest` | 25 | 25 | 15.23 s |
| [summaries_20261007_165544_807344.json](data/summaries/summaries_20261007_165544_807344.json) | `gpt-oss:120b` | 5 | 5 | 40.51 s |

Timings are means of the saved request `elapsed` values; a full automation run takes longer. `gpt-oss:120b` ran locally through Ollama and is separate from the cloud comparison in Stage 5. The five-record runs are too small to rank the models.

The **original-prompt Mistral run, `163137_014229`,** is the retained baseline. The later `164817_107388` run tested a revised prompt. The supplied code uses the original English prompt. The [development report for Stages 1–5](../RSS_Project_Stages_1_to_5.md) records the manual review; the examples below point to the corresponding saved outputs.

## Quality and decision

The [Mistral quality report](data/quality/quality_report_20261007_170702_468681Z.md) checks 25 outputs: **1 flagged, 24 unflagged**, plus five additional review samples. The one numerical warning is a false alarm: the output writes `million` where the source writes `mln`.

For the manual comparison I used the original title and prepared text stored with each output. Record numbers below are one-based positions in each run's `attempts` list. The comparison checks whether a summary matches its input; it does not check whether the publisher's report is true.

| Run and record | Observation from the saved input and output |
|---|---|
| [Qwen, record 11](data/summaries/summaries_20261007_162017_072906.json) — Taihang Pass | The output claims structural integrity over three millennia. The input describes an ancient route and buildings still recognizable from photographs taken in 1896; it says nothing about three millennia of structural integrity. |
| [Qwen, record 22](data/summaries/summaries_20261007_162017_072906.json) — Kremenchuk | The input distinguishes 35 damaged private houses from six additional destroyed houses. The output says six of the 35 homes were destroyed, changing the relationship between the counts. |
| [Revised Mistral, record 20](data/summaries/summaries_20261007_164817_107388.json) — machinery funding | The output introduces `2024`, while the supplied description says `next year` and the title refers to 2027–2029. The original-prompt output retains `next year`. |
| [Revised Mistral, record 3](data/summaries/summaries_20261007_164817_107388.json) — Merz and the AfD vote | The output refers to AfD sympathizers in Merz's own ranks and drops the input's uncertainty about whether the extra votes came from the CDU. The original-prompt output refers to potential support from his party. |

The revised prompt did improve one thing. In record 23 it makes the injury update clearer: it reports two injured people and two hospitalizations. The original-prompt output also mentions an earlier report of one injured person and leaves the order of the updates unclear. But this gain came with the unsupported year and the lost uncertainty shown above.

**Decision:** I kept Mistral with the original prompt as the local model for daily operation. Qwen was faster, but speed alone did not decide it: I made the choice after reviewing the sample outputs above. It is a practical choice based on this sample of 25 records, not a measured quality ranking.

The retained Mistral baseline has weaknesses too. In [record 5](data/summaries/summaries_20261007_163137_014229.json), its summary focuses on musicians returning to Iran and omits the article's discussion of music as political control and resistance. In record 21, it adds `Volodymyr`, which is absent from the supplied title and prepared text.

Switching to English editions also changed publishers and article selection, so Stage 3 and Stage 4 cannot be compared as a pure translation test.

## Example commands

From the repository root:

```bash
python stage4/summarize_news_test.py --input stage4/data/prepared/prepared_20261007_161827_481006.json --limit-per-country 5 --models mistral-small3.1:latest --think off
python stage3/check_summaries.py --input stage4/data/summaries/summaries_20261007_163137_014229.json --language en --output-dir stage4/data/quality
```

Generating again creates a separate result file. Each archived JSON keeps the prompt and settings used in its original run.
