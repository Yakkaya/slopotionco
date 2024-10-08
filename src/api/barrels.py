import sqlalchemy
from src import database as db
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
from src.util import INVENTORY_TABLE_NAME, INVENTORY_ML_TYPES, INVENTORY_POTION_TYPES, get_ml_attribute_from_sku, get_potion_type_barrel 


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
    for barrel in barrels_delivered:
        ml_type_to_update = get_ml_attribute_from_sku(barrel.sku)
        ml = barrel.ml_per_barrel
        barrel_cost = barrel.quantity * barrel.price

        update_expression = sqlalchemy.text(f"""
        UPDATE {INVENTORY_TABLE_NAME} 
        SET {ml_type_to_update} = {ml_type_to_update} + :ml, 
        gold = gold - :barrel_cost""")

        with db.engine.begin() as connection:
            connection.execute(update_expression, {
            "ml": ml,
            "barrel_cost": barrel_cost
        })

    print(f"barrels delievered: {barrels_delivered} order_id: {order_id}")

    return "OK"


# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]) -> list[PurchaseRequest]:
    requests = []
    print(wholesale_catalog)

    select_gold_expression = f"SELECT gold FROM {INVENTORY_TABLE_NAME}" 
    gold_plan = 0
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(select_gold_expression))
        row = result.fetchone() 
        gold_plan = row[0]

    for barrel in wholesale_catalog:
        inventory_potion_type = get_potion_type_barrel(barrel.potion_type) 
        select_expression = f"SELECT {inventory_potion_type} FROM {INVENTORY_TABLE_NAME}"
        with db.engine.begin() as connection:
            result = connection.execute(sqlalchemy.text(select_expression))
            row = result.fetchone()
            potion_inventory = row[0]
            if potion_inventory < 10 and gold_plan >= barrel.price:
                # if the number of this potion type is less than 10 and gold in inventory is 
                # sufficient, request a new barrel
                request_quantity = 1
                # request_quantity = 20 - potion_inventory
                # max_affordable_quantity = gold_inventory // barrel.price
                # request_quantity = min(request_quantity, max_affordable_quantity)
                purchase_request = PurchaseRequest(
                    sku=barrel.sku,
                    quantity=request_quantity
                )
                gold_plan -= barrel.price
                requests.append(purchase_request)
    print(requests)
    return requests