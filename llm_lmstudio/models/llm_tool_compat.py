import ast
import inspect
import json
from typing import Any, Optional, Union, get_origin, get_type_hints

from odoo import models


DomainScalar = Union[str, int, bool, float, None]
DomainValue = Union[DomainScalar, list[DomainScalar]]


class LLMTool(models.Model):
    _inherit = "llm.tool"

    def _get_available_implementations(self):
        implementations = super()._get_available_implementations()
        return implementations + [("odoo_record_aggregator", "Odoo Record Aggregator")]

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

    def odoo_record_retriever_execute(
        self,
        model: str,
        domain: list[list[DomainValue]] = [],  # noqa: B006
        fields: list[str] = [],  # noqa: B006
        limit: int = 100,
    ) -> dict[str, Any]:
        """Allow domain values such as ['field', 'in', ['a', 'b']] in schema."""
        return super().odoo_record_retriever_execute(
            model=model,
            domain=domain,
            fields=fields,
            limit=limit,
        )

    def odoo_record_updater_execute(
        self,
        model: str,
        domain: list[list[DomainValue]],
        values: dict[str, Any],
        limit: int = 1,
    ) -> dict[str, Any]:
        """Allow list-valued domain operands in updater schema."""
        return super().odoo_record_updater_execute(
            model=model,
            domain=domain,
            values=values,
            limit=limit,
        )

    def odoo_record_unlinker_execute(
        self,
        model: str,
        domain: list[list[DomainValue]],
        limit: int = 1,
    ) -> dict[str, Any]:
        """Allow list-valued domain operands in unlinker schema."""
        return super().odoo_record_unlinker_execute(
            model=model,
            domain=domain,
            limit=limit,
        )

    def odoo_model_inspector_execute(
        self,
        model: str,
        include_fields: bool = True,
        include_methods: bool = False,
        field_limit: int = 20,
        method_limit: int = 10,
        include_private: bool = False,
        method_name_filter: Optional[str] = None,
        method_type_filter: Optional[list[str]] = None,
        field_name_filter: Optional[str] = None,
        field_type_filter: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Keep safer inspector defaults while reusing apexive implementation."""
        return super().odoo_model_inspector_execute(
            model=model,
            include_fields=include_fields,
            include_methods=include_methods,
            field_limit=field_limit,
            method_limit=method_limit,
            include_private=include_private,
            method_name_filter=method_name_filter,
            method_type_filter=method_type_filter,
            field_name_filter=field_name_filter,
            field_type_filter=field_type_filter,
        )

    def odoo_record_aggregator_execute(
        self,
        model: str,
        domain: list[list[DomainValue]] = [],  # noqa: B006
        aggregates: list[str] = [],  # noqa: B006
        groupby: list[str] = [],  # noqa: B006
        limit: int = 100,
        orderby: Optional[str] = None,
        lazy: bool = True,
    ) -> dict[str, Any]:
        """Run grouped aggregations through ORM read_group (sum/avg/min/max/count)."""
        if model not in self.env:
            return {"error": f"Model '{model}' not found in Odoo environment"}

        if not aggregates:
            return {
                "error": "Parameter 'aggregates' is required and must contain at least one aggregation expression"
            }

        model_obj = self.env[model]
        normalized_domain = list(domain) if isinstance(domain, tuple) else (domain or [])
        normalized_groupby = list(groupby) if isinstance(groupby, tuple) else (groupby or [])

        result = model_obj.read_group(
            domain=normalized_domain,
            fields=aggregates,
            groupby=normalized_groupby,
            limit=limit,
            orderby=orderby or False,
            lazy=lazy,
        )

        return {
            "model": model,
            "domain": normalized_domain,
            "aggregates": aggregates,
            "groupby": normalized_groupby,
            "rows": json.loads(json.dumps(result, default=str)),
            "row_count": len(result),
        }
