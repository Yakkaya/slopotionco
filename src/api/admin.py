import sqlalchemy
from src import database as db
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth


router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(auth.get_api_key)],
)

@router.post("/reset")
def reset():
    """
    Reset the game state. Gold goes to 100, all potions are removed from
    inventory, and all barrels are removed from inventory. Carts are all reset.
    """
    with db.engine.begin() as connection:
        # Reset gold to 100 and ml to 0 in the global inventory
        reset_gold_query = """
        UPDATE global_inventory
        SET gold = 100, num_red_ml = 0, num_green_ml = 0, num_blue_ml = 0, num_dark_ml = 0;
        """
        connection.execute(sqlalchemy.text(reset_gold_query))

        # Set potion quantities to 0 in catalog items
        reset_potions_query = """
        UPDATE catalog_items
        SET quantity = 0;
        """
        connection.execute(sqlalchemy.text(reset_potions_query))

        # Reset carts and cart items
        delete_cart_items_query = """
        DELETE FROM cart_items;
        """
        connection.execute(sqlalchemy.text(delete_cart_items_query))

        delete_carts_query = """
        DELETE FROM carts;
        """
        connection.execute(sqlalchemy.text(delete_carts_query))
    return {"success": True, "message": "Game state has been reset"}

