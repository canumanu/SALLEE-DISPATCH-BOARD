[README_6.md](https://github.com/user-attachments/files/32113704/README_6.md)
[README (3).md](https://github.com/user-attachments/files/31557920/README.3.md)
# Sallee Dispatch Board

An interactive dispatch board for Sallee Horse Vans, replacing the manual 2-week Excel dispatch chart. Drivers/trucks run as columns across the top, dates run down the left, and jobs live in the grid where they intersect — drag a job into a different driver's column and it adopts that driver automatically.

Live board: single self-contained `index.html`, no build step — same pattern as `barn-boards`, hosted on GitHub Pages.

## Current features

- **Drivers/trucks as columns**, dates as rows — the full chart, not a scrolling list.
- **Region grouping**: driver columns are grouped and color-banded by location — **KY** (left), **FL** (center), **NY** (right), with an "Unassigned" group for any driver without a location set. Set a driver's location from their edit modal; the columns re-sort automatically.
- **Drag a job into any driver's column** (any date) to reassign it — the job adopts that driver and date on drop. No separate "assign driver" drag step.
- **Synced top scrollbar**: a slim scrollbar sits just below the top bar, mirroring the main board's horizontal scroll — no need to reach the bottom of the screen to scroll across 25+ driver columns.
- **Duplicate-time protection**: dropping or saving a job onto a driver who's already booked at the exact same Load Time on the same day is blocked, with an on-page banner (not a browser `alert()`, which gets silently blocked in some embedded/preview contexts) naming the driver, time, and conflicting trip.
- **Multi-day entries**: Start Date / End Date fields on new jobs create one entry per day in one step (e.g. a vacation stretch), all pre-assigned to the chosen driver.
- **Three distinct time fields** per job, since they mean different things to a dispatcher:
  - **Leave Yard Time** — when the truck pulls out
  - **Load Time** — when pickup happens at origin
  - **Maintenance Time** — separate field, only shown for PM/Safety Inspection entries
- **Job types**: Normal, Spare/standby, Vacation/off, Note only, **PM**, **Safety Inspection** — the last two show an **Assigned Technician** field and render as a distinct colored banner at the top of the card (blue for PM, orange for Safety Inspection) instead of the usual route line, since they're maintenance events on this truck rather than a haul. Being just another job type, they're fully draggable between driver columns like any other entry.
- **Load Type**: Stable Move, Special, Mix Load, Shuttle, Race and Return, Plane.
- **Job cards**: Origin/Destination, Origin & Destination Trainer/Farm, both wrap instead of truncating so long names show in full; Notes clamp at 3 lines; smaller font sized to fit more at a glance without being unreadable.
- **Load Board link**: optional field to paste a link or order # once a dispatch job becomes a real Load Board order, plus a "Browse" button that live-fetches the Load Board's `orders.json` (same-origin under `canumanu.github.io`) and lists matches for that date instead of typing.
- **Add/edit/remove driver columns** (with location) and jobs entirely from the UI.
- **Autosaves to browser localStorage** as a fast local cache/offline fallback — Export/Import JSON buttons for backup and moving between machines (Import stays local-only; see Multi-user section below).
- **Multi-user sign-in via Microsoft 365 (MSAL.js) + SharePoint sync** — see "Status" below.

## Data model (in-browser only, for now)

```js
driver = { id, name1, name2, truck, trailer, location }   // location: 'KY' | 'FL' | 'NY' | ''
job    = { id, date, assignedDriverId, type, technician, maintTime,
           origin, originFarm, destination, destinationFarm,
           leaveYardTime, time, loadType, notes, loadBoardRef, order }
```

`type` values: `normal`, `spare`, `vacation`, `note`, `pm`, `safety_inspection`.
`loadType` values: `stable_move`, `special`, `mix_load`, `shuttle`, `race_and_return`, `plane`.

Adding a new dropdown option (Type or Load Type) needs two matching edits in `index.html`: the `<option value="x">Label</option>` line in the `<select>`, and the same key in the corresponding JS label lookup (`LOAD_TYPE_LABELS` or `MAINTENANCE_LABELS`) — otherwise the card displays the raw value instead of the label.

## Status: multi-user, backed by SharePoint

The interaction model and rules (conflict checks, turnaround logic, etc.) were proven out single-user first, per the original plan. Now wired to a shared backend:

- **Sign-in**: "Sign in with Microsoft" button (top bar) uses MSAL.js against the "Sallee Dispatch Board Sign-in" Azure AD app registration (client ID `3530a45a-659e-4d10-95fd-6f32b857e702`, tenant `428e82a0-5a1b-41e6-a24c-ca8ea70db05a`). Redirect URI is this page's own GitHub Pages URL, registered as a Single-page application (SPA) platform entry.
- **Data store**: two SharePoint lists — `DispatchDrivers` and `DispatchJobs` — on the "Sallee Dispatch Board" site (`https://salleehorsevans.sharepoint.com/sites/SALLEEDISPATCHBOARD`). The app auto-creates these lists (with the right columns) the first time anyone signs in and they don't exist yet, and seeds them from whatever's currently in the browser's local data at that moment.
- **Permission tiers**: enforced by SharePoint's own site roles, not by the app itself — a Visitor gets read-only (writes come back `403` and the app switches into a "view-only" banner state); a Member can create/edit. Manage who's a Visitor vs. Member from the SharePoint site's own permissions page.
- **Sync model**: every add/edit/delete/drag-drop pushes straight to the relevant SharePoint list item. The board also polls SharePoint every 45s (only when no modal is open) to pick up other dispatchers' changes. `localStorage` remains a local cache/fallback — if SharePoint is unreachable, the board keeps working from whatever was last synced, and retries are implicit (the next edit attempts to sync again).
- **Known limitation**: Import JSON stays local-only by design (doesn't bulk-push to SharePoint), to avoid an accidental mass overwrite of the shared board from a backup file.

No live data pipeline yet for jobs beyond this (unlike `barn-boards` / `SALLEE-LOAD-BOARD`'s Power Automate pipelines) — sync here is direct browser-to-Graph-API, no Power Automate involved.

## Turnaround-time (in progress, not live yet)

See `turnaround-sketch.html` — a working proof-of-concept of the actual comparison logic: for a driver's back-to-back jobs, compute (previous trip's drive time) + (2hr buffer) + (drive time to the next job's origin), and flag it if the next job's start time doesn't leave enough room. Correctly handles gaps that cross midnight into the next day.

**Known gap: the sketch predates the column-based rebuild.** It was built against the older driver-strip drag model and hasn't been ported to the current column layout yet. The underlying turnaround math (`getTurnaroundWarning`, the drive-time lookup) is still valid and reusable — it just needs to be re-attached to the new column-based job cards before it's mergeable into `index.html`.

The sketch uses a hardcoded sample drive-time table (4 tracks only: KEE/BEL/CD/FG) — not real data. The real version needs `drive_times.json`, generated by the script in `scripts/drive-times/`.

## scripts/drive-times/

A standalone Python script that calls Google's Routes API once against a fixed location list (your real 26 tracks, pulled from the Load Board's `TRACK_ADDRESSES`) and writes a static `drive_times.json` lookup — no live API calls needed at dispatch time. See that folder's own README for setup steps (Google Cloud project, billing, API key, GitHub secret).

**Known gap:** Origin/Destination Trainer-Farm fields are free text, not a fixed list, so farms aren't covered by this matrix yet. Plan is to grow `locations.json` over time as farm addresses become available.

## Roadmap

- **Port the turnaround-time sketch to the column-based layout**, then get a real Google Cloud API key and run `compute_drive_times.py` for real, replacing the sketch's sample data.
- **Publish `drive_times.json`** somewhere the live board can fetch it (same pattern as `orders.json` on the Load Board).
- **Extend duplicate-time conflict checking** to Leave Yard Time and Maintenance Time — currently only Load Time is checked for double-booking.
- **Grow the farm/trainer address list** as they come up in regular dispatch use.
- **Print / simple view**: a no-login "print a load" view, in the same spirit as the Load Board's planned standalone print view.
- **Conflict resolution UI**: writes currently overwrite without checking SharePoint's `etag`, so two dispatchers editing the exact same job at the exact same moment would have last-write-win with no warning. Fine at current usage levels; worth revisiting if that ever causes a real collision.

## Notes

- NAV (Microsoft) remains the system of record for billing/BOL — this board is an operational/coordination layer only.
- Starter driver roster was seeded from the header rows of the original `DISPATCH_CHART_2026.xlsx` "Chart" tab; that source workbook is a freeform whiteboard layout (not a clean table) and was not parsed automatically for job data — jobs are entered fresh through the UI.
