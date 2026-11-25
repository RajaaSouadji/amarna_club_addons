import { patch } from "@web/core/utils/patch";
import { SIZES } from "@web/core/ui/ui_utils";
import { FormController } from "@web/views/form/form_controller";
import { FormRenderer } from "@web/views/form/form_renderer";

// Odoo puts the chatter beside the form (and lays the form out in a row) on
// very wide screens, from the XXL breakpoint. In this club the forms are short
// and the history is long, so the chatter always goes below the form: the form
// controller and renderer are simply told that the screen is never wider than XL.
function capSize(ui) {
    return new Proxy(ui, {
        get(target, prop) {
            if (prop === "size") {
                return Math.min(target.size, SIZES.XL);
            }
            const value = Reflect.get(target, prop, target);
            return typeof value === "function" ? value.bind(target) : value;
        },
    });
}

patch(FormRenderer.prototype, {
    setup() {
        super.setup();
        if (this.uiService) {
            this.uiService = capSize(this.uiService);
        }
    },
});

patch(FormController.prototype, {
    setup() {
        super.setup();
        if (this.ui) {
            this.ui = capSize(this.ui);
        }
    },
});
