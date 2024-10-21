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
    select_expression_inventory = f"SELECT num_red_ml, num_green_ml, num_blue_ml, num_dark_ml, gold FROM {INVENTORY_TABLE_NAME}"
    select_expression_catalog = f"SELECT pt.sku, ci.quantity FROM catalog_items ci JOIN potion_types pt ON ci.potion_type_id = pt.id"
    
    with db.engine.begin() as connection:
        # Get milliliters and gold from inventory table
        result_inventory = connection.execute(sqlalchemy.text(select_expression_inventory))
        row_inventory = result_inventory.fetchone()
        num_red_ml_inventory = row_inventory[0]
        num_green_ml_inventory = row_inventory[1]
        num_blue_ml_inventory = row_inventory[2]
        num_dark_ml_inventory = row_inventory[3]
        gold_inventory = row_inventory[4]
        
        # Get potion quantities for each potion type from catalog items table
        result_catalog = connection.execute(sqlalchemy.text(select_expression_catalog))
        potions_inventory = {row[0]: row[1] for row in result_catalog}
    
    return {
        "potions": potions_inventory,
        "ml_in_barrels": {
            "red": num_red_ml_inventory,
            "green": num_green_ml_inventory,
            "blue": num_blue_ml_inventory,
            "dark": num_dark_ml_inventory
        },
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
        "potion_capacity": 50,
        "ml_capacity": 10000
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
