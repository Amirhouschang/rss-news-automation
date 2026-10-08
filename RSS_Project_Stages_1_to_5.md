# RSS News Automation — Stages 1–5

Project record: 7 October 2026. This report documents the development status at the end of Stage 5. The final automation was implemented subsequently and is described in [Stage 6](stage6/README.md). Code and comments are written in English; the repository also provides German and English project overviews. Local inference is the primary approach; cloud inference is an optional comparison.

## Project overview

The project collects news from five countries, prepares available text and generates concise summaries. Development proceeded through five documented stages rather than replacing the entire pipeline at each step.

| Stage | Purpose | Recorded outcome |
|---|---|---|
| 1 | Fetch multilingual RSS feeds and test article access | RSS collection and JSON persistence worked; article-access limitations were identified |
| 2 | Prepare records with explicit text provenance | A fixed sample of 25 records was prepared, including article text and RSS-summary fallbacks |
| 3 | Test local multilingual summarization | Local models generated English and German outputs; Qwen completed a 50-output run |
| 4 | Use English-language feeds and compare local models | Translation was removed; original English titles were retained; local quality review was completed |
| 5 | Compare cloud outputs against the same English inputs | Sol and Astra each completed 25 outputs; offline and manual review were recorded |

These five stages are development and evaluation work. The scheduled daily pipeline was built afterwards, in Stage 6.

### Interpretation rules

An RSS feed shows a changing window of entries, not everything a publisher has published. A per-country limit takes a sample from that window. Five records per country are a small sample and do not represent a country or a publisher.

An `article` text basis means that article text was extracted; some paragraphs of the publisher's page may still be missing. An `rss_summary` basis means that only the feed description was available. Outputs and documentation always show which of the two was used.

A generation status of `success` means that the script accepted the response. Whether the summary is correct is a separate question: offline checks flag possible problems, and a manual comparison with the source assesses meaning and coverage.

## Stage 1 — RSS collection and article-access diagnostics

### Objective

Verify that feeds from Germany, Iran, China, Russia and Ukraine can be downloaded and parsed, retain their original text and save the results for later processing.

### Implementation

`rss_test.py` uses Requests and Feedparser, collects entries and source-status records, and writes timestamped UTF-8 JSON snapshots. Non-Latin text is preserved using `ensure_ascii=False`. All retrieved entries are saved, while the terminal preview displays only a small subset.

| Country | Publisher | Initial feed |
|---|---|---|
| Germany | Tagesschau | https://www.tagesschau.de/index~rss2.xml |
| Iran | IRNA | https://www.irna.ir/rss |
| China | Chinanews | https://www.chinanews.com.cn/rss/scroll-news.xml |
| Russia | TASS | https://tass.ru/rss/v2.xml |
| Ukraine | Ukrinform | https://www.ukrinform.ua/rss/block-lastnews |

The response is parsed independently of its Content-Type header, and the recognized feed format is checked. Empty recognized feeds and failed requests are separate conditions. UTC timestamps were updated to timezone-aware datetime handling after a deprecation warning.

`article_test.py` and `source_diagnostic.py` then tested article retrieval and extraction. Interstitial pages were explicitly rejected rather than counted as article text.

### Observed results

The snapshot [rss_20261007T080917933739Z.json](stage1/data/raw/rss_20261007T080917933739Z.json) contains 261 entries: 71 from Tagesschau, 30 from IRNA, 30 from Chinanews, 100 from TASS and 30 from Ukrinform.

The corrected five-URL article test produced three successful extractions, one IRNA interstitial and one TASS download failure. The saved result is [articles_test_20261007T083820504493Z.json](stage1/data/articles/articles_test_20261007T083820504493Z.json).

Two additional diagnostic runs each tested three IRNA and three TASS URLs. Both runs produced zero successful article extractions: IRNA returned interstitial pages, and TASS article requests returned HTTP 403. RSS summaries remained available.

### Limitations and conclusion

A working RSS feed does not mean the article can be read, and an HTTP 200 response may contain an interstitial instead of an article. The diagnostics are the reason for the fallback to RSS descriptions. Access may differ in other environments.

Stage 1 delivered working collection, saved results and reliable detection of unusable article responses.

## Stage 2 — Text preparation and fallback handling

### Objective

Convert feed entries into traceable records suitable for model input, while retaining original metadata and the reason a particular text basis was selected.

### Implementation

`prepare_news.py` fetches feeds, selects a configurable number of entries per country and attempts article extraction. It prepares available text using article extraction or feed-provided content and summaries. It saves a raw snapshot and a prepared-results JSON file under the stage's `data/raw/` and `data/prepared/` directories.

The output keeps country, source, original title, URL and text provenance. It records an article failure separately from the fallback text, because a rejected article can still come with a usable RSS description.

### Observed results

The frozen input used for Stage 3, [prepared_20261007_115940_871486.json](stage2/data/prepared/prepared_20261007_115940_871486.json), contains 25 records, five per country. Fifteen records use article text and ten use RSS summaries.

Early runs encountered missing optional parser attributes, uninitialized variables and malformed Python strings. I corrected those defects before using the final sample. Compiling the script was only a first check; network access and runtime behavior were tested by running it.

Network diagnostics also explained much of the early delay. A Tagesschau IPv4 request completed in approximately 0.24 seconds, while the corresponding IPv6 test timed out after 20 seconds. TASS feed access failed in some VPN tests but completed without the VPN in approximately 0.45 seconds. A later one-record-per-country preparation run completed in approximately four seconds.

### Limitations and conclusion

These network results come from my machine; other machines and networks may behave differently. Source availability can also change between runs. For this reason, all model comparisons use one fixed prepared input instead of a fresh sample for every model.

Character counts and text-basis labels describe the input that was available, not its completeness or truth. Stage 2 delivered a reusable preparation step and made the limits of the input visible.

## Stage 3 — Local multilingual summarization

### Objective

Test local Ollama models on the same prepared news records, generating concise English and German outputs from multilingual inputs.

### Implementation

`summarize_news_test.py` reads saved prepared records, selects up to a configurable number per country and invokes the named local model. It saves response data, model identity, prompt and generation settings, elapsed times and a Markdown comparison report.

The prompt asks for summaries that stay faithful to the source, without outside additions or political reframing, and that keep the source's meaning, certainty and attribution. Whether the publisher's statements are true is outside the task.

### Observed runs

| Model and run | Records | Output languages | Successful outputs | Sum of request times |
|---|---:|---|---:|---:|
| Aya Expanse 32B, `135428_400898` | 5 | English and German | 10/10 | Approximately 368 seconds |
| Qwen 3.6 35B, `141154_295166` | 5 | English and German | 10/10 | Approximately 77 seconds |
| Gemma 4 31B, `143304_261130` | 5 | English and German | 10/10 | Approximately 476 seconds |
| Qwen 3.6 35B, `152729_414957` | 25 | English and German | 50/50 | Approximately 357 seconds |

The final Qwen run produced 25 English and 25 German outputs. I observed a total execution time of approximately five minutes and 57 seconds. Qwen used thinking disabled in these successful runs. A small direct Ollama JSON-response test also confirmed that the model could respond with thinking disabled.

### Quality review

`check_summaries.py` checked the 25 English outputs in the larger Qwen run. It marked two for review, left 23 unflagged and selected five additional unflagged samples for inspection. An unflagged output has passed the heuristic check only; it has not been verified.

The check covers English outputs from one model, so it says nothing about English versus German or about which model is best. Translation accuracy can only be judged by comparing outputs with the original-language inputs, not by counting successful outputs.

### Limitations and conclusion

The sample combines extracted article text with short RSS descriptions. Comparing speeds across countries is affected by differences in input length. Generating a summary in another language combines translation and summarization, so an error may originate in either task.

Stage 3 delivered working local multilingual generation and a repeatable output review. It also led to the next experiment: using English input, so that translation is no longer part of every run.

## Stage 4 — English feeds and local model comparison

### Objective

Remove the translation task by using English-language news inputs, copy original titles unchanged and ask the model only to summarize the supplied English text.

### Sources and prepared sample

| Country | Publisher | English feed |
|---|---|---|
| Germany | DW | https://rss.dw.com/rdf/rss-en-all |
| Iran | IRNA | https://en.irna.ir/rss |
| China | ECNS | https://www.ecns.cn/rss/rss.xml |
| Russia | TASS | https://tass.com/rss/v2.xml |
| Ukraine | Ukrinform | https://www.ukrinform.net/rss/block-lastnews |

The frozen sample is [prepared_20261007_161827_481006.json](stage4/data/prepared/prepared_20261007_161827_481006.json). The feed snapshot contains 396 entries, of which 25 were selected, five per country. Fifteen selected records use extracted article text; ten use RSS summaries. The latter are the IRNA and TASS records.

For the tested TASS English feed, a request with a browser-style User-Agent and XML Accept header returned HTTP 200 after a simpler request returned HTTP 403. This applies to the feed only; TASS article pages remained inaccessible.

### Local runs

| Model and run | Outputs | Accepted outputs | Sum of request times |
|---|---:|---:|---:|
| Qwen 3.6 35B, `162017_072906` | 25 | 25/25 | 154.21 seconds |
| Mistral Small 3.1, original prompt, `163137_014229` | 25 | 25/25 | 425.56 seconds |
| Mistral Small 3.1, revised prompt, `164817_107388` | 25 | 25/25 | 380.80 seconds |
| GPT-OSS 120B, `165544_807344` | 5 | 5/5 | 202.56 seconds |

Gemma 4 31B was also tested on the five-record sample, completing five accepted outputs. GPT-OSS 120B is a local Ollama model in this experiment; its successful run is separate from the cloud comparison in Stage 5.

### Manual observations and prompt decision

I compared the accepted responses with their sources. In the Qwen sample, record 11 claimed that the Taihang Pass had maintained its structural integrity over three millennia. The input describes an ancient route and buildings recognizable from photographs taken in 1896, but says nothing about three millennia of structural integrity. In record 22, the output described six destroyed houses as part of the 35 damaged houses, although the input identifies six additional destroyed houses.

The revised Mistral prompt made the injury update clearer in record 23: it reports two injured people and two hospitalizations. The original-prompt output also mentions an earlier report of one injured person without making the update sequence clear. However, the revised run introduced other problems. Record 20 adds the year 2024 where the supplied description says `next year`; record 3 no longer preserves the uncertainty about potential CDU votes. I therefore kept the original prompt for the final comparison. The decision is based on this sample.

The original Mistral run has weaknesses too. Record 5 focuses on musicians returning to Iran but omits the article's discussion of music as political control and resistance. Record 23 has the injury-update ambiguity described above. Record 21 adds Zelensky's first name even though that name was absent from the supplied title and prepared text.

Record numbers are one-based positions in the saved runs' `attempts` lists. The [Stage 4 README](stage4/README.md) links these observations to the exact saved result files. These comparisons check whether a summary matches its input; they do not check whether the publisher's report is true.

### Offline quality check

The original Mistral run was checked in [quality_20261007_170702_468681Z.json](stage4/data/quality/quality_20261007_170702_468681Z.json): 25 outputs checked, one marked for review, 24 unflagged and five additional unflagged samples. The numerical flag was a false alarm caused by `mln` versus `million`; the two monetary values referred to the correct separate periods.

### Limitations and conclusion

English editions may publish a different selection from the original-language editions. Germany's publisher also changed from Tagesschau to DW. Stages 3 and 4 therefore do not isolate translation as the only experimental difference.

I kept the larger Mistral run with the original prompt as the local baseline. Qwen was faster in its recorded run; I assessed speed and fidelity separately. The five-record tests are too small to rank the models. Stage 4 removed translation from the task and kept the original English titles.

## Stage 5 — Optional cloud comparison

### Objective

Compare cloud-generated summaries with local outputs using exactly the same frozen English sample and the retained Stage 4 prompt. Local inference remains the primary project approach.

### Implementation

`summarize_news_cloud.py` uses authenticated cloud access through Sign in with ChatGPT, which was confirmed to work for this account and application during the experiment. It lists the account's available models, submits source text, accepts completed structured responses and saves JSON results and Markdown reports. Original titles are copied unchanged.

Credentials are stored outside the project. Result files record the prompt, model, input and timings. The script saves progress and stops on the first request error; a new execution starts a separate timestamped run.

### Final runs

| Model | Selected records | Accepted outputs | Sum of request times | Mean request time | Observed total runtime |
|---|---:|---:|---:|---:|---:|
| GPT-5.6-Sol | 25 | 25/25 | 110.62 seconds | 4.42 seconds | Approximately 1 minute 51 seconds |
| GPT-6-Astra | 25 | 25/25 | 276.55 seconds | 11.06 seconds | Approximately 4 minutes 37 seconds |

The final result files are [summaries_20261007_174007_180201Z.json](stage5/data/summaries/summaries_20261007_174007_180201Z.json) for Sol and [summaries_20261007_173408_673609Z.json](stage5/data/summaries/summaries_20261007_173408_673609Z.json) for Astra. Both runs used the same 25 selected source records and the same system prompt and user-template text.

An earlier Sol run stopped at request 10 with HTTP 503 after nine successful outputs. Fifteen selected records were not attempted. The later complete Sol run is used in the final comparison. The error response gave no cause, so it is no evidence of content rejection or censorship.

### Offline quality results

| Model | Checked | Marked for review | Unflagged | Additional unflagged samples |
|---|---:|---:|---:|---:|
| Sol | 25 | 2 | 23 | 5 |
| Astra | 25 | 1 | 24 | 5 |

Sol's report is [quality_20261007_175233_419718Z.json](stage5/data/quality/sol/quality_20261007_175233_419718Z.json); Astra's is [quality_20261007_175233_497896Z.json](stage5/data/quality/astra/quality_20261007_175233_497896Z.json), with matching Markdown reports.

All three automatic markings are false alarms. Sol's monetary output uses `million` where the input uses `mln`. Both models use the digit `35` where the source writes `Thirty-five`. These are equivalent representations, and no correction is required for these flagged passages. Raw check results remain unchanged; this manual decision is recorded separately here.

### Manual source-fidelity review

Manual comparison of the final outputs found two small source-fidelity deviations in Sol:

1. In record 16, the source title says that the EU fears a US diesel export ban, while the body separately describes an EC observation. The output attributes the fear specifically to the EC, narrowing the actor beyond the supplied wording.
2. In record 21, the output adds the first name `Volodymyr`, while the supplied title and text only name `Zelensky`. The issue is an addition beyond the allowed input, not a claim that the first name is incorrect.

The automatic numerical checks did not detect these two issues. In Astra's 25 outputs I found no clear content errors, and in both final cloud runs I found no clear numerical errors. These findings apply to this sample; future runs may differ.

### Limitations and conclusion

Sol was approximately 2.5 times faster by summed request time in these two runs. Request times include service and network delays, so the figure describes these two runs and is not a general speed benchmark. Astra was more faithful on the two passages identified above, in this sample.

Cloud and local systems differ in execution environment and available generation controls. The comparisons are practical observations from this project, not a controlled benchmark. Subscription availability and service errors can also affect execution.

Stage 5 delivered a working optional cloud route and documented its speed, quality observations and failure handling. The local pipeline remains the main approach.

## Shared quality criteria

For every stage that generates summaries, compare the output against the supplied original title and prepared text. Check names, numbers, units, dates, time periods, relationships between quantities, uncertainty and existing attribution. Retain the source's meaning and perspective without adding political judgments, external corrections or balancing statements.

An offline numerical match cannot establish that a number refers to the right event. Conversely, a mismatch may simply reflect equivalent notation. A concise summary may omit details; the review question is whether the omission changes the central meaning or creates a misleading impression.

RSS-summary inputs provide less context than extracted articles. A `success` label does not remove this limitation, so the text basis stays visible.

## Reproducibility and records

Keep stage-specific scripts, timestamped raw and prepared inputs, output JSON files, comparison reports and quality reports together. Preserve historical versions as development evidence, but identify the selected final input and run explicitly when reporting results.

Model names and, where available, local model digests are recorded in generation outputs. Preserve the exact prompts and generation settings with those outputs. Timings in the tables above refer to the listed runs; different records or prompt versions should not be silently merged into the same comparison.

Saved Ollama project models and exported Modelfiles can retain saved interactive Ollama conversation state. They do not automatically archive requests submitted by Python scripts or the ChatGPT conversations used during development. Code, input data, results and this documentation are separate project records.

## Next development step at the end of Stage 5

At the end of Stage 5, the planned next step was to connect collection, preparation and local summarization through a single entry point, with explicit input selection, failure handling and output paths. Scheduling and deduplication across repeated runs were still planned at that time. They were subsequently implemented in [Stage 6](stage6/README.md), together with database archival, random sampling and email delivery. Larger evaluations remain outside these small-sample tests.

