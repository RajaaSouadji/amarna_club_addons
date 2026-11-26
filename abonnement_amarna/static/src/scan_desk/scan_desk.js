import { Component, onMounted, proxy } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const LABELS = {
    success: "Accès autorisé",
    duplicate: "Déjà enregistré",
    denied: "Accès refusé",
    choose: "Choisissez l'abonnement",
};

/**
 * Reader desk: the card reader types the card number and presses Enter, the
 * screen checks the card, records the passage and shows the verdict at once.
 * No second click: one read = one passage (a second read within a few minutes is
 * reported as "déjà enregistré" and takes nothing, see amarna.checkin.scan_card).
 */
export class ScanDesk extends Component {
    static template = "abonnement_amarna.ScanDesk";

    setup() {
        this.orm = useService("orm");
        this.state = proxy({ code: "", busy: false, result: null, history: [] });
        onMounted(() => this.focusInput());
    }

    focusInput() {
        const input = document.querySelector(".o_amarna_scan_input");
        if (input) {
            input.focus();
            input.select();
        }
    }

    get verdictLabel() {
        return LABELS[this.state.result?.status] || "";
    }

    onInput(ev) {
        this.state.code = ev.target.value;
    }

    onKeydown(ev) {
        if (ev.key === "Enter") {
            ev.preventDefault();
            this.scan();
        }
    }

    async scan(subscriptionId) {
        const code = (this.state.code || "").trim();
        if (this.state.busy || !code) {
            return;
        }
        this.state.busy = true;
        try {
            const result = await this.orm.call("amarna.checkin", "scan_card", [code], {
                subscription_id: subscriptionId || null,
            });
            this.state.result = result;
            if (result.status !== "choose") {
                this.state.history = [
                    {
                        key: Date.now(),
                        time: new Date().toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" }),
                        who: result.member?.name || result.card || code,
                        status: result.status,
                        message: result.message,
                    },
                    ...this.state.history,
                ].slice(0, 8);
                this.state.code = "";
            }
        } finally {
            this.state.busy = false;
            // ready for the next card, whatever happened
            setTimeout(() => this.focusInput(), 0);
        }
    }

    choose(choice) {
        this.scan(choice.id);
    }

    photo(member) {
        return `/web/image/res.partner/${member.id}/avatar_128`;
    }
}

registry.category("actions").add("abonnement_amarna.scan_desk", ScanDesk);
