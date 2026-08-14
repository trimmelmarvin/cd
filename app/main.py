import math
import time
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

app = FastAPI(title="Fahrzeug-Dashboard", version="0.2.0")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# --- Skalenendwerte der Gauges (auch vom Frontend genutzt) ---
RPM_MAX = 8000
RPM_REDLINE = 6500
SPEED_MAX = 260


class Telemetry(BaseModel):
    """Aktueller Fahrzeugzustand. Alle Felder sind optional beim Schreiben."""

    rpm: float = Field(0.0, ge=0, le=RPM_MAX)
    speed_kmh: float = Field(0.0, ge=0, le=SPEED_MAX)
    brake: bool = False
    throttle: bool = False
    clutch: bool = False


class TelemetryUpdate(BaseModel):
    """Teil-Update: nur gesetzte Felder werden uebernommen."""

    rpm: float | None = Field(None, ge=0, le=RPM_MAX)
    speed_kmh: float | None = Field(None, ge=0, le=SPEED_MAX)
    brake: bool | None = None
    throttle: bool | None = None
    clutch: bool | None = None


# --- In-memory Zustand (spaeter durch echte Datenquelle ersetzen) ---
state = Telemetry()
demo_mode = True
_started_at = time.monotonic()


def _demo_telemetry(elapsed: float) -> Telemetry:
    """Simuliert eine Beschleunigungs-/Bremsphase mit Gangwechseln.

    Zyklus von 24 s: 18 s beschleunigen ueber 4 Gaenge, dann 6 s bremsen.
    """
    cycle = 24.0
    t = elapsed % cycle
    accel_time = 18.0

    if t < accel_time:
        gears = 4
        gear_time = accel_time / gears
        gear = int(t / gear_time)
        gear_progress = (t % gear_time) / gear_time

        # Drehzahl saegt pro Gang von 2000 auf 7000 hoch.
        rpm = 2000 + gear_progress * 5000
        # Geschwindigkeit steigt ueber alle Gaenge hinweg an.
        speed = (gear + gear_progress) / gears * (SPEED_MAX * 0.8)

        # Kurz vor jedem Gangwechsel: Kupplung tritt, Gas geht weg.
        shifting = gear_progress > 0.92 and gear < gears - 1
        if shifting:
            rpm = 7000 - (gear_progress - 0.92) / 0.08 * 4000
        return Telemetry(
            rpm=rpm,
            speed_kmh=speed,
            brake=False,
            throttle=not shifting,
            clutch=shifting,
        )

    # Bremsphase: Geschwindigkeit und Drehzahl fallen ab.
    brake_progress = (t - accel_time) / (cycle - accel_time)
    falloff = math.cos(brake_progress * math.pi / 2)
    return Telemetry(
        rpm=800 + falloff * 4200,
        speed_kmh=SPEED_MAX * 0.8 * falloff,
        brake=True,
        throttle=False,
        clutch=brake_progress > 0.85,
    )


def current_telemetry() -> Telemetry:
    if demo_mode:
        return _demo_telemetry(time.monotonic() - _started_at)
    return state


# --- Web-UI ---
@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "rpm_max": RPM_MAX,
            "rpm_redline": RPM_REDLINE,
            "speed_max": SPEED_MAX,
        },
    )


# --- API ---
@app.get("/api/status")
def api_status():
    return {
        "status": "ok",
        "demo": demo_mode,
        "time": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/telemetry")
def api_get_telemetry():
    data = current_telemetry().model_dump()
    data["demo"] = demo_mode
    return data


@app.post("/api/telemetry")
def api_set_telemetry(update: TelemetryUpdate):
    """Setzt Werte aus einer externen Quelle (z. B. CAN-Bus-Gateway).

    Ein Schreibzugriff schaltet den Demo-Modus automatisch ab.
    """
    global demo_mode
    demo_mode = False
    for field, value in update.model_dump(exclude_none=True).items():
        setattr(state, field, value)
    return state


@app.post("/api/demo/{enabled}")
def api_set_demo(enabled: bool):
    global demo_mode
    demo_mode = enabled
    return {"demo": demo_mode}
