# Validation plan (backtest)

This folder holds the **news analysis backtest / validation** specification and supporting artifacts. It is separate from runtime code under `prd/`.

| File | Purpose |
|------|---------|
| [검증_기획서.md](./검증_기획서.md) | Korean entry / pointer to the files below |
| [VALIDATION_PLAN.md](./VALIDATION_PLAN.md) | Full planning document (purpose, rules, process, risks) |
| [queries.sql](./queries.sql) | Reference SQL for sampling and backtest windows |
| [category_indicator_mapping.md](./category_indicator_mapping.md) | Template: `cost_categories` / chain category → indicator column |

Document language: English (stable in repo tooling). Scope matches agreements: calendar **M → M+1**, aggregate per **`news_analysis_id`** using **method B**, score uses **direction + magnitude + change_pct** (pct skipped if both NULL), **monthly indicators first**.

**Encoding:** All files under `validation_plan/` are **UTF-8** (no BOM). Repository default is set in the root `.editorconfig` and `.gitattributes`.
