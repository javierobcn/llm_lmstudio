{
    "name": "LM Studio LLM Integration",
    "summary": "LM Studio provider integration for LLM module",
    "description": """
        Implements LM Studio provider service for the LLM integration module.
        Uses OpenAI-compatible endpoints exposed by LM Studio.
    """,
    "author": "Apexive Solutions LLC",
    "website": "https://github.com/apexive/odoo-llm",
    "category": "Technical",
    "version": "18.0.1.0.0",
    "depends": ["llm_openai", "llm_tool", "llm_thread"],
    "data": [
        "data/llm_publisher.xml",
    ],
    "license": "LGPL-3",
    "installable": True,
}
