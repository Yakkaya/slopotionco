import sqlalchemy
from src import database as db
from fastapi import APIRouter
from pydantic import BaseModel
from src.util import INVENTORY_TABLE_NAME, CATALOG_TABLE_NAME, INVENTORY_POTION_TYPES, POTION_TYPES, POTION_SKUS, POTION_NAMES

router = APIRouter()

CATALOG_TABLE_NAME = "catalog_items"
POTION_SKUS = ["GREEN_POTION_0", "RED_POTION_0", "BLUE_POTION_0", "DARK_POTION_0"]
POTION_NAMES = ["green potion", "red potion", "blue potion", "dark potion"]

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
    catalog = []

    with db.engine.begin() as connection:
        select_expression = f"SELECT {', '.join(INVENTORY_POTION_TYPES)} FROM {INVENTORY_TABLE_NAME}"
        result = connection.execute(sqlalchemy.text(select_expression))
        row = result.fetchone()
        if row:
            num_green_potions = max(row[0], 0)
            num_red_potions = max(row[1], 0)
            num_blue_potions = max(row[2], 0)
            num_dark_potions = max(row[3], 0)

            potion_quantities = [num_green_potions, num_red_potions, num_blue_potions, num_dark_potions]

            for i, potion_quantity in enumerate(potion_quantities):
                if potion_quantity > 0:
                    catalog_item = CatalogItem(
                        sku=POTION_SKUS[i],
                        name=POTION_NAMES[i],
                        quantity=potion_quantity,
                        price=50,
                        potion_type=POTION_TYPES[i]
                    )
                    catalog.append(catalog_item)

            for item in catalog:
                print(item)
                insert_query = f"""
                INSERT INTO {CATALOG_TABLE_NAME} (sku, name, quantity, price, potion_type)
                VALUES (:sku, :name, :quantity, :price, :potion_type)
                ON CONFLICT (sku) 
                DO UPDATE SET quantity = EXCLUDED.quantity;
                """
                connection.execute(sqlalchemy.text(insert_query), {
                    "sku": item.sku,
                    "name": item.name,
                    "quantity": item.quantity,
                    "price": item.price,
                    "potion_type": item.potion_type
                })

    
    return catalog
