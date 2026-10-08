# Stage 5 — Cloud Summarization Comparison

Review date: 2026-10-07

## Outcome

Both final runs completed 25 English-language records, five per country. Each record received one or two English summary strings, and every original headline was copied unchanged. Local Ollama remains the project’s primary approach; Stage 5 is an optional cloud comparison using ChatGPT plan sign-in.

I compared every summary with its supplied title and prepared text. The final Sol run has two minor issues, described below. In the 25 Astra summaries I found no clear content errors, and in both final runs I found no clear numerical errors. These findings apply to this fixed sample; future output may differ.

## Final runs and timing

| Model | Selected | Successful | Failed | Sum of request elapsed times | Mean per record | Run wall time |
|---|---:|---:|---:|---:|---:|---:|
| GPT-5.6-Sol | 25 | 25 | 0 | 110.62 s | 4.42 s | 110.97 s |
| GPT-6-Astra | 25 | 25 | 0 | 276.55 s | 11.06 s | 276.91 s |

Astra’s summed request time was 2.50 times Sol’s in these runs. Sol therefore completed the same workload in about 40% of Astra’s request time. Each figure comes from a single sequential run and includes network and service latency, so it describes these runs and is not a general speed ranking.

Final result files:

- [Sol results](../stage5/data/summaries/summaries_20261007_174007_180201Z.json)
- [Astra results](../stage5/data/summaries/summaries_20261007_173408_673609Z.json)
- [Sol report](../stage5/data/reports/comparison_report_20261007_174007_180201Z.md)
- [Astra report](../stage5/data/reports/comparison_report_20261007_173408_673609Z.md)

## Comparison design

- Same frozen input: `../stage4/data/prepared/prepared_20261007_161827_481006.json`.
- The selected records, their order, original titles, URLs, and prepared texts are identical across the final runs.
- The saved system prompt and user prompt template are identical.
- Translation is disabled. English source titles are preserved unchanged.
- There are 15 article-based inputs and 10 RSS-summary-based inputs. IRNA and TASS use RSS summaries; the other three sources use extracted article text.
- Each model produced one final output per record. There was no prompt tuning between the two final runs.
- The review checks each summary against its title and prepared text. It does not check whether the publishers’ news claims are true.

System-prompt SHA-256:

`2ad0d1a84b7efd8886315a243c80aafa77f45a4524613fdab87e9978f21b8bdb`

## Review method

Structural checks verified 25 successful attempts per final run, unchanged titles, one or two summary strings per attempt, identical source selection and prompts, and agreement between the final Sol JSON summaries and their generated Markdown report. The Astra report was checked against its JSON in the earlier review.

All 25 outputs from each model were manually compared with the supplied original title and prepared text for meaning, attribution, certainty, names, numbers, units, chronology, and main-topic coverage. This is a descriptive review, without blind independent raters or a numerical score. A valid JSON response says nothing about source fidelity, which is why I compared each output by hand.

## Automated quality check using the unchanged Stage 3 checker

The existing `check_summaries.py` was run offline on both final cloud JSON files with `--language en --report-all`. Neither the checker nor the generated summaries were changed.

| Model | Checked | Automatically flagged | Not flagged | Additional unflagged samples |
|---|---:|---:|---:|---:|
| GPT-5.6-Sol | 25 | 2 | 23 | 5 |
| GPT-6-Astra | 25 | 1 | 24 | 5 |

All three automatic flags were manually checked against the corresponding title and prepared text:

- Sol, record 20: the checker did not match `$468 million` and `$17.55 million` with `$468 mln` and `$17.55 mln`. These are equivalent units; the title supplies the $468 mln figure and the body supplies $17.55 mln. This is a false positive.
- Sol and Astra, record 22: the checker did not match the digit `35` with the source’s spelled-out `Thirty-five`. The number of damaged private houses is correct in both outputs. These are false positives.

So the automatic flag counts are not counts of confirmed errors, in both directions: all three flags were false alarms, and the checker missed Sol’s EU-to-EC attribution shift and the added first name in record 21.

The JSON and Markdown quality files keep the checker’s original flags unchanged; my manual decisions are recorded only in this document. The checks in this folder were run on copies of the result files, so the input paths recorded in them point to the review environment.

To reproduce the checks locally, run the following commands from the repository's `stage5` directory:

```bash
python ../stage3/check_summaries.py \
  --input data/summaries/summaries_20261007_174007_180201Z.json \
  --language en --output-dir data/quality/sol --report-all

python ../stage3/check_summaries.py \
  --input data/summaries/summaries_20261007_173408_673609Z.json \
  --language en --output-dir data/quality/astra --report-all
```

## Minor issues in the final Sol run

### Record 16 — EU diesel-export concern

The headline says “EU fears US diesel export ban — Der Spiegel.” The body says the EC noted that awareness of damage to US companies might not prevent Washington from acting. Sol writes “The EC fears Washington may ban US diesel exports.”

This narrows the institution expressing concern from the EU to the European Commission without that narrower attribution being explicit in the input. This is a small attribution shift. The export ban itself is not invented: the output keeps it as an uncertain possibility. Astra preserves EU/Der Spiegel in the first sentence and EC’s observation in the second.

### Record 21 — Added first name

The supplied title and text use “Zelensky.” Sol writes “President Volodymyr Zelensky.” The first name is absent from the permitted title/text input. The first name is correct, but adding it breaks the rule against supplementing the source with outside details. The figures of 18 deaths, four children and 15 rescued match the source. Astra uses “Zelensky” without adding the first name.

## Record-by-record review

| Record | Country | Review note |
|---:|---|---|
| 1 | Germany | Sol attributes support for Israel specifically to Merz in this final run; Astra separately preserves Steinmeier’s Palestinian self-determination statement. |
| 2 | Germany | 70 contributors and the exhibition dates are preserved. |
| 3 | Germany | Four additional votes are retained; neither final summary presents CDU responsibility as established. |
| 4 | Germany | Both retain the 15-year proposal; Astra also preserves the unanimous-approval obstacle. |
| 5 | Germany | Both retain the music/control/resistance angle. Astra preserves December 2025 and January 2026 explicitly. |
| 6 | Iran | Full control and legitimate demands remain attributed to the IRGC advisor. |
| 7 | Iran | Both retain Baqaei as the speaker. Sol’s “what he called” is consistent with that existing attribution. |
| 8 | Iran | Strategic cooperation and the Wednesday phone call are preserved. |
| 9 | Iran | October 8 and both summits are preserved. |
| 10 | Iran | Full-scale war, continued talks, and defending rights from a position of strength are preserved. |
| 11 | China | Both anchor the photography comparison to 1896 rather than claiming unchanged buildings for 3,000 years. |
| 12 | China | Sol’s 6.4%, HK$272.9 billion, 116 listings and over HK$388 billion match the input. Astra emphasizes the cooperation angle. |
| 13 | China | September 30 and nine flower baskets are preserved. |
| 14 | China | The 77th anniversary and national rejuvenation statement are preserved. |
| 15 | China | Six films, Paris, and panel discussions are preserved. |
| 16 | Russia | Minor source-fidelity issue in Sol: headline EU concern becomes EC concern; Astra keeps the distinction and Der Spiegel attribution. |
| 17 | Russia | The Indian branch and bank press-service attribution are preserved. |
| 18 | Russia | Tokayev’s praise remains attributed to Tokayev. |
| 19 | Russia | Both preserve Saldo as the speaker. |
| 20 | Russia | Both retain nearly $468 million for 2027–2029 and $17.55 million next year. Sol’s mln-to-million conversion is equivalent. |
| 21 | Ukraine | Minor prompt-compliance issue in Sol: the first name Volodymyr is absent from the title and prepared text. Casualty numbers match. |
| 22 | Ukraine | Both retain two deaths, 41 injuries, 35 damaged private houses and six other destroyed houses. Astra retains the earlier 34 injuries, 17:00 and 431 apartments. |
| 23 | Ukraine | Both retain the final two injuries. Sol also includes two deaths in the separately named Darnytskyi district and compresses the fire descriptions. |
| 24 | Ukraine | Both retain the COREPER stage, clusters 2 and 3, and committee approval rather than claiming completed EU admission. |
| 25 | Ukraine | Both retain possible/suspected plague and Russia’s denial; neither turns the possible outbreak into a confirmed one. |

## Earlier interrupted Sol run

An earlier 25-record selection (`summaries_20261007_173234_262887Z.json`) stopped after nine successful requests and an HTTP 503 on request ten. Fifteen selected records were not attempted. Its nine accepted outputs were preserved. The exact service cause was not available in the saved diagnostic (`unknown_error`, no request ID).

That incomplete run is excluded from the final timing table and final 25-record quality comparison. The later complete Sol run is the benchmark used here. The HTTP failure is a service availability problem. It says nothing about content quality, and it is no evidence that an Iranian source was rejected because of its content.

## Limits and project decision

Both models received the same prompt and input, which allows a direct comparison. Each model was run only once, and the generation settings do not control all model behavior. Subscription inference uses model defaults and omits the local temperature/seed controls, so a later comparison with Ollama is not a fully controlled model-only experiment.

The sample is small, feed-selected and unequal in text length and source type. Short RSS summaries allow fewer compression decisions than full articles. English editions may select different stories from the publishers’ original-language editions. This is not a full archive of all news published by each source.

Astra was more precise on the two identified issues in this sample, while Sol was approximately 2.5 times faster. Both complete cloud runs and their source texts should be retained for reproducibility. No third cloud model or additional prompt revision is needed to document Stage 5. The local pipeline remains primary, with cloud inference presented as an alternative.
