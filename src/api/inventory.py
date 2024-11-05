import sqlalchemy
from src import database as db
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth


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
    select_expression_inventory = f"""
        SELECT COALESCE(SUM(gold_change), 0) AS gold, 
               COALESCE(SUM(num_red_ml_change + num_green_ml_change + num_blue_ml_change + num_dark_ml_change), 0) AS total_ml
        FROM inventory_ledger
    """
    select_expression_catalog = f"SELECT COALESCE(SUM(potion_quantity_change), 0) AS total_potions FROM inventory_ledger"
    
    with db.engine.begin() as connection:
        # get milliliters and gold from inventory ledger
        result_inventory = connection.execute(sqlalchemy.text(select_expression_inventory))
        row_inventory = result_inventory.fetchone()
        ml_inventory = row_inventory[1]
        gold_inventory = row_inventory[0]
        
        # get potion quantities for each potion type from inventory ledger
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

