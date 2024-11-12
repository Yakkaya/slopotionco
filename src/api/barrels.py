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

    # update inventory ledger with the delivered barrels
    insert_ledger_entries = [
        {
            'transaction_type': 'barrel delivery',
            'potion_type_id': None,  # only ml changes, so no potion type
            'num_red_ml_change': ml if attr == 'num_red_ml' else 0,
            'num_blue_ml_change': ml if attr == 'num_blue_ml' else 0,
            'num_green_ml_change': ml if attr == 'num_green_ml' else 0,
            'num_dark_ml_change': ml if attr == 'num_dark_ml' else 0,
            'gold_change': -barrel_costs if i == 0 else 0
        }
        for i, (attr, ml) in enumerate(ml_types_to_update)
    ]

    with db.engine.begin() as connection:
        for entry in insert_ledger_entries:
            connection.execute(
                sqlalchemy.text(f"""
                    INSERT INTO inventory_ledger (
                        transaction_type, potion_type_id, num_red_ml_change, num_blue_ml_change,
                        num_green_ml_change, num_dark_ml_change, gold_change
                    )
                    VALUES (:transaction_type, :potion_type_id, :num_red_ml_change, :num_blue_ml_change,
                            :num_green_ml_change, :num_dark_ml_change, :gold_change)
                """),
                entry
            )

    print(f"Barrels delivered: {barrels_delivered} for order ID: {order_id}")
    return "OK"


@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]) -> list[PurchaseRequest]:
    requests = []
    print("Wholesale catalog:", wholesale_catalog)

    select_gold_expression = f"SELECT SUM(gold_change), SUM(num_red_ml_change), SUM(num_green_ml_change), SUM(num_blue_ml_change), SUM(num_dark_ml_change) FROM inventory_ledger"
    
    # get current amount of gold and milliliters of each type
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
    
    # calculate target ml quantity to even out all ml types
    total_ml = sum(ml_inventory.values())
    num_types = len(ml_inventory)
    target_ml = 100 if (total_ml / num_types) == 0 else (total_ml / num_types)

    # sort barrels by price to put cheaper first
    wholesale_catalog.sort(key=lambda x: x.price)

    for barrel in wholesale_catalog:
        ml_type = get_ml_attribute_from_sku(barrel.sku)

        # check if current ml type is less than target and if there's enough gold
        while ml_inventory[ml_type] < target_ml and gold_plan >= barrel.price:
            purchase_request = PurchaseRequest(
                sku=barrel.sku,
                quantity=1
            )
            gold_plan -= barrel.price
            ml_inventory[ml_type] += barrel.ml_per_barrel  # update the ml quantity based on the barrel
            requests.append(purchase_request)

    return requests

