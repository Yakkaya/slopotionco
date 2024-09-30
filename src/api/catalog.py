import sqlalchemy
from src import database as db
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

INVENTORY_TABLE_NAME = "global_inventory"

class CatalogItem(BaseModel):
    sku: str
    name: str
    quantity: int
    price: int
    potion_type: list[int]  # r, g, b, d as integers adding to 100

@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Each unique item combination must have only a single price.
    """

    select_expression = f"SELECT num_green_potions FROM {INVENTORY_TABLE_NAME}"

    num_green_potions = 0
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(select_expression))
        row = result.fetchone()
        if row:
            num_green_potions = row[0]
            print(row[0])
    
    # Ensure green potion quantity isnt negative
    if num_green_potions < 0:
        num_green_potions = 0 
    
    print(f"Catalog: There are {num_green_potions} available in inventory")

    return [
            {
                "sku": "GREEN_POTION_0",
                "name": "green potion",
                "quantity": num_green_potions,
                "price": 50,
                "potion_type": [0, 100, 0, 0],
            }
        ]
