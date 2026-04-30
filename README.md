# llm_lmstudio

LM Studio provider integration for the [odoo-llm](https://github.com/apexive/odoo-llm) module.

## Description

Implements the LM Studio provider service for the Odoo LLM integration module.
Uses OpenAI-compatible endpoints exposed by LM Studio.

## Dependencies

- `llm_openai` (from [apexive/odoo-llm](https://github.com/apexive/odoo-llm))

## Configuration

1. Install the module
2. Go to LLM > Configuration > Providers
3. Create a new provider with service **LM Studio**
4. Set the **API Base URL** to your LM Studio server (e.g. `http://localhost:1234/v1`)

## License

LGPL-3
