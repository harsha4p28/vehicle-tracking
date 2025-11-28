import time
import logging
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from shapely.geometry import Point, Polygon
import json
from fastapi.middleware.cors import CORSMiddleware



logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

vehicle_logger = logging.getLogger('vehicle_logger')
vehicle_logger.setLevel(logging.INFO)
file_handler = logging.FileHandler('app.log')
file_handler.setFormatter(formatter)
vehicle_logger.addHandler(file_handler)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    start_time = time.time()

    response = None
    try:
        response = await call_next(request)
    except Exception as e:
        logger.error(f"Unhandled error: {str(e)}")
        raise

    duration = (time.time() - start_time) * 1000 
    logger.info(
        f"{request.method} {request.url.path} "
        f"Status={response.status_code} "
        f"Time={duration:.2f}ms"
    )

    return response


try:
    with open("zones.json") as f:
        zones_config = json.load(f)
except Exception as e:
    logger.error(f"Failed to load zones.json: {e}")
    raise

ZONES = {
    zone["name"]: Polygon(zone["coordinates"])
    for zone in zones_config
}

logger.info(f"Loaded zones: {list(ZONES.keys())}")

vehicle_state = {}  
vehicle_history = {} 

class LocationEvent(BaseModel):
    vehicle_id: str
    lat: float
    lon: float

def get_zone_for_point(lat, lon):
    point = Point(lon, lat)
    for name, polygon in ZONES.items():
        if polygon.contains(point):
            return name
    return None


@app.post("/location-event")
def process_location(event: LocationEvent):
    try:
        if not (-90 <= event.lat <= 90 and -180 <= event.lon <= 180):
            raise HTTPException(status_code=400, detail="Invalid coordinates")
        new_zone = get_zone_for_point(event.lat, event.lon)
        prev_zone = vehicle_state.get(event.vehicle_id, {}).get("zone")

        transition = None
        if prev_zone != new_zone:
            if prev_zone is None and new_zone is not None:
                transition = f"ENTERED {new_zone}"
            elif prev_zone is not None and new_zone is None:
                transition = f"EXITED {prev_zone}"
            elif prev_zone and new_zone:
                transition = f"MOVED from {prev_zone} to {new_zone}"

            if transition:
                vehicle_logger.info(f"Vehicle {event.vehicle_id} {transition}")

                if event.vehicle_id not in vehicle_history:
                    vehicle_history[event.vehicle_id] = []
                vehicle_history[event.vehicle_id].append({
                    "transition": transition,
                    "zone": new_zone,
                    "lat": event.lat,
                    "lon": event.lon,
                    "timestamp": time.time()
                })
        vehicle_state[event.vehicle_id] = {
            "zone": new_zone,
            "lat": event.lat,
            "lon": event.lon,
            "transition": transition,
        }
        if new_zone is None:
            new_zone="Outside of known zones"
        if transition is None:
            transition="No transition"
        return {
            "vehicle_id": event.vehicle_id,
            "current_zone": new_zone,
            "transition": transition
        }

    except Exception as e:
        logger.error(f"Error processing event for vehicle {event.vehicle_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal processing error")


@app.get("/vehicle/{vehicle_id}")
def get_vehicle_status(vehicle_id: str):
    if vehicle_id not in vehicle_state:
        logger.warning(f"Vehicle not found: {vehicle_id}")
        raise HTTPException(status_code=404, detail="Vehicle not found")

    return vehicle_state[vehicle_id]

@app.get("/vehicle/{vehicle_id}/history")
def get_vehicle_history(vehicle_id: str):
    if vehicle_id not in vehicle_history:
        return {"vehicle_id": vehicle_id, "history": []}

    return {
        "vehicle_id": vehicle_id,
        "history": vehicle_history[vehicle_id]
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/vehicles")
def list_vehicles():
    return {"vehicles": list(vehicle_state.keys())}
