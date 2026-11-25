import { registry } from "@web/core/registry";

// The "partner autocomplete" module of Odoo (installed automatically with the mail
// plug-ins) suggests companies from an online directory while the user types a name
// or a contact, and sends what is typed to Odoo's servers. A club only registers its
// own members, so the two widgets it installs are turned back into the plain ones:
// no dropdown, nothing leaves the server.
const PLAIN = {
    field_partner_autocomplete: "char",
    res_partner_many2one: "many2one",
};

const fields = registry.category("fields");

function usePlainWidgets() {
    for (const [key, plainKey] of Object.entries(PLAIN)) {
        if (fields.contains(key) && fields.contains(plainKey) && fields.get(key) !== fields.get(plainKey)) {
            fields.add(key, fields.get(plainKey), { force: true });
        }
    }
}

// the module may be loaded before or after this file
usePlainWidgets();
fields.addEventListener("UPDATE", ({ detail }) => {
    if (detail.operation === "add" && detail.key in PLAIN) {
        usePlainWidgets();
    }
});
