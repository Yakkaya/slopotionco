import sqlalchemy
from src import database as db
from fastapi import APIRouter
from pydantic import BaseModel
from src.util import CATALOG_TABLE_NAME, POTION_TYPES_TABLE_NAME, POTION_COMPOSITIONS_TABLE_NAME

router = APIRouter()

class CatalogItem(BaseModel):
    sku: str
    name: str
    quantity: int
    price: int
    potion_type: list[int]  # Array of percentages [r, g, b, d]

@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    catalog = []

    with db.engine.begin() as connection:
        # Fetch all necessary data from potion_types and catalog_items
        catalog_query = f"""
        SELECT pt.sku, pt.name, pt.price, ci.quantity, pt.id AS potion_type_id
        FROM {POTION_TYPES_TABLE_NAME} pt
        JOIN {CATALOG_TABLE_NAME} ci
        ON pt.id = ci.potion_type_id
        """
        result = connection.execute(sqlalchemy.text(catalog_query))
        rows = result.fetchall()

        # For each catalog item, fetch the potion composition (red, green, blue, dark percentages)
        for row in rows:
            potion_type_id = row[4]

            # Query to fetch potion composition for this potion
            composition_query = f"""
            SELECT element, percentage
            FROM {POTION_COMPOSITIONS_TABLE_NAME}
            WHERE potion_type_id = :potion_type_id
            """
            composition_result = connection.execute(sqlalchemy.text(composition_query), {
                "potion_type_id": potion_type_id
            })

            # Initialize potion type percentages in the order: [red, green, blue, dark]
            potion_type_percentages = [0, 0, 0, 0]
            element_map = {'red': 0, 'green': 1, 'blue': 2, 'dark': 3}

            # Populate the potion type percentages based on the elements
            for composition_row in composition_result:
                element = composition_row[0]
                percentage = composition_row[1]
                if element in element_map:
                    potion_type_percentages[element_map[element]] = percentage

            # Create the CatalogItem instance

            catalog_item = CatalogItem(
                sku=row[0],
                name=row[1],
                quantity=row[3],
                price=row[2],
                potion_type=potion_type_percentages  # Array of [r, g, b, d] percentages
            )
            catalog.append(catalog_item)

    return catalog

