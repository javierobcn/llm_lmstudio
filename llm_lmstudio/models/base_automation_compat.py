from odoo import fields, models
from odoo.tools import safe_eval


class BaseAutomation(models.Model):
    _inherit = "base.automation"

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

            if existing_doc:
                if collection.id not in existing_doc.collection_ids.ids:
                    existing_doc.write({"collection_ids": [(4, collection.id)]})
            else:
                if hasattr(record, "display_name") and record.display_name:
                    name = record.display_name
                elif hasattr(record, "name") and record.name:
                    name = record.name
                else:
                    name = f"{self.model_id.name} #{record.id}"

                # Do not auto-process here; this automation should only sync membership.
                self.env["llm.resource"].create(
                    {
                        "name": name,
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
