import sqlalchemy
from src import database as db
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth

INVENTORY_TABLE_NAME = "global_inventory"

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(auth.get_api_key)],
)

@router.post("/reset")
def reset():
    """
    Reset the game state. Gold goes to 100, all potions are removed from
    inventory, and all barrels are removed from inventory. Carts are all reset.
    """
    update_expression = f"UPDATE {INVENTORY_TABLE_NAME} SET num_green_potions = 0, num_green_ml = 0, gold = 100"
    with engine.begin() as connection:
        connection.execute(sqlalchemy.text(update_expression))
    return "OK"

