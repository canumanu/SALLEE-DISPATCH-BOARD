# Sallee Dispatch Board

An interactive, drag-and-drop dispatch board for Sallee Horse Vans. Replaces the manual 2-week Excel dispatch chart with a visual planning tool: jobs sit on a date, and drivers/teams (with truck & trailer numbers) are dragged from a top strip onto a job to assign it.

Live prototype: single self-contained `index.html`, no build step — same pattern as `barn-boards`, hosted on GitHub Pages.

## Current features

- **Rows = dates** (rolling 2-week window, Prev/Next 2 Wks and This Week nav)
- **Driver/team strip** at top — draggable blocks showing name(s) + truck/trailer number
- **Color-coded availability**: green = driver/team not yet used in the visible window, red = already on a job
- **Drag driver block onto a job** to assign it; drag the assigned badge out of one job straight into another to reassign; click the `×` to unassign
- **Job cards**: Origin / Destination, Origin & Destination Trainer-Farm, Time, Load Type (Stable Move / Special / Mix Load / Shuttle), Notes, and a type tag (normal / spare / vacation / note) with its own color accent
- **Add/edit/remove driver columns** and jobs entirely from the UI
- **Autosaves to browser localStorage** — Export/Import JSON buttons for backup and moving between machines

## Data model (in-browser only, for now)

```js
driver = { id, name1, name2, truck, trailer }
job    = { id, date, assignedDriverId, type, origin, originFarm, destination, destinationFarm, time, loadType, notes, order }
```

## Status: visual prototype only

Not yet wired to any backend — this is intentional, so the interaction model can be refined with real dispatch use before committing to a sync architecture. No live data pipeline yet (unlike `barn-boards` / `SALLEE-LOAD-BOARD`, which sync from SharePoint Excel via Power Automate / Graph API).

## Roadmap

- **Multi-user + auth**: sign-in via existing Microsoft 365 accounts (MSAL.js), two permission tiers (view-only vs. create/edit), likely via SharePoint list permissions or Azure AD groups — same approach planned for the Load Board's "Build a Load" feature.
- **Real persistence**: move off localStorage to a shared SharePoint list via Microsoft Graph (delegated permissions).
- **Turnaround-time / availability engine**: calculate whether a driver/truck is realistically available for a next job based on actual drive time from their previous drop-off to the next job's origin, using the **Samsara Routes/Address API** (Sallee has an active Samsara account). Requires:
  - Real addresses on origin/destination (extend the `TRACK_ADDRESSES`-style lookup from the Load Board to cover farms/trainers too)
  - Separate departure and estimated-arrival times per job (currently just one time field)
  - A backend script (same shape as `sync_orders.py`) to call Samsara server-side and publish a `drive_times.json` lookup — a Samsara token can't be safely exposed in a static GitHub Pages page
- **Print / simple view**: a no-login "print a load" view, in the same spirit as the Load Board's planned standalone print view.

## Notes

- NAV (Microsoft) remains the system of record for billing/BOL — this board is an operational/coordination layer only.
- Starter driver roster was seeded from the header rows of the original `DISPATCH_CHART_2026.xlsx` "Chart" tab; that source workbook is a freeform whiteboard layout (not a clean table) and was not parsed automatically for job data — jobs are entered fresh through the UI.
