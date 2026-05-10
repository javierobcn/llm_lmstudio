from odoo import api, fields, models
from odoo.tools import safe_eval


class BaseAutomation(models.Model):
    _inherit = "base.automation"

    def _get_llm_resource_name(self, record):
        self.ensure_one()
        if hasattr(record, "display_name") and record.display_name:
            return record.display_name
        if hasattr(record, "name") and record.name:
            return record.name
        return f"{self.model_id.name} #{record.id}"

    def _register_hook(self):
        result = super()._register_hook()
        automations = self.sudo().search(
            [
                ("llm_collection_id", "!=", False),
                ("trigger", "in", ["on_create", "on_write", "on_unlink"]),
            ]
        )
        automations._ensure_llm_automation_action()
        return result

    def _is_llm_knowledge_automation(self):
        self.ensure_one()
        return bool(
            self.llm_collection_id
            and self.trigger in {"on_create", "on_write", "on_unlink"}
        )

    def _get_llm_automation_action_vals(self):
        self.ensure_one()
        return {
            "name": self.name,
            "model_id": self.model_id.id,
            "state": "code",
            "code": (
                "env['base.automation'].browse(%d)._process_llm_update(records)" % self.id
            ),
        }

    def _find_llm_automation_action(self):
        self.ensure_one()
        return self.action_server_ids.filtered(
            lambda action: action.state == "code"
            and action.code
            and "._process_llm_update(records)" in action.code
        )[:1]

    def _ensure_llm_automation_action(self):
        for automation in self:
            if not automation._is_llm_knowledge_automation():
                continue

            vals = automation._get_llm_automation_action_vals()
            llm_action = automation._find_llm_automation_action()

            if llm_action:
                llm_action.write(vals)
            else:
                vals["base_automation_id"] = automation.id
                self.env["ir.actions.server"].create(vals)

            if automation.state != "code":
                automation.with_context(skip_llm_action_sync=True).write({"state": "code"})

    @api.model_create_multi
    def create(self, vals_list):
        automations = super().create(vals_list)
        if not automations.env.context.get("skip_llm_action_sync"):
            automations._ensure_llm_automation_action()
        return automations

    def write(self, vals):
        result = super().write(vals)
        if not self.env.context.get("skip_llm_action_sync"):
            self._ensure_llm_automation_action()
        return result

    def _process_llm_update(self, records):
        self.ensure_one()

        # document.page uses compute/inverse flow for content/history.
        # Skip create-time sync to avoid blanking content on first save.
        if self.trigger == "on_create" and self.model_id.model == "document.page":
            return True

        if not self.llm_collection_id:
            return False

        collection = self.llm_collection_id
        model_id = self.model_id.id

        domain = self.filter_domain or "[]"
        matched_records = records
        if self.trigger != "on_create" and domain != "[]":
            eval_context = self._get_eval_context()
            domain_result = safe_eval.safe_eval(domain, eval_context)
            matched_records = records.filtered_domain(domain_result)

        for record in matched_records:
            existing_doc = self.env["llm.resource"].search(
                [("model_id", "=", model_id), ("res_id", "=", record.id)], limit=1
            )
            resource_name = self._get_llm_resource_name(record)

            if existing_doc:
                values = {}
                if existing_doc.name != resource_name:
                    values["name"] = resource_name
                if collection.id not in existing_doc.collection_ids.ids:
                    values["collection_ids"] = [(4, collection.id)]
                if values:
                    existing_doc.write(values)
            else:
                # Do not auto-process here; this automation should only sync membership.
                self.env["llm.resource"].create(
                    {
                        "name": resource_name,
                        "model_id": model_id,
                        "res_id": record.id,
                        "collection_ids": [(4, collection.id)],
                    }
                )

        if self.trigger in ["on_write", "on_unlink"]:
            unmatched_records = records - matched_records
            for record in unmatched_records:
                resource = self.env["llm.resource"].search(
                    [("model_id", "=", model_id), ("res_id", "=", record.id)], limit=1
                )
                if resource and collection.id in resource.collection_ids.ids:
                    resource.write({"collection_ids": [(3, collection.id)]})
                    if not resource.collection_ids:
                        resource.unlink()

        return True

    def _process(self, records, domain_post=None):
        if self.state == "llm_update":
            self._ensure_llm_automation_action()
            self.invalidate_recordset(["state"])

        if self.state != "llm_update":
            return super()._process(records, domain_post=domain_post)

        action_done = self._context.get("__action_done") or {}
        records_done = action_done.get(self, records.browse())
        records -= records_done
        if not records:
            return

        if self.env.context.get("__action_feedback"):
            action_done[self] = records_done + records
        else:
            action_done = dict(action_done)
            action_done[self] = records_done + records
            self = self.with_context(__action_done=action_done)
            records = records.with_context(__action_done=action_done)

        records = records.filtered(self._check_trigger_fields)
        action_done[self] = records_done + records

        if records and "date_automation_last" in records._fields:
            records.date_automation_last = fields.Datetime.now()

        if not records:
            return

        self._process_llm_update(records)
