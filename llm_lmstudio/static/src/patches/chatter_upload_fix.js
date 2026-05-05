/** @odoo-module **/

import { Chatter } from "@mail/chatter/web_portal/chatter";
import { patch } from "@web/core/utils/patch";

patch(Chatter.prototype, {
    onUploaded(data, { thread } = {}) {
        const effectiveThread = thread || this.state?.thread || this.attachmentUploader?.thread;
        if (!effectiveThread) {
            return async () => {};
        }
        const uploadHandler = super.onUploaded(undefined, { thread: effectiveThread });
        const hasPayload =
            data && typeof data === "object" && (Object.hasOwn(data, "data") || Object.hasOwn(data, "name"));
        if (hasPayload) {
            return uploadHandler(data);
        }
        return uploadHandler;
    },
});
