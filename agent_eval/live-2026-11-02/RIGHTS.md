# Rights and provenance of the live evaluation results

The three `<provider>_results.json` files are the complete outputs of `python agent_eval/run_eval.py` for the live runs
of 2026-11-02 (agent code at commit `983494e`; `5c7d171` in the private repository). Each file's `summary` and
`generated_at` equal those of the committed `<provider>_summary.json`, and the per-case token and latency sums
reproduce the README table. SHA-256 sums: [SHA256SUMS](SHA256SUMS).

Content: case results, tool-call arguments chosen by the models, code-generated reports (`verified_summary` is written
by the project's code, not by a model) and token counts. No model-authored free text, API keys, request ids, local
paths or host names (scanned 2026-11-03).

Provider terms on outputs (read in the original on 2026-11-03):

| Provider | Terms | Clause |
| --- | --- | --- |
| Meta (Muse Spark 1.3, Model API) | Meta Model API Terms of Service, last revised 2026-10-02 (dev.meta.ai/legal/terms-of-service) | 4.1: the user owns all rights, title and interest in inputs and outputs ("Content"); Meta claims no ownership of the Content |
| OpenAI (gpt-6.1-terra, API) | OpenAI Services Agreement, effective 2026-01-01 (openai.com/policies/services-agreement; read via the Internet Archive copy of 2026-10-08 because the live page refused automated access) | 4.1: as between Customer and OpenAI, Customer owns all Output; OpenAI assigns its right, title and interest, if any, in Output |
| Anthropic (claude-sonnet-5-5, API) | Anthropic Commercial Terms of Service, effective 2025-06-17 (anthropic.com/legal/commercial-terms) | B: Customer retains all rights to its Inputs and owns its Outputs |

These clauses concern ownership between the user and the provider; they are not a statement that the outputs are
copyrightable. The project's own data in these files is licensed under CC BY 4.0 like the other documentation and data
of this repository (LICENSE-docs.md).
