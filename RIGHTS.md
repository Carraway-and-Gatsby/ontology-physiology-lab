# Third-party rights decisions

The history rewrite preserves paths and provenance. Ledger SHA-256 values refer to the original bytes, before either privacy or rights filtering. Each version below is a distinct original blob at that path. Retrieval dates and sources come from retained ledgers or the audit citation.

Whole-file captures without redistribution permission are replaced by UTF-8 stubs (JSON objects for JSON paths). The selected publisher abstracts are replaced with `[abstract omitted: publisher copyright; see DOI/PMID]`. The OPB test fixture retains only identifier/label XML and its provenance.

The two Smith 2004 CellML encodings are retained unchanged under the integrator’s PMR CC BY 3.0 decision, including their embedded abstract. Attribution is in [NOTICE.md](NOTICE.md). This is an explicit exception to the abstract phrase scan; copies in other files are still redacted.

Short bounded quotations in otherwise retained ledgers remain as audited. Re-fetching evidence or re-running retrieval/quotation scripts can restore excluded material: run this filter before publication.

## `docs/c_sources.json`

- Class: REMOVE; action: REDACT_QUOTES; original version count: 1.

- Licence: Smith 2004 (Elsevier) abstract at line 317 and Burkhoff & Tyberg 1993 abstract at line 425 are verbatim publisher text; other quotes are short or from CC BY/Apache/MIT sources

| Original SHA-256 | Bytes | Source | Retrieved |
| --- | ---: | --- | --- |
| `29488044198043e6015e34f7dcc0b1f52334148d13c8336545fadf8d97beefe2` | 35749 | https://pubmed.ncbi.nlm.nih.gov/15036180; https://pubmed.ncbi.nlm.nih.gov/8238596 | 2026-10-30 |

## `docs/evidence/a_smith_2004.cellml`

- Class: UNSURE; action: KEEP; original version count: 1.

- Licence: CC BY 3.0 (PMR whole model; binding integrator decision)

| Original SHA-256 | Bytes | Source | Retrieved |
| --- | ---: | --- | --- |
| `92d98dcc028e307b06d7931465951f0025f085663859cd126334dca40a260715` | 130247 | https://models.physiomeproject.org/workspace/267/rawfile/6ae217019bf59fc1e22e2dc5235751c6fcf6be24/Smith_2004.cellml | 2026-10-30 |

## `docs/evidence/a_smith_2004_canonical.cellml`

- Class: UNSURE; action: KEEP; original version count: 1.

- Licence: CC BY 3.0 (PMR whole model; binding integrator decision)

| Original SHA-256 | Bytes | Source | Retrieved |
| --- | ---: | --- | --- |
| `8cca17e89404daeef858fb3db67a16ce4200b7c2712ae6c1ccac83c68f813e60` | 75074 | https://models.physiomeproject.org/workspace/smith_chase_nokes_shaw_wake_2004/rawfile/f7b732c9707abdba5a55d471c49baf7dee92b036/smith_chase_nokes_shaw_wake_2004.cellml | 2026-10-31T14:02:27Z |

## `docs/evidence/a_smith_overview.html`

- Class: UNSURE; action: STUB; original version count: 1.

- Licence: PMR site content is CC BY 3.0 but page embeds the Elsevier abstract (line 151) and site chrome (c) IUPS Physiome Project (line 290)

| Original SHA-256 | Bytes | Source | Retrieved |
| --- | ---: | --- | --- |
| `b158602c3ce99cfc0c19dc1a4125ad0f10a74c6634e826f540db72f31cc77649` | 17882 | https://models.physiomeproject.org/exposure/9d046663ba5cac5c8a61ac146183614b/view | 2026-10-30 |

## `docs/evidence/b_cellml.json`

- Class: UNSURE; action: STUB; original version count: 1.

- Licence: Unknown: cellml.org page footer says only '(c) The CellML Project'; no licence text captured

| Original SHA-256 | Bytes | Source | Retrieved |
| --- | ---: | --- | --- |
| `3a717b84495b7ee1c25f0bdcc285084a52f01e53e33c298d285df68f2151324b` | 18336 | https://www.cellml.org/specifications/metadata | 2026-10-30T14:48:35.484983+00:00 |

## `docs/evidence/b_opb_excerpt.json`

- Class: UNSURE; action: SLIM_TO_ID_AND_LABEL; original version count: 1.

- Licence: Unknown: OPB GitHub repo has no LICENSE (d_sources.json:86, d_opb_master... note); the bundled copy sits inside SemGen's non-commercial licence

| Original SHA-256 | Bytes | Source | Retrieved |
| --- | ---: | --- | --- |
| `debdf632b2b1165cdd37e4f993ca01d98e33959fb477b3782a28d8814e5f7187` | 28546 | https://raw.githubusercontent.com/SemBioProcess/SemGen/master/src/semsim/owl/OPBv1.07.owl | 2026-10-30T14:44:52.533378+00:00 |

## `docs/evidence/c_carraway_web.txt`

- Class: REMOVE; action: STUB; original version count: 1.

- Licence: No licence for the page chrome ((c) 2026 GitHub, Inc., plain:493); repository content is MIT but is already retained cleanly as c_carraway_readme_main.txt

| Original SHA-256 | Bytes | Source | Retrieved |
| --- | ---: | --- | --- |
| `e2568d3fc37cfd7597039489dd3c1d28dd731eade1495cc04527e1ca13ee92f9` | 300671 | https://github.com/Carraway-and-Gatsby/cardiac-simulator | 2026-10-30T14:44:22.346281+00:00 |

## `docs/evidence/c_carraway_web_plain.txt`

- Class: REMOVE; action: STUB; original version count: 1.

- Licence: No licence for the page chrome ((c) 2026 GitHub, Inc., plain:493); repository content is MIT but is already retained cleanly as c_carraway_readme_main.txt

| Original SHA-256 | Bytes | Source | Retrieved |
| --- | ---: | --- | --- |
| `92fa724031390de216281c151ed10ad127a12f352357ca4592e5d15831d0a8cf` | 68361 | https://github.com/Carraway-and-Gatsby/cardiac-simulator | 2026-10-30T14:44:22.346281+00:00 |

## `docs/evidence/c_cellml_environments.txt`

- Class: UNSURE; action: STUB; original version count: 1.

- Licence: Unknown: only '(c) 2001-2026 The CellML Project' in the capture (spec_plain:2064, environments_plain:145); no CC statement captured

| Original SHA-256 | Bytes | Source | Retrieved |
| --- | ---: | --- | --- |
| `be6459ba3dd7483a213b9f58d2381789597891299362f6ab21faf0f13f101963` | 27667 | https://www.cellml.org/tools/modeling-environments | 2026-10-30T14:44:22.316967+00:00 |

## `docs/evidence/c_cellml_environments_plain.txt`

- Class: UNSURE; action: STUB; original version count: 1.

- Licence: Unknown: only '(c) 2001-2026 The CellML Project' in the capture (spec_plain:2064, environments_plain:145); no CC statement captured

| Original SHA-256 | Bytes | Source | Retrieved |
| --- | ---: | --- | --- |
| `8ba6d157eb7c05ac044aac17b879184540910daad776c269ba7988543bf3d00a` | 6688 | https://www.cellml.org/tools/modeling-environments | 2026-10-30T14:44:22.316967+00:00 |

## `docs/evidence/c_cellml_spec.txt`

- Class: UNSURE; action: STUB; original version count: 1.

- Licence: Unknown: only '(c) 2001-2026 The CellML Project' in the capture (spec_plain:2064, environments_plain:145); no CC statement captured

| Original SHA-256 | Bytes | Source | Retrieved |
| --- | ---: | --- | --- |
| `2ec74917458e2e33ad90f18e375c93f1c1907f5dcf0335f7ce1e8c33a35ba1f2` | 155580 | https://www.cellml.org/cellml/2.0 | 2026-10-30T14:44:58.518478+00:00 |

## `docs/evidence/c_cellml_spec_plain.txt`

- Class: UNSURE; action: STUB; original version count: 1.

- Licence: Unknown: only '(c) 2001-2026 The CellML Project' in the capture (spec_plain:2064, environments_plain:145); no CC statement captured

| Original SHA-256 | Bytes | Source | Retrieved |
| --- | ---: | --- | --- |
| `29fe3f7524382ff9201fc18ecb422c47a941491cad2b08b48ecab8bbdfbbb42f` | 42793 | https://www.cellml.org/cellml/2.0 | 2026-10-30T14:44:58.518478+00:00 |

## `docs/evidence/c_circadapt_license.txt`

- Class: REMOVE; action: STUB; original version count: 1.

- Licence: Proprietary (EULA) / all rights reserved

| Original SHA-256 | Bytes | Source | Retrieved |
| --- | ---: | --- | --- |
| `490bf146d47d0158d5e86f63da8d00f4dbca48e79d36261a5b31cd32a9788f74` | 18932 | https://framework.circadapt.org/latest/license.html | 2026-10-30T14:44:22.327109+00:00 |

## `docs/evidence/c_circadapt_license_plain.txt`

- Class: REMOVE; action: STUB; original version count: 1.

- Licence: Proprietary (EULA) / all rights reserved

| Original SHA-256 | Bytes | Source | Retrieved |
| --- | ---: | --- | --- |
| `1f55b4fa00744aff495d9d30fa2ea8b7732ab310f169350301051ec727efa7ec` | 11117 | https://framework.circadapt.org/latest/license.html | 2026-10-30T14:44:22.327109+00:00 |

## `docs/evidence/c_circadapt_verification.txt`

- Class: REMOVE; action: STUB; original version count: 1.

- Licence: Proprietary (EULA) / all rights reserved

| Original SHA-256 | Bytes | Source | Retrieved |
| --- | ---: | --- | --- |
| `eb10f86057a899e28fc1d6a74e8e544aa087a37fc008adc1158cca855341e107` | 9210 | https://framework.circadapt.org/latest/userguide/verification/index.html | 2026-10-30T14:45:44.718268+00:00 |

## `docs/evidence/c_circadapt_verification_plain.txt`

- Class: REMOVE; action: STUB; original version count: 1.

- Licence: Proprietary (EULA) / all rights reserved

| Original SHA-256 | Bytes | Source | Retrieved |
| --- | ---: | --- | --- |
| `cfcc7e1421eac7c82c10527c7bd9d136cc078762e3e875f7a9e07cedb3d92a20` | 959 | https://framework.circadapt.org/latest/userguide/verification/index.html | 2026-10-30T14:45:44.718268+00:00 |

## `docs/evidence/c_contractility_pubmed.txt`

- Class: REMOVE; action: STUB; original version count: 1.

- Licence: Publisher copyright (abstract); PubMed record is NLM metadata but abstracts are publisher-owned

| Original SHA-256 | Bytes | Source | Retrieved |
| --- | ---: | --- | --- |
| `de2e88f1747e54a72c1433ced2d587d991c3eaf658ba7818dd8ee8c4ebe8dbe0` | 135685 | https://pubmed.ncbi.nlm.nih.gov/8238596/ | 2026-10-30T14:45:44.873733+00:00 |

## `docs/evidence/c_contractility_pubmed_plain.txt`

- Class: REMOVE; action: STUB; original version count: 1.

- Licence: Publisher copyright (abstract); PubMed record is NLM metadata but abstracts are publisher-owned

| Original SHA-256 | Bytes | Source | Retrieved |
| --- | ---: | --- | --- |
| `4056c40ef4cad18344a4042247fb06327c0097fdffeda883b06ecc765174bf2d` | 12102 | https://pubmed.ncbi.nlm.nih.gov/8238596/ | 2026-10-30T14:45:44.873733+00:00 |

## `docs/evidence/c_quotes.json`

- Class: REMOVE; action: REDACT_QUOTES; original version count: 1.

- Licence: Same as docs/c_sources.json (Smith abstract line 200, Burkhoff abstract line 265)

| Original SHA-256 | Bytes | Source | Retrieved |
| --- | ---: | --- | --- |
| `40ff89f0be68a27289c5ec1c4f540703812f9ee63739375d8c2863629be8f777` | 24597 | https://pubmed.ncbi.nlm.nih.gov/15036180; https://pubmed.ncbi.nlm.nih.gov/8238596 | 2026-10-30 |

## `docs/evidence/c_semgen_protocol.txt`

- Class: UNSURE; action: STUB; original version count: 1.

- Licence: SemGen custom licence: non-commercial use only, redistribution 'must include this entire notice' (c_semgen_readme.txt:226); JxBrowser clause needs TeamDev licence for commercial use

| Original SHA-256 | Bytes | Source | Retrieved |
| --- | ---: | --- | --- |
| `8116ed78503235178b0323fb98bb062d91d571ff6329c674fe51b8727d0f967c` | 10658 | https://raw.githubusercontent.com/wiki/SemBioProcess/SemGen/Annotation-protocol.md | 2026-10-30T14:44:57.122709+00:00 |

## `docs/evidence/c_semgen_readme.txt`

- Class: UNSURE; action: STUB; original version count: 1.

- Licence: SemGen custom licence: non-commercial use only, redistribution 'must include this entire notice' (c_semgen_readme.txt:226); JxBrowser clause needs TeamDev licence for commercial use

| Original SHA-256 | Bytes | Source | Retrieved |
| --- | ---: | --- | --- |
| `5d18a266a4e24e5d1b7a342c961971bc3c67594934e7e011fcf71181d2067503` | 16603 | https://raw.githubusercontent.com/SemBioProcess/SemGen/master/README.md | 2026-10-30T14:44:21.631385+00:00 |

## `docs/evidence/c_smith_pubmed.txt`

- Class: REMOVE; action: STUB; original version count: 1.

- Licence: Publisher copyright (abstract); PubMed record is NLM metadata but abstracts are publisher-owned

| Original SHA-256 | Bytes | Source | Retrieved |
| --- | ---: | --- | --- |
| `d0580e3c2ad28d5bad5e4ed6f17abeb055d4a580f14fc4e6cc1d12228a321ce7` | 127423 | https://pubmed.ncbi.nlm.nih.gov/15036180/ | 2026-10-30T14:44:57.967989+00:00 |

## `docs/evidence/c_smith_pubmed_plain.txt`

- Class: REMOVE; action: STUB; original version count: 1.

- Licence: Publisher copyright (abstract); PubMed record is NLM metadata but abstracts are publisher-owned

| Original SHA-256 | Bytes | Source | Retrieved |
| --- | ---: | --- | --- |
| `f48754228d5efc203c4bc62141398917127e721403d24cde68a6384486fe58f6` | 11505 | https://pubmed.ncbi.nlm.nih.gov/15036180/ | 2026-10-30T14:44:57.967989+00:00 |
