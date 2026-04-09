"""List Gemini models that support generateContent for local debugging."""

from __future__ import annotations

from prd.config import get_gemini_api_key, load_environment

load_environment()

import google.generativeai as genai  # noqa: E402


def main() -> None:
    """Print available Gemini model ids."""
    api_key = get_gemini_api_key()
    if not api_key:
        raise SystemExit(
            "GEMINI_API_KEY (or GOOGLE_API_KEY) is missing. Set it in the repo root .env or prd/.env."
        )

    genai.configure(api_key=api_key)
    for model in genai.list_models():
        if "generateContent" in model.supported_generation_methods:
            print(model.name)


if __name__ == "__main__":
    main()

