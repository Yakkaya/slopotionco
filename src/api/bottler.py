import sqlalchemy
import math
from src import database as db
from fastapi import APIRouter, Depends
from enum import Enum
from pydantic import BaseModel
from src.api import auth
from src.util import INVENTORY_TABLE_NAME, INVENTORY_ML_TYPES, INVENTORY_POTION_TYPES, POTION_TYPES, get_potion_type_bottle, get_potion_type_from_ml 


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
    for potion_inventory in potions_delivered:
        potion_type = get_potion_type_bottle(potion_inventory.potion_type)
        update_expression = sqlalchemy.text(f"""
        UPDATE {INVENTORY_TABLE_NAME} 
        SET {potion_type} = {potion_type} + :quantity
        """)
        with db.engine.begin() as connection:
            connection.execute(update_expression, {
                "quantity": potion_inventory.quantity
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

    # Version 2 Logic: bottle all ml of each barrel into its respective potion type

    requests = []
    
    for ml_type in INVENTORY_ML_TYPES:
        with db.engine.begin() as connection:
            select_expression = f"SELECT {ml_type} FROM {INVENTORY_TABLE_NAME}"
            update_expression = sqlalchemy.text(f"""
            UPDATE {INVENTORY_TABLE_NAME} 
            SET {ml_type} = {ml_type} - :ml
            """)
            result = connection.execute(sqlalchemy.text(select_expression))
            row = result.fetchone()
            num_ml = row[0]
            if num_ml >= 100:
                potion_quantity = math.floor(num_ml/100)
                ml_used = potion_quantity * 100
                connection.execute(update_expression, {
                    "ml": ml_used
                }) 
                requests.append(PotionInventory(potion_type=get_potion_type_from_ml(ml_type), quantity=potion_quantity))
            else:
                print(f"Not enough ml for mixing potion")

    return requests

if __name__ == "__main__":
    print(get_bottle_plan())