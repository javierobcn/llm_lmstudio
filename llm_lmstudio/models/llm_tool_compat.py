import ast
import inspect
import json
from typing import get_origin, get_type_hints

from odoo import models


class LLMTool(models.Model):
    _inherit = "llm.tool"

    def _parse_structured_string(self, value):
        """Parse stringified list/dict payloads sent by some clients."""
        if not isinstance(value, str):
            return value

        text = value.strip()
        if not text or text[0] not in "[{(":
            return value

        try:
            return json.loads(text)
        except (TypeError, ValueError):
            try:
                return ast.literal_eval(text)
            except (ValueError, SyntaxError):
                return value

    def execute(self, parameters):
        """Coerce structured strings before pydantic validation in base execute()."""
        self.ensure_one()

        method = self._get_implementation_method()
        type_hints = get_type_hints(method)
        signature = inspect.signature(method)
        normalized = dict(parameters or {})

        for param_name, param in signature.parameters.items():
            if param_name == "self" or param_name not in normalized:
                continue
            value = normalized[param_name]
            if not isinstance(value, str):
                continue

            expected = type_hints.get(param_name)
            origin = get_origin(expected)
            parsed = self._parse_structured_string(value)

            if param_name == "domain" and parsed is not value:
                normalized[param_name] = list(parsed) if isinstance(parsed, tuple) else parsed
                continue

            if origin in (list, tuple) and parsed is not value:
                normalized[param_name] = list(parsed) if isinstance(parsed, tuple) else parsed
                continue

            if origin is dict and isinstance(parsed, dict):
                normalized[param_name] = parsed
                continue

            if param.default == [] and parsed is not value:
                normalized[param_name] = list(parsed) if isinstance(parsed, tuple) else parsed

        return super().execute(normalized)
