import sqlalchemy
from src import database as db
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
from src.util import INVENTORY_TABLE_NAME
import math



router = APIRouter(
    prefix="/inventory",
    tags=["inventory"],
    dependencies=[Depends(auth.get_api_key)],
)

@router.get("/audit")
def get_inventory():
    """
    Retrieve and audit the current inventory, including potions, milliliters, and gold.
    """
    select_expression_inventory = f"SELECT gold, (num_red_ml + num_green_ml + num_blue_ml + num_dark_ml) AS total_ml FROM {INVENTORY_TABLE_NAME}"
    select_expression_catalog = f"SELECT SUM(quantity) AS total_potions FROM catalog_items"
    
    with db.engine.begin() as connection:
        # Get milliliters and gold from inventory table
        result_inventory = connection.execute(sqlalchemy.text(select_expression_inventory))
        row_inventory = result_inventory.fetchone()
        ml_inventory = row_inventory[1]
        gold_inventory = row_inventory[0]
        
        # Get potion quantities for each potion type from catalog items table
        result_catalog = connection.execute(sqlalchemy.text(select_expression_catalog))
        potions_inventory = result_catalog.fetchone()[0]
    
    return {
        "potions": potions_inventory,
        "ml_in_barrels": ml_inventory,
        "gold": gold_inventory
    }

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
