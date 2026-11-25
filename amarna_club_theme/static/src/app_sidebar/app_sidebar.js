import { Component, onMounted, onPatched, onWillDestroy, proxy } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const STORAGE_KEY = "amarna_club.sidebar_collapsed";
// Apps of the club suite are listed first, the native Odoo ones go below.
const CLUB_PREFIXES = ["abonnement_amarna.", "amarna_club_"];

/**
 * Persistent left-hand app navigator: one entry per app with its icon,
 * the current app highlighted, and a collapse button (icons only).
 * It replaces the text-only dropdown of the navbar on desktop screens.
 */
export class AppSidebar extends Component {
    static template = "amarna_club_theme.AppSidebar";

    setup() {
        this.menuService = useService("menu");
        this.actionService = useService("action");
        this.ui = proxy(useService("ui"));
        this.state = proxy({ collapsed: this.readCollapsed() });
        onMounted(() => this.syncBody());
        onPatched(() => this.syncBody());
        onWillDestroy(() => this.clearBody());
    }

    readCollapsed() {
        try {
            return browser.localStorage.getItem(STORAGE_KEY) === "1";
        } catch {
            return false;
        }
    }

    toggleCollapsed() {
        this.state.collapsed = !this.state.collapsed;
        try {
            browser.localStorage.setItem(STORAGE_KEY, this.state.collapsed ? "1" : "0");
        } catch {
            // private mode: the choice just lasts for this page
        }
    }

    // The page layout (margin of the action area, hidden dropdown) is driven
    // by classes on <body>, so that nothing moves if this component fails.
    syncBody() {
        const visible = !this.ui.isSmall;
        const classes = document.body.classList;
        classes.toggle("o_amarna_sidebar_on", visible);
        classes.toggle("o_amarna_sidebar_collapsed", visible && this.state.collapsed);
    }

    clearBody() {
        document.body.classList.remove("o_amarna_sidebar_on", "o_amarna_sidebar_collapsed");
    }

    isClubApp(app) {
        const xmlid = app.xmlid || "";
        return CLUB_PREFIXES.some((prefix) => xmlid.startsWith(prefix));
    }

    get groups() {
        const apps = this.menuService.getApps();
        const club = apps.filter((app) => this.isClubApp(app));
        const others = apps.filter((app) => !this.isClubApp(app));
        return [
            { key: "club", label: "Club", apps: club },
            { key: "system", label: "Système", apps: others },
        ].filter((group) => group.apps.length);
    }

    isCurrent(app) {
        return this.menuService.getCurrentApp()?.id === app.id;
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

    goHome() {
        this.actionService.doAction("amarna_club_theme.action_amarna_home", {
            clearBreadcrumbs: true,
        });
    }
}

registry.category("main_components").add("amarna_club_theme.AppSidebar", {
    Component: AppSidebar,
});
