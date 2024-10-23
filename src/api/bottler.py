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
    """
    Deliver potions based on the composition [red, green, blue, dark] for each potion.
    Find the potion type based on the composition, update the catalog, and deduct from inventory.
    Handle potions that don't use all elements.
    """
    if not potions_delivered:
        return {"message": "No potions delivered", "order_id": order_id}

    # Prepare dictionaries to track how much of each element (r, g, b, d) to deduct
    element_usage = {
        "red": 0,
        "green": 0,
        "blue": 0,
        "dark": 0
    }

    with db.engine.begin() as connection:
        for potion_inventory in potions_delivered:
            # Extract the potion composition from the list [r, g, b, d]
            red_ml, green_ml, blue_ml, dark_ml = potion_inventory.potion_type

            # Build a query to find the potion type based on the provided composition
            composition_conditions = []
            params = {}
            
            if red_ml > 0:
                composition_conditions.append("(pc.element = 'red' AND pc.percentage = :red_percentage)")
                params["red_percentage"] = red_ml
            if green_ml > 0:
                composition_conditions.append("(pc.element = 'green' AND pc.percentage = :green_percentage)")
                params["green_percentage"] = green_ml
            if blue_ml > 0:
                composition_conditions.append("(pc.element = 'blue' AND pc.percentage = :blue_percentage)")
                params["blue_percentage"] = blue_ml
            if dark_ml > 0:
                composition_conditions.append("(pc.element = 'dark' AND pc.percentage = :dark_percentage)")
                params["dark_percentage"] = dark_ml

            print(params)

            # Join the conditions to ensure all non-zero elements are matched
            condition_string = " OR ".join(composition_conditions)

            print(condition_string)

            potion_composition_query = f"""
                SELECT pc.potion_type_id
                FROM potion_compositions pc
                WHERE {condition_string}
                GROUP BY pc.potion_type_id
                HAVING COUNT(*) = {len([e for e in potion_inventory.potion_type if e > 0])}
            """
            result = connection.execute(sqlalchemy.text(potion_composition_query), params).fetchone()

            if result is None:
                return {"message": "Potion composition not found in potion_compositions", "order_id": order_id}

            # Get the potion type ID
            potion_type_id = result[0]

            # Calculate total ml usage for each element based on the potion composition and quantity
            element_usage["red"] += red_ml * potion_inventory.quantity
            element_usage["green"] += green_ml * potion_inventory.quantity
            element_usage["blue"] += blue_ml * potion_inventory.quantity
            element_usage["dark"] += dark_ml * potion_inventory.quantity

            # Insert / Update the catalog for the matching potion type
            insert_or_update_query = sqlalchemy.text("""
                INSERT INTO catalog_items (potion_type_id, quantity)
                VALUES (:potion_type_id, :quantity)
                ON CONFLICT (potion_type_id)
                DO UPDATE SET quantity = catalog_items.quantity + EXCLUDED.quantity
            """)

            connection.execute(insert_or_update_query, {
                "potion_type_id": potion_type_id,
                "quantity": potion_inventory.quantity
            })

        # Fetch current global inventory to ensure enough ml is available
        inventory_query = """
            SELECT num_red_ml, num_green_ml, num_blue_ml, num_dark_ml 
            FROM global_inventory
            LIMIT 1
        """
        global_inventory = connection.execute(sqlalchemy.text(inventory_query)).fetchone()

        # Check if there is enough ml in the global inventory for each element being used
        if ((red_ml > 0 and global_inventory[0] < element_usage["red"]) or
            (green_ml > 0 and global_inventory[1] < element_usage["green"]) or
            (blue_ml > 0 and global_inventory[2] < element_usage["blue"]) or
            (dark_ml > 0 and global_inventory[3] < element_usage["dark"])):
            return {"message": "Not enough ml in inventory to fulfill the order", "order_id": order_id}

        # Update the global inventory in a single transaction
        update_global_inventory_query = sqlalchemy.text("""
            UPDATE global_inventory
            SET num_red_ml = num_red_ml - :red_ml,
                num_green_ml = num_green_ml - :green_ml,
                num_blue_ml = num_blue_ml - :blue_ml,
                num_dark_ml = num_dark_ml - :dark_ml
        """)
        connection.execute(update_global_inventory_query, {
            "red_ml": element_usage["red"],
            "green_ml": element_usage["green"],
            "blue_ml": element_usage["blue"],
            "dark_ml": element_usage["dark"]
        })

    print(f"Potions delivered: {potions_delivered} for order_id: {order_id}")
    return {"message": "Potions delivered successfully", "order_id": order_id}


@router.post("/plan")
def get_bottle_plan():
    """
    Plan the bottling process by converting available ml in the global inventory into potions
    based on potion compositions. Dynamically fetch potion types and batch SQL queries for performance.
    """

    # Prepare list to store potion bottling requests
    requests = []

    with db.engine.begin() as connection:
        # Fetch all global inventory data in a single query
        global_inventory_query = """
            SELECT num_red_ml, num_blue_ml, num_green_ml, num_dark_ml 
            FROM global_inventory
            LIMIT 1
        """
        global_inventory = connection.execute(sqlalchemy.text(global_inventory_query)).fetchone()
        inventory_ml = {
            'red': global_inventory[0],
            'blue': global_inventory[1],
            'green': global_inventory[2],
            'dark': global_inventory[3],
        }

        # Fetch all potion compositions in a single query
        potion_compositions_query = """
            SELECT pt.id AS potion_type_id, pt.sku, pc.element, pc.percentage
            FROM potion_types pt
            JOIN potion_compositions pc ON pt.id = pc.potion_type_id
        """
        compositions = connection.execute(sqlalchemy.text(potion_compositions_query)).fetchall()

    # Organize potion compositions by potion type ID and calculate potion_type list [r, g, b, d]
    potion_compositions = {}
    for composition in compositions:
        potion_type_id, sku, element, percentage = composition
        if potion_type_id not in potion_compositions:
            potion_compositions[potion_type_id] = {
                "sku": sku,
                "elements": {"red": 0, "green": 0, "blue": 0, "dark": 0}  # Initialize all elements to 0
            }
        potion_compositions[potion_type_id]["elements"][element] = percentage

    # Calculate potion quantities based on inventory limits for each potion type
    for potion_type_id, potion_data in potion_compositions.items():
        sku = potion_data["sku"]
        elements = potion_data["elements"]

        min_potion_quantity = None
        ml_used_by_element = {}

        # Check each element to determine the limiting factor for potion bottling
        for element, percentage in elements.items():
            if percentage > 0:
                # Calculate required ml for the potion
                required_ml = percentage
                available_ml = inventory_ml[element]

                # Determine max potion quantity based on the limiting element
                potion_quantity_by_element = math.floor(available_ml / required_ml)
                if min_potion_quantity is None or potion_quantity_by_element < min_potion_quantity:
                    min_potion_quantity = potion_quantity_by_element

                # Store ml used for later inventory update
                ml_used_by_element[element] = min_potion_quantity * required_ml

        # If we can bottle at least one potion, update the inventory and catalog
        if min_potion_quantity > 0:
            # Calculate the milliliters of each element used for this potion type
            potion_type = [
                int(elements['red']),  # Red
                int(elements['green']),  # Green
                int(elements['blue']),  # Blue
                int(elements['dark'])   # Dark
            ]

            # Append a bottling request for the potion type with the composition [r, g, b, d]
            requests.append(PotionInventory(potion_type=potion_type, quantity=min_potion_quantity))

            # Deduct used milliliters from the in-memory inventory
            for element, used_ml in ml_used_by_element.items():
                inventory_ml[element] -= used_ml  # Deduct used ml from the in-memory tracking


    return requests


if __name__ == "__main__":
    print(get_bottle_plan())