from odoo import SUPERUSER_ID, api


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    automations = env["base.automation"].search(
        [
            ("llm_collection_id", "!=", False),
            ("trigger", "in", ["on_create", "on_write", "on_unlink"]),
        ]
    )
    automations._ensure_llm_automation_action()
