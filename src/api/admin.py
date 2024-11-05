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
        # reset entry into the inventory ledger to reset gold and ml values
        inventory_query = """
            SELECT 
                COALESCE(SUM(num_red_ml_change), 0),
                COALESCE(SUM(num_blue_ml_change), 0),
                COALESCE(SUM(num_green_ml_change), 0),
                COALESCE(SUM(num_dark_ml_change), 0),
                COALESCE(SUM(gold_change), 0),
                COALESCE(SUM(potion_quantity_change), 0)
            FROM inventory_ledger
        """
        result = connection.execute(sqlalchemy.text(inventory_query)).fetchone()
        current_inventory = {
            'num_red_ml': result[0],
            'num_blue_ml': result[1],
            'num_green_ml': result[2],
            'num_dark_ml': result[3],
            'gold': result[4],
            'total_potions': result[5]
        }

        # insert a reset entry that negates the current inventory values
        reset_ledger_entry = {
            'transaction_type': 'reset',
            'potion_type_id': None,
            'num_red_ml_change': -current_inventory['num_red_ml'],
            'num_blue_ml_change': -current_inventory['num_blue_ml'],
            'num_green_ml_change': -current_inventory['num_green_ml'],
            'num_dark_ml_change': -current_inventory['num_dark_ml'],
            'gold_change': 100 - current_inventory['gold'],  # set gold to 100
            'potion_quantity_change': -current_inventory['total_potions']
        }

        connection.execute(
            sqlalchemy.text("""
                INSERT INTO inventory_ledger (
                    transaction_type, potion_type_id, num_red_ml_change, num_blue_ml_change,
                    num_green_ml_change, num_dark_ml_change, gold_change, potion_quantity_change
                )
                VALUES (
                    :transaction_type, :potion_type_id, :num_red_ml_change, :num_blue_ml_change,
                    :num_green_ml_change, :num_dark_ml_change, :gold_change, :potion_quantity_change
                )
            """),
            reset_ledger_entry
        )

        # reset carts and cart items
        delete_cart_items_query = """
        DELETE FROM cart_items;
        """
        connection.execute(sqlalchemy.text(delete_cart_items_query))

        delete_carts_query = """
        DELETE FROM carts;
        """
        connection.execute(sqlalchemy.text(delete_carts_query))
    
    return {"success": True, "message": "Game state has been reset"}



