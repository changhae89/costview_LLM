# PRD Evaluation Rubric

## Summary checks

- Must be exactly 3 Korean sentences.
- Must read as complete sentences, not fragments.
- Must not contain markdown, bullets, or JSON.

## Causal checks

- `effects` should be empty when the news has no clear household-cost link.
- `reliability` should be low for weakly related political or diplomatic news.
- `event` and `mechanism` should be concise and factual.
- `related_indicators` should only include `usd_krw`, `wti`, `gold`, `base_rate`.

## Regression note

- Use `sample_news_politics.json` to verify that unrelated political news does not create false consumer-impact effects.
