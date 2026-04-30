import emoji
import markdown2
from markupsafe import Markup

from odoo import models


class LLMThread(models.Model):
    _inherit = "llm.thread"

    def _process_llm_body(self, body):
        """Render aliases as emoji before markdown conversion."""
        if not body or isinstance(body, Markup):
            return body
        return markdown2.markdown(emoji.emojize(body, language="alias"))
