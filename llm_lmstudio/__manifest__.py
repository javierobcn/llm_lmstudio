{
    "name": "LM Studio LLM Integration",
    "summary": "LM Studio provider integration for LLM module",
    "description": """
        Implements LM Studio provider service for the LLM integration module.
        Uses OpenAI-compatible endpoints exposed by LM Studio.
    """,
    "author": "Javier AG <hola@javieranto.com>",
    "website": "https://github.com/apexive/odoo-llm",
    "category": "Technical",
    "version": "18.0.1.0.0",
    "depends": [
        "llm_openai",
        "llm_tool",
        "llm_thread",
        "llm_knowledge_automation",
    ],
    "data": [
        "data/llm_publisher.xml",
        "data/llm_tool_data.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "llm_lmstudio/static/src/patches/chatter_upload_fix.js",
            "llm_lmstudio/static/src/xml/chatter_uploader_fix.xml",
        ],
    },
    "post_init_hook": "post_init_hook",
    "license": "LGPL-3",
    "installable": True,
}
