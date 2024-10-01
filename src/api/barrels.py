import sqlalchemy
from src import database as db
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth

INVENTORY_TABLE_NAME = "global_inventory"

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

@router.post("/deliver/{order_id}")
def post_deliver_barrels(barrels_delivered: list[Barrel], order_id: int):
    update_expression = sqlalchemy.text(f"""
        UPDATE {INVENTORY_TABLE_NAME} 
        SET num_green_ml = num_green_ml + :ml
    """)

    for barrel in barrels_delivered:
        if barrel.sku == "SMALL_GREEN_BARREL":
            ml = barrel.ml_per_barrel * barrel.quantity
            with db.engine.begin() as connection:
                connection.execute(update_expression, {
                "ml": ml
            })
    print(f"barrels delievered: {barrels_delivered} order_id: {order_id}")

    return "OK"

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    print(wholesale_catalog)
    request_quantity = 0
    select_expression = f"SELECT num_green_potions, gold FROM {INVENTORY_TABLE_NAME}"
    update_gold_expression = sqlalchemy.text(f"""
        UPDATE {INVENTORY_TABLE_NAME} 
        SET gold = gold - :barrel_cost
    """)

    for barrel in wholesale_catalog:
        # Version 1 only supports green potions
        if barrel.sku == "SMALL_GREEN_BARREL": 
            with db.engine.begin() as connection:
                result = connection.execute(sqlalchemy.text(select_expression))
                row = result.fetchone()
                num_green_potions_inventory = row[0]
                gold_inventory = row[1]
                barrel_cost = 0
                if row and num_green_potions_inventory < 10 and gold_inventory >= barrel.price:
                    # if the number of green potions is less than 10 and gold in inventory is 
                    # sufficient, request a new barrel
                    request_quantity = 1
                    barrel_cost = request_quantity * barrel.price
                    result = connection.execute(update_gold_expression, {
                        "barrel_cost": barrel_cost
                    }) 
                print(f"Requested {request_quantity} small green barrel(s). Deducted gold by {barrel_cost}")

    return [
        {
            "sku": "SMALL_GREEN_BARREL",
            "quantity": request_quantity,
        }
    ]

