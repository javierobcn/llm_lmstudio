from openai import OpenAI

from odoo import _, api, models
from odoo.exceptions import UserError


class LLMProvider(models.Model):
    _inherit = "llm.provider"

    @api.model
    def _get_available_services(self):
        services = super()._get_available_services()
        return services + [("lmstudio", "LM Studio")]

    def _dispatch(self, method, *args, record=None, **kwargs):
        if not self.service:
            raise UserError(_("Provider service not configured"))

        if self.service == "lmstudio":
            if method == "get_client":
                service_method = "lmstudio_get_client"
            elif method == "models":
                service_method = "lmstudio_models"
            elif method == "format_messages":
                service_method = "lmstudio_format_messages"
            else:
                service_method = f"openai_{method}"
            record = record if record else self
            record_name = record._name
            if not hasattr(record, service_method):
                raise NotImplementedError(
                    _(
                        "Method '%s' (via '%s') not implemented "
                        "for service '%s' on target '%s'"
                    )
                    % (method, service_method, self.service, record_name)
                )
            return getattr(record, service_method)(*args, **kwargs)

        return super()._dispatch(method, *args, record=record, **kwargs)

    def lmstudio_get_client(self):
        self.ensure_one()
        if not self.api_base:
            raise UserError(
                _(
                    "API base URL is required for LM Studio provider. "
                    "Please set it in the provider configuration."
                )
            )
        return OpenAI(
            api_key=self.api_key or "lm-studio",
            base_url=self.api_base,
        )

    def lmstudio_models(self, model_id=None):
        """List available LM Studio models with tolerant response parsing."""
        if model_id:
            model = self.client.models.retrieve(model_id)
            yield self._lmstudio_parse_model(model)
            return

        models_response = self.client.models.list()
        models_data = getattr(models_response, "data", None)

        if models_data is None and isinstance(models_response, dict):
            models_data = models_response.get("data")

        if not models_data:
            return

        for model in models_data:
            yield self._lmstudio_parse_model(model)

    def _lmstudio_parse_model(self, model):
        """Parse LM Studio model payloads (OpenAI objects or plain dicts)."""
        if isinstance(model, dict):
            model_id = model.get("id")
            if not model_id:
                return {
                    "name": "unknown",
                    "details": {"capabilities": ["chat"]},
                }
            model_id_lower = model_id.lower()
            capabilities = ["chat"]
            if (
                "text-embedding" in model_id_lower
                or "embedding" in model_id_lower
            ):
                capabilities = ["embedding"]
            elif any(p in model_id_lower for p in self.OPENAI_VISION_PATTERNS):
                capabilities = ["chat", "multimodal"]
            return {
                "name": model_id,
                "details": {
                    "id": model_id,
                    "capabilities": capabilities,
                    **model,
                },
            }

        return self._openai_parse_model(model)

    def lmstudio_format_messages(
        self, messages, system_prompt=None, model=None
    ):
        """Format messages for LM Studio.

        Wraps openai_format_messages and ensures a user message is present.
        Some LM Studio model Jinja templates (e.g. qwen3) raise
        "No user query found in messages" if no user message is present at all,
        or when the last message has role 'tool' after tool results.
        """
        formatted = self.openai_format_messages(
            messages, system_prompt=system_prompt, model=model
        )
        if formatted and formatted[-1].get("role") == "tool":
            formatted.append(
                {
                    "role": "user",
                    "content": (
                        "Please provide the final answer based on "
                        "the tool results above."
                    ),
                }
            )
        # Guard: some templates require at least one user message in
        # the sequence.
        # Handle also the empty-sequence case.
        if not any(m.get("role") == "user" for m in formatted):
            formatted.append({"role": "user", "content": "Please respond."})
        return formatted
