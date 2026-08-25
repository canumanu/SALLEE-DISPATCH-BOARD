[README (1).md](https://github.com/user-attachments/files/31438109/README.1.md)
# Drive-time matrix (Google Routes API)

Computes a static drive-time lookup between known locations (tracks, and
farms once addressed), so the dispatch board never needs a live API call.

## Files

- `compute_drive_times.py` — the script. Reads `locations.json`, calls
  Google's Routes API once, writes `drive_times.json`.
- `locations.json` — **all 26 real tracks/training centers are in here now**,
  pulled straight from the Load Board's `TRACK_ADDRESSES`. Farms/trainers
  still need to be added over time as addresses become available for them
  (see "Known gap" below).
- `drive_times.json` — generated output. This is what the dispatch board
  will eventually fetch.

## One-time Google Cloud setup (you'll need to do this part yourself)

1. Go to console.cloud.google.com, create or select a project.
2. Enable billing on that project — Routes API requires a billing account
   attached even for free-tier usage, though typical usage here should stay
   well within the free monthly allotment given the small, fixed location
   count.
3. In "APIs & Services" > Library, enable the **Routes API**.
4. In "APIs & Services" > Credentials, create an API key. Restrict it to
   the Routes API only (Application restrictions > None needed for a
   server-side script; API restrictions > Routes API).
5. Don't commit this key anywhere. Store it as a GitHub Actions secret
   (e.g. `GOOGLE_ROUTES_API_KEY`) on whichever repo runs this script.

## Running it

```
export GOOGLE_ROUTES_API_KEY="your-key-here"
pip install requests
python compute_drive_times.py
```

## Output shape

```json
{
  "generatedAt": "2026-08-25T12:00:00Z",
  "locations": [
    {"code": "KEE", "name": "Keeneland"},
    {"code": "BEL", "name": "Belmont Park"}
  ],
  "matrix": {
    "KEE": {
      "BEL": {"minutes": 743, "miles": 811.4}
    },
    "BEL": {
      "KEE": {"minutes": 738, "miles": 811.4}
    }
  }
}
```

## Known gap: farms/trainers

Origin/Destination Trainer-Farm fields on the dispatch board are free text,
not a fixed list, so they're not covered by this matrix yet. Plan is to
grow `locations.json` over time — whenever a farm shows up regularly in
dispatch, add its real address here once, and the next scheduled run picks
it up. Until a given farm has an address in this file, any leg touching it
just won't have a computed drive time, and the dispatch board should treat
that as "unknown" rather than guessing.

## Not yet wired up

This script runs standalone. Two things still need to happen before the
dispatch board actually uses this data:

1. Publish `drive_times.json` somewhere the board can fetch it (same
   pattern as `orders.json` on the Load Board — likely this script running
   in a GitHub Actions workflow on a schedule, committing the output).
2. Add the actual turnaround-time logic to the dispatch board: for a given
   driver's jobs on a day, look up (previous destination -> next origin)
   in this matrix, add the 2-hour buffer, and compare against the next
   job's start time.
