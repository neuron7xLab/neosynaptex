# Bibliography Verification (Bible-grade)

This document is the offline audit log for the MLSDM bibliography. The single source of truth lives in:
- `docs/bibliography/REFERENCES.bib` (canonical BibTeX)
- `docs/bibliography/metadata/identifiers.json` (frozen identifiers and metadata)
- `docs/bibliography/REFERENCES_APA7.md` (APA 7 render with key markers)

CI fails if any entry drifts from the frozen metadata below or if coverage is incomplete. No network calls are made during validation.

## Allowed canonical_id_type
- `doi`
- `arxiv`
- `isbn`
- `url` (official publisher or official standard URL only)

## Canonical verification table
| key | canonical_id_type | canonical_id | canonical_url | verified_on | verification_method |
|---|---|---|---|---|---|
| asha_aphasia | url | https://www.asha.org/practice-portal/clinical-topics/aphasia/ | https://www.asha.org/practice-portal/clinical-topics/aphasia/ | 2025-12-30 | publisher |
| bai2022_constitutional | arxiv | arXiv:2212.08073 | https://arxiv.org/abs/2212.08073 | 2025-12-30 | arxiv |
| bassett2017_network | doi | 10.1038/nn.4502 | https://doi.org/10.1038/nn.4502 | 2025-12-30 | crossref |
| bassett2017_smallworld | doi | 10.1177/1073858416667720 | https://doi.org/10.1177/1073858416667720 | 2025-12-30 | crossref |
| benna2016_synaptic | doi | 10.1038/nn.4401 | https://doi.org/10.1038/nn.4401 | 2025-12-30 | crossref |
| borgeaud2022_retro | arxiv | arXiv:2112.04426 | https://arxiv.org/abs/2112.04426 | 2025-12-30 | arxiv |
| brady2016_aphasia | doi | 10.1002/14651858.CD000425.pub4 | https://doi.org/10.1002/14651858.CD000425.pub4 | 2025-12-30 | crossref |
| carr2011_replay | doi | 10.1038/nn.2732 | https://doi.org/10.1038/nn.2732 | 2025-12-30 | crossref |
| davies2018_loihi | doi | 10.1109/MM.2018.112130359 | https://doi.org/10.1109/MM.2018.112130359 | 2025-12-30 | crossref |
| elkishky2022_sigstore | doi | 10.1145/3548606.3560596 | https://doi.org/10.1145/3548606.3560596 | 2025-12-30 | crossref |
| fedorenko2023_agrammatic | doi | 10.1080/02687038.2022.2143233 | https://doi.org/10.1080/02687038.2022.2143233 | 2025-12-30 | crossref |
| friederici2011_brain | doi | 10.1152/physrev.00006.2011 | https://doi.org/10.1152/physrev.00006.2011 | 2025-12-30 | crossref |
| foster2006_reverse | doi | 10.1038/nature04587 | https://doi.org/10.1038/nature04587 | 2025-12-30 | crossref |
| fusi2005_cascade | doi | 10.1016/j.neuron.2005.02.001 | https://doi.org/10.1016/j.neuron.2005.02.001 | 2025-12-30 | crossref |
| gabriel2020_alignment | doi | 10.1007/s11023-020-09539-2 | https://doi.org/10.1007/s11023-020-09539-2 | 2025-12-30 | crossref |
| hastings2018_circadian | doi | 10.1038/s41583-018-0026-z | https://doi.org/10.1038/s41583-018-0026-z | 2025-12-30 | crossref |
| hickok2007_cortical | doi | 10.1038/nrn2113 | https://doi.org/10.1038/nrn2113 | 2025-12-30 | crossref |
| hbp2024_assessment | doi | 10.2759/6494125 | https://doi.org/10.2759/6494125 | 2025-12-30 | crossref |
| hebb1949_organization | isbn | 9780471362728 | https://archive.org/details/organizationofbe00hebb | 2025-12-30 | publisher |
| hong2025_agents | doi | 10.3389/fpsyg.2025.1591618 | https://doi.org/10.3389/fpsyg.2025.1591618 | 2025-12-30 | crossref |
| hopfield1982_neural | doi | 10.1073/pnas.79.8.2554 | https://doi.org/10.1073/pnas.79.8.2554 | 2025-12-30 | crossref |
| ieee2020_7010 | doi | 10.1109/IEEESTD.2020.9084219 | https://doi.org/10.1109/IEEESTD.2020.9084219 | 2025-12-30 | crossref |
| iso2023_42001 | url | https://www.iso.org/standard/42001 | https://www.iso.org/standard/42001 | 2025-12-30 | publisher |
| jensen2024_replayplanning | doi | 10.1038/s41593-024-01675-7 | https://doi.org/10.1038/s41593-024-01675-7 | 2025-12-30 | crossref |
| ji2023_survey | arxiv | arXiv:2310.19852 | https://arxiv.org/abs/2310.19852 | 2025-12-30 | arxiv |
| karpukhin2020_dpr | arxiv | arXiv:2004.04906 | https://arxiv.org/abs/2004.04906 | 2025-12-30 | arxiv |
| lewis2020_rag | arxiv | arXiv:2005.11401 | https://arxiv.org/abs/2005.11401 | 2025-12-30 | arxiv |
| masuyama2014_qibam | doi | 10.1142/S0219843614500066 | https://doi.org/10.1142/S0219843614500066 | 2025-12-30 | crossref |
| masuyama2018_qmam | doi | 10.1109/TNNLS.2017.2653114 | https://doi.org/10.1109/TNNLS.2017.2653114 | 2025-12-30 | crossref |
| mendoza2009_clocks | doi | 10.1177/1073858408327808 | https://doi.org/10.1177/1073858408327808 | 2025-12-30 | crossref |
| nist2022_ssdf | doi | 10.6028/NIST.SP.800-218 | https://doi.org/10.6028/NIST.SP.800-218 | 2025-12-30 | crossref |
| nist2023_rmf | url | https://nvlpubs.nist.gov/nistpubs/ai/nist.ai.100-1.pdf | https://nvlpubs.nist.gov/nistpubs/ai/nist.ai.100-1.pdf | 2025-12-30 | publisher |
| olafsdottir2018_replay | doi | 10.1016/j.cub.2017.10.073 | https://doi.org/10.1016/j.cub.2017.10.073 | 2025-12-30 | crossref |
| openai2023_gpt4 | arxiv | arXiv:2303.08774 | https://arxiv.org/abs/2303.08774 | 2025-12-30 | arxiv |
| openssf2023_slsa | url | https://slsa.dev/spec/v1.0/ | https://slsa.dev/spec/v1.0/ | 2025-12-30 | publisher |
| ouyang2022_instruct | arxiv | arXiv:2203.02155 | https://arxiv.org/abs/2203.02155 | 2025-12-30 | arxiv |
| park2023_generative | doi | 10.1145/3586183.3606763 | https://doi.org/10.1145/3586183.3606763 | 2025-12-30 | crossref |
| schick2023_toolformer | arxiv | arXiv:2302.04761 | https://arxiv.org/abs/2302.04761 | 2025-12-30 | arxiv |
| torresarias2019_intoto | url | https://www.usenix.org/conference/usenixsecurity19/presentation/torres-arias | https://www.usenix.org/conference/usenixsecurity19/presentation/torres-arias | 2025-12-30 | publisher |
| touvron2023_llama | arxiv | arXiv:2302.13971 | https://arxiv.org/abs/2302.13971 | 2025-12-30 | arxiv |
| touvron2023_llama2 | arxiv | arXiv:2307.09288 | https://arxiv.org/abs/2307.09288 | 2025-12-30 | arxiv |
| tononi2014_sleep | doi | 10.1016/j.neuron.2013.12.025 | https://doi.org/10.1016/j.neuron.2013.12.025 | 2025-12-30 | crossref |
| turrigiano2012_homeostatic | doi | 10.1101/cshperspect.a005736 | https://doi.org/10.1101/cshperspect.a005736 | 2025-12-30 | crossref |
| vallverdu2025_neuroq | doi | 10.3390/biomimetics10080516 | https://doi.org/10.3390/biomimetics10080516 | 2025-12-30 | crossref |
| vaswani2017_attention | arxiv | arXiv:1706.03762 | https://arxiv.org/abs/1706.03762 | 2025-12-30 | arxiv |
| vasylenko2025_mlsdm | url | https://github.com/neuron7xLab/mlsdm-governed-cognitive-memory | https://github.com/neuron7xLab/mlsdm-governed-cognitive-memory | 2025-12-30 | publisher |
| wang2024_clllm | arxiv | arXiv:2402.01364 | https://arxiv.org/abs/2402.01364 | 2025-12-30 | arxiv |
| weidinger2023_veil | doi | 10.1073/pnas.2213709120 | https://doi.org/10.1073/pnas.2213709120 | 2025-12-30 | crossref |
| xie2013_glymphatic | doi | 10.1126/science.1241224 | https://doi.org/10.1126/science.1241224 | 2025-12-30 | crossref |
| wu2022_memorizing | arxiv | arXiv:2203.08913 | https://arxiv.org/abs/2203.08913 | 2025-12-30 | arxiv |
| yao2022_react | arxiv | arXiv:2210.03629 | https://arxiv.org/abs/2210.03629 | 2025-12-30 | arxiv |

### How to update
- Update `docs/bibliography/REFERENCES.bib` with the new entry (title, year, author, identifier).
- Add the same key to `docs/bibliography/REFERENCES_APA7.md` with a leading `<!-- key: ... -->` marker.
- Add the verified identifier and frozen metadata to `docs/bibliography/metadata/identifiers.json` and regenerate the table above.
- Run `python scripts/validate_bibliography.py` (CI runs this offline) to block duplicates, missing identifiers, or metadata drift.

## Maintenance

- **Quarterly review**: Check for DOI/URL rot (broken links)
- **Version updates**: When software version changes, update CITATION.cff and CITATION.bib
- **New releases**: Ensure date-released in CITATION.cff matches actual release date
- **Release verification**: CITATION metadata must match release (version + date in CHANGELOG.md)
- **Verification table**: Update verified_on date when re-verifying references
