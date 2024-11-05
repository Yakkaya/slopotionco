import sqlalchemy
import math
from src import database as db
from fastapi import APIRouter, Depends
from enum import Enum
from pydantic import BaseModel
from src.api import auth 


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
    if not potions_delivered:
        return {"message": "No potions delivered", "order_id": order_id}

    # prepare dictionaries to track how much of each element (r, g, b, d) to deduct
    element_usage = {
        "red": 0,
        "green": 0,
        "blue": 0,
        "dark": 0
    }

    with db.engine.begin() as connection:
        for potion_inventory in potions_delivered:
            # get potion composition from the list [r, g, b, d]
            red_ml, green_ml, blue_ml, dark_ml = potion_inventory.potion_type

            potion_type_query = sqlalchemy.text("""
                SELECT id FROM potion_types
                WHERE red = :red AND green = :green AND blue = :blue AND dark = :dark
            """)
            result = connection.execute(potion_type_query, {
                "red": red_ml,
                "green": green_ml,
                "blue": blue_ml,
                "dark": dark_ml
            }).fetchone()

            if not result:
                return {"message": "Potion type not found for the given composition", "order_id": order_id}

            potion_type_id = result[0]

            # calculate total ml usage for each element based on the potion composition and quantity
            element_usage["red"] += red_ml * potion_inventory.quantity
            element_usage["green"] += green_ml * potion_inventory.quantity
            element_usage["blue"] += blue_ml * potion_inventory.quantity
            element_usage["dark"] += dark_ml * potion_inventory.quantity

            # insert ledger entry for the delivered potions
            insert_ledger_entry = {
                'transaction_type': 'bottling',
                'potion_type_id': potion_type_id,  # no specific potion, just element changes
                'num_red_ml_change': -element_usage["red"],
                'num_blue_ml_change': -element_usage["blue"],
                'num_green_ml_change': -element_usage["green"],
                'num_dark_ml_change': -element_usage["dark"],
                'gold_change': 0,
                'potion_quantity_change': potion_inventory.quantity
            }

            connection.execute(
                sqlalchemy.text(f"""
                    INSERT INTO inventory_ledger (
                        transaction_type, potion_type_id, num_red_ml_change, num_blue_ml_change,
                        num_green_ml_change, num_dark_ml_change, gold_change, potion_quantity_change
                    )
                    VALUES (:transaction_type, :potion_type_id, :num_red_ml_change, :num_blue_ml_change,
                            :num_green_ml_change, :num_dark_ml_change, :gold_change, :potion_quantity_change)
                """),
                insert_ledger_entry
            )

    print(f"Potions delivered: {potions_delivered} for order_id: {order_id}")
    return {"message": "Potions delivered successfully", "order_id": order_id}


@router.post("/plan")
def get_bottle_plan():
    requests = []

    with db.engine.begin() as connection:

        inventory_ledger_query = """
            SELECT SUM(num_red_ml_change), SUM(num_blue_ml_change),
                   SUM(num_green_ml_change), SUM(num_dark_ml_change)
            FROM inventory_ledger
        """
        inventory_ledger = connection.execute(sqlalchemy.text(inventory_ledger_query)).fetchone()
        inventory_ml = {
            'red': inventory_ledger[0],
            'blue': inventory_ledger[1],
            'green': inventory_ledger[2],
            'dark': inventory_ledger[3]
        }

        potion_types_query = """
            SELECT id, sku, red, green, blue, dark
            FROM potion_types
        """
        potion_types = connection.execute(sqlalchemy.text(potion_types_query)).fetchall()

    # organize potion types and calculate potion_type list [r, g, b, d]
    for potion in potion_types:
        potion_type_id, sku, red, green, blue, dark = potion
        elements = {
            "red": red,
            "green": green,
            "blue": blue,
            "dark": dark
        }

        min_potion_quantity = None
        ml_used_by_element = {}

        # check each element
        for element, percentage in elements.items():
            if percentage > 0:
                # calculate required ml for the potion
                required_ml = percentage
                available_ml = inventory_ml[element]

                # determine max potion quantity
                potion_quantity_by_element = math.floor(available_ml / required_ml)
                if min_potion_quantity is None or potion_quantity_by_element < min_potion_quantity:
                    min_potion_quantity = potion_quantity_by_element

                # store ml used for later inventory update
                ml_used_by_element[element] = min_potion_quantity * required_ml

        # if we can bottle at least one potion, add to requests
        if min_potion_quantity > 0:
            # calculate the milliliters of each element used for this potion type
            potion_type = [
                int(elements['red']),  # Red
                int(elements['green']),  # Green
                int(elements['blue']),  # Blue
                int(elements['dark'])   # Dark
            ]

            requests.append(PotionInventory(potion_type=potion_type, quantity=min_potion_quantity))

            # deduct used milliliters from the in-memory inventory
            for element, used_ml in ml_used_by_element.items():
                inventory_ml[element] -= used_ml

    return requests


if __name__ == "__main__":
    print(get_bottle_plan())
