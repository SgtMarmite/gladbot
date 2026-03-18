from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.api.routes import init_routes, router
from src.api.websocket import ConnectionManager
from src.bot.arena import ArenaModule
from src.bot.dungeon import DungeonModule
from src.bot.engine import BotEngine
from src.bot.equipment import EquipmentModule
from src.bot.expedition import ExpeditionModule
from src.bot.inventory import InventoryModule
from src.bot.packages import PackagesModule
from src.bot.quests import QuestsModule
from src.bot.smelting import SmeltingModule
from src.bot.training import TrainingModule
from src.bot.work import WorkModule
from src.config import Settings
from src.session.manager import SessionManager

if getattr(sys, 'frozen', False):
    WEB_DIR = Path(sys._MEIPASS) / "src" / "web"
else:
    WEB_DIR = Path(__file__).parent / "web"


def create_app() -> FastAPI:
    settings = Settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    session = SessionManager(settings)
    ws_manager = ConnectionManager()
    engine = BotEngine(session)

    inventory = InventoryModule(session)
    inventory.config["heal_threshold"] = settings.heal_threshold

    equipment = EquipmentModule(session)
    equipment.config.update({
        "sell_below_quality": settings.equipment.sell_below_quality,
        "compare_to_equipped": settings.equipment.compare_to_equipped,
        "auto_equip": settings.equipment.auto_equip,
    })

    training = TrainingModule(session)
    training.config.update({
        "priority_weights": settings.training_weights.model_dump(),
        "gold_reserve": settings.gold_reserve,
    })

    expedition = ExpeditionModule(session, inventory_module=inventory)
    dungeon = DungeonModule(session, inventory_module=inventory)
    arena = ArenaModule(session, inventory_module=inventory)
    quests = QuestsModule(session)
    work = WorkModule(session)
    packages = PackagesModule(session)
    smelting = SmeltingModule(session)

    for mod in [inventory, equipment, training, expedition, dungeon, arena, quests, work, packages, smelting]:
        engine.register(mod)

    engine.on_log(ws_manager.broadcast_log)

    async def on_expired():
        await ws_manager.broadcast_session_status(False)

    session.on_session_expired(on_expired)

    init_routes(session, engine, ws_manager)

    app = FastAPI(title="Gladbot")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)

    @app.middleware("http")
    async def no_cache_static(request: Request, call_next):
        response: Response = await call_next(request)
        if request.url.path.endswith((".js", ".css", ".html")) or request.url.path == "/":
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response

    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="static")

    return app


app = create_app()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gladbot")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    uvicorn.run("src.main:app", host="127.0.0.1", port=args.port)
