import sqlalchemy
from src import database as db
from fastapi import APIRouter
from pydantic import BaseModel
from src.util import POTION_TYPES_TABLE_NAME

router = APIRouter()

class CatalogItem(BaseModel):
    sku: str
    name: str
    quantity: int
    price: int
    potion_type: list[int]  # array of percentages [r, g, b, d]

@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    catalog = []

    with db.engine.begin() as connection:
        catalog_query = f"""
        SELECT pt.sku, pt.name, pt.price, COALESCE(SUM(il.potion_quantity_change), 0) AS quantity, pt.red, pt.green, pt.blue, pt.dark
        FROM {POTION_TYPES_TABLE_NAME} pt
        LEFT JOIN inventory_ledger il ON pt.id = il.potion_type_id
        GROUP BY pt.id, pt.sku, pt.name, pt.price, pt.red, pt.green, pt.blue, pt.dark
        HAVING COALESCE(SUM(il.potion_quantity_change), 0) > 0
        """
        result = connection.execute(sqlalchemy.text(catalog_query))
        rows = result.fetchall()

        # construct potion type percentages for each catalog item
        for row in rows:
            potion_type_percentages = [row[4], row[5], row[6], row[7]]

            catalog_item = CatalogItem(
                sku=row[0],
                name=row[1],
                quantity=row[3],
                price=row[2],
                potion_type=potion_type_percentages
            )
            catalog.append(catalog_item)

    return catalog

