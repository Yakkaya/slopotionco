import sqlalchemy
from src import database as db
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import math


INVENTORY_TABLE_NAME = "global_inventory"

router = APIRouter(
    prefix="/inventory",
    tags=["inventory"],
    dependencies=[Depends(auth.get_api_key)],
)

@router.get("/audit")
def get_inventory():
    """ """
    select_expression = f"SELECT num_green_potions, num_green_ml, gold FROM {INVENTORY_TABLE_NAME}"
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(select_expression))
        row = result.fetchone()
        num_green_potions_inventory = row[0]
        num_green_ml_inventory = row[1]
        gold_inventory = row[2]
    return {"number_of_potions": num_green_potions_inventory, "ml_in_barrels": num_green_ml_inventory, "gold": gold_inventory}

# Gets called once a day
@router.post("/plan")
def get_capacity_plan():
    """ 
    Start with 1 capacity for 50 potions and 1 capacity for 10000 ml of potion. Each additional 
    capacity unit costs 1000 gold.
    """

    return {
        "potion_capacity": 0,
        "ml_capacity": 0
        }

class CapacityPurchase(BaseModel):
    potion_capacity: int
    ml_capacity: int

# Gets called once a day
@router.post("/deliver/{order_id}")
def deliver_capacity_plan(capacity_purchase : CapacityPurchase, order_id: int):
    """ 
    Start with 1 capacity for 50 potions and 1 capacity for 10000 ml of potion. Each additional 
    capacity unit costs 1000 gold.
    """

    return "OK"
