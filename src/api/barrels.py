import sqlalchemy
from src import database as db
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
from src.util import (
    INVENTORY_TABLE_NAME,
    get_ml_attribute_from_sku
)

router = APIRouter(
    prefix="/barrels",
    tags=["barrels"],
    dependencies=[Depends(auth.get_api_key)],
)

class Barrel(BaseModel):
    sku: str
    ml_per_barrel: int
    potion_type: list[int]
    price: int
    quantity: int

class PurchaseRequest(BaseModel):
    sku: str
    quantity: int


@router.post("/deliver/{order_id}")
def post_deliver_barrels(barrels_delivered: list[Barrel], order_id: int):
    ml_types_to_update = []
    barrel_costs = 0

    for barrel in barrels_delivered:
        ml = barrel.ml_per_barrel
        ml_types_to_update.append((get_ml_attribute_from_sku(barrel.sku), ml))
        barrel_costs += barrel.quantity * barrel.price

    set_clauses = ", ".join([f"{attr} = {attr} + :ml_val_{i}" for i, (attr, _) in enumerate(ml_types_to_update)])

    update_expression = (f"""
        UPDATE {INVENTORY_TABLE_NAME} 
        SET {set_clauses},
            gold = gold - :barrel_cost
    """)

    params = {f"ml_val_{i}": ml for i, (_, ml) in enumerate(ml_types_to_update)}
    params['barrel_cost'] = barrel_costs

    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text(update_expression), params)

    print(f"Barrels delivered: {barrels_delivered} for order ID: {order_id}")
    return "OK"


@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]) -> list[PurchaseRequest]:
    requests = []
    print("Wholesale catalog:", wholesale_catalog)

    select_gold_expression = f"SELECT gold, num_red_ml, num_green_ml, num_blue_ml, num_dark_ml FROM {INVENTORY_TABLE_NAME}"
    
    # Fetch the current amount of gold and milliliters of each type
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(select_gold_expression))
        row = result.fetchone()
        gold_plan = row[0]
        ml_inventory = {
            "num_red_ml": row[1],
            "num_green_ml": row[2],
            "num_blue_ml": row[3],
            "num_dark_ml": row[4]
        }

    for barrel in wholesale_catalog:
        # Current Logic: Request 1 if ml quantity is less than 500 for the given potion type and if there's enough gold
        if ml_inventory[(get_ml_attribute_from_sku(barrel.sku))] < 500 and gold_plan >= barrel.price:
            purchase_request = PurchaseRequest(
                sku=barrel.sku,
                quantity=1
            )
            gold_plan -= barrel.price
            requests.append(purchase_request)

    print("Generated purchase requests:", requests)
    return requests
