import sqlalchemy
from src import database as db
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth

INVENTORY_TABLE_NAME = "global_inventory"
INVENTORY_ML_TYPES = ["num_green_ml", "num_red_ml", "num_blue_ml", "num_dark_ml"]
INVENTORY_POTION_TYPES = ["num_green_potions", "num_red_potions", "num_blue_potions", "num_dark_potions"]

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

    for barrel in wholesale_catalog:
        potion_type_to_check = get_potion_type_from_sku(barrel.sku) 
        select_expression = f"SELECT {potion_type_to_check}, gold FROM {INVENTORY_TABLE_NAME}"
        with db.engine.begin() as connection:
            potion_type_to_check = get_potion_type(barrel.potion_type)
            result = connection.execute(sqlalchemy.text(select_expression))
            row = result.fetchone()
            potion_inventory = row[0]
            gold_inventory = row[1]
            if potion_inventory < 10 and gold_inventory >= barrel.price:
                # if the number of this potion type is less than 10 and gold in inventory is 
                # sufficient, request a new barrel
                purchase_request = PurchaseRequest(
                    sku=barrel.sku,
                    quantity=request_quantity
                )
                requests.append(purchase_request)
    print(requests)
    return requests


def get_ml_attribute_from_sku(barrel_sku: str) -> str:
    if "red" in barrel_sku.lower():
        return INVENTORY_ML_TYPES[1]
    elif "green" in barrel_sku.lower():
        return INVENTORY_ML_TYPES[0]
    elif "blue" in barrel_sku.lower():
        return INVENTORY_ML_TYPES[2]
    elif "dark" in barrel_sku.lower():
        return INVENTORY_ML_TYPES[3]
    else:
        raise ValueError(f"Invalid SKU: {barrel_sku} does not contain a valid color")


def get_potion_type(potion_type: list[int]) -> str:
    if potion_type == [1, 0, 0, 0]:
        return INVENTORY_POTION_TYPES[1]
    elif potion_type == [0, 1, 0, 0]:
        return INVENTORY_POTION_TYPES[0]
    elif potion_type == [0, 0, 1, 0]:
        return INVENTORY_POTION_TYPES[2]
    elif potion_type == [0, 0, 0, 1]:
        return INVENTORY_POTION_TYPES[3]
    else:
        raise ValueError(f"Invalid potion type: {potion_type} is not a valid potion type")