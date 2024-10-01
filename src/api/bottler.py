import sqlalchemy
import math
from src import database as db
from fastapi import APIRouter, Depends
from enum import Enum
from pydantic import BaseModel
from src.api import auth


INVENTORY_TABLE_NAME = "global_inventory"

router = APIRouter(
    prefix="/bottler",
    tags=["bottler"],
    dependencies=[Depends(auth.get_api_key)],
)

class PotionInventory(BaseModel):
    potion_type: list[int]
    quantity: int

@router.post("/deliver/{order_id}")
def post_deliver_bottles(potions_delivered: list[PotionInventory], order_id: int):
    update_expression = sqlalchemy.text(f"""
        UPDATE {INVENTORY_TABLE_NAME} 
        SET num_green_potions = num_green_potions + :quantity,
        num_green_ml = num_green_ml - :ml
    """)
    
    for potion_inventory in potions_delivered:
        if potion_inventory.potion_type[1]: 
            with db.engine.begin() as connection:
                connection.execute(update_expression, {
                    "quantity": potion_inventory.quantity,
                    "ml": potion_inventory.potion_type[1]
                })
    print(f"potions delievered: {potions_delivered} order_id: {order_id}")
    return "OK"

@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """

    # Each bottle has a quantity of what proportion of red, blue, and
    # green potion to add.
    # Expressed in integers from 1 to 100 that must sum up to 100.

    # Initial logic: bottle all barrels into red potions.
    # Version 1 Logic: bottle all barrels into green potions

    select_expression = f"SELECT num_green_ml, num_green_potions FROM {INVENTORY_TABLE_NAME}"

    green_potion_quantity = 0
    
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(select_expression))
        row = result.fetchone()
        num_green_ml = row[0]
        num_green_potions = row[1]
        if num_green_potions < 10 and num_green_ml >= 100:
            # if the number of green potions is less than 10, request a new barrel
            green_potion_quantity = math.floor(row[0]/100)
        else:
            print(f"Not enough green ml for mixing potion")
    print(f"Bottle Plan: make {green_potion_quantity} green potions")

    return [
            {
                "potion_type": [0, 100, 0, 0],
                "quantity": green_potion_quantity,
            }
        ]

if __name__ == "__main__":
    print(get_bottle_plan())