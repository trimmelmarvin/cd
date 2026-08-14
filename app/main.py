from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

app = FastAPI(title="Marvin Dashboard", version="0.1.0")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# --- In-memory Beispiel-Datenspeicher (spaeter durch DB ersetzen) ---
items: list[dict] = [
    {"id": 1, "name": "Beispiel-Eintrag", "value": 42},
]


class Item(BaseModel):
    name: str
    value: int


# --- Web-UI ---
@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse(
        "index.html", {"request": request, "items": items}
    )


# --- API ---
@app.get("/api/status")
def api_status():
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}


@app.get("/api/items")
def api_list_items():
    return items


@app.post("/api/items")
def api_create_item(item: Item):
    new_id = max((i["id"] for i in items), default=0) + 1
    entry = {"id": new_id, "name": item.name, "value": item.value}
    items.append(entry)
    return entry


@app.delete("/api/items/{item_id}")
def api_delete_item(item_id: int):
    global items
    items = [i for i in items if i["id"] != item_id]
    return {"deleted": item_id}
