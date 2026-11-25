import { Component, onMounted, onWillDestroy, proxy } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

// Apps of the club suite come first, the native Odoo ones after them.
const CLUB_PREFIXES = ["abonnement_amarna.", "amarna_club_"];

/**
 * Home screen: every application the user may open, as a grid of icons.
 * It is the page Odoo opens at login (see ir_http.py) and the "Accueil"
 * button of the top bar and of the sidebar leads back to it.
 */
export class AmarnaHome extends Component {
    static template = "amarna_club_theme.Home";

    setup() {
        this.menuService = useService("menu");
        this.state = proxy({ query: "" });
        // the sidebar and the page margin are hidden by a class on <body>
        onMounted(() => document.body.classList.add("o_amarna_home_on"));
        onWillDestroy(() => document.body.classList.remove("o_amarna_home_on"));
    }

    isClubApp(app) {
        const xmlid = app.xmlid || "";
        return CLUB_PREFIXES.some((prefix) => xmlid.startsWith(prefix));
    }

    get apps() {
        const apps = this.menuService.getApps();
        const ordered = [
            ...apps.filter((app) => this.isClubApp(app)),
            ...apps.filter((app) => !this.isClubApp(app)),
        ];
        const query = this.state.query.trim().toLowerCase();
        return query ? ordered.filter((app) => app.name.toLowerCase().includes(query)) : ordered;
    }

    href(app) {
        return `/odoo/${app.actionPath || "action-" + app.actionID}`;
    }

    // Native icons are icon-font entries "name,color,background".
    fontIcon(app) {
        const [name, color, background] = (app.webIcon || "").split(",");
        return { name, color, background };
    }

    initial(app) {
        return (app.name || "?").trim().charAt(0).toUpperCase();
    }

    onSelect(app) {
        this.menuService.selectMenu(app);
    }

    onSearchInput(ev) {
        this.state.query = ev.target.value;
    }

    onSearchKeydown(ev) {
        if (ev.key === "Enter" && this.apps.length) {
            this.onSelect(this.apps[0]);
        }
    }
}

registry.category("actions").add("amarna_club_theme.home", AmarnaHome);
