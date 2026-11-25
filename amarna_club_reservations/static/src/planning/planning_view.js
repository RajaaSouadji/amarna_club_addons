import { registry } from "@web/core/registry";
import { calendarView } from "@web/views/calendar/calendar_view";

// The week calendar of the Planning: same view as Odoo's, plus a button next to
// the search bar that opens the waiting list (the list view has the same button).
registry.category("views").add("amarna_planning_calendar", {
    ...calendarView,
    buttonTemplate: "amarna_club_reservations.PlanningButtons",
});
