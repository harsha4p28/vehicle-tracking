# vehicle-tracking

## Features
### Real time location event handling

- Accepts GPS updates via POST ```/location-event```

- Automatically detects:
  - Zone entry
  - Zone exit
  - Zone to zone movement
  - Locations outside of known zones
### Zone based geofencing
- Zones are defined in ```zones.json``` using polygons.
- The service uses Shapely to perform point in polygon checks.

### Vehicle state tracking

For each vehicle, the service stores:
  - Current zone
  - Last known latitude & longitude
  - Most recent transition (enter/exit/move)
  - Full movement history in chronological order

### History endpoint

GET ```/vehicle/{vehicle_id}/history``` returns all significant movements detected for that vehicle.

## Tech Stack
- FastAPI
- Shapely
- Python Logging + RotatingFileHandler

## Files
```app.py```	FastAPI application with geofence logic, event processing, logging, and history

```zones.json```	Defines polygon boundaries for all geofence regions

```requirements.txt```	Python dependencies for running the service

```app.log```	Auto generated rotating log file storing all service events

# How It Works

## Receive GPS Event

POST ```/location-event```
The server:
- Reads vehicle_id, lat, and lon
- Determines which zone the point belongs to
- Compares it with the vehicle’s previous zone
- Detects transitions:
  - ENTERED Zone
  - EXITED Zone
  - MOVED from ZoneA to ZoneB
  - Or remains unchanged
- Stores updated state
  
**Edge case:**
If the vehicle is not inside any defined zone, "Outside of known zones" is returned.

## Track History

Each significant transition is appended to:```vehicle_history[vehicle_id]```

Stored with:
- Transition message
- New zone
- Coordinates
- Timestamp

## Query Current State
GET ```/vehicle/{vehicle_id}```
Returns:
- Current zone
- Last known coordinates
- Last transition

## View Movement History

GET ```/vehicle/{vehicle_id}/history```

Returns an ordered list of all transitions
the vehicle has made since the service started.

## Assumptions

- In memory storage is acceptable for the challenge (data is lost on restart).
- Zones are rectangular polygons defined in ```zones.json```.
- No authentication is required for the challenge.
- GPS updates are expected in correct latitude/longitude format.

## Future Improvements

If more time is available:

- Persist state in PostgreSQL
- Add real world coordinates instead of rectangular coordinates
- Add WebSocket streaming for live vehicle movement
- Build visualization UI using react Leaflet
