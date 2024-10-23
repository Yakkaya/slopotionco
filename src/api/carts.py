import sqlalchemy
from src import database as db
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
from src.api.catalog import CatalogItem
from src.util import CATALOG_TABLE_NAME
from enum import Enum

router = APIRouter(
    prefix="/carts",
    tags=["cart"],
    dependencies=[Depends(auth.get_api_key)],
)

class search_sort_options(str, Enum):
    customer_name = "customer_name"
    item_sku = "item_sku"
    line_item_total = "line_item_total"
    timestamp = "timestamp"

class search_sort_order(str, Enum):
    asc = "asc"
    desc = "desc"

class OrderLineItem(BaseModel):
    line_item_id: int
    item_sku: str
    customer_name: str
    line_item_total: int
    timestamp: str

@router.get("/search/", tags=["search"])
def search_orders(
    customer_name: str = "",
    potion_sku: str = "",
    search_page: str = "",
    sort_col: search_sort_options = search_sort_options.timestamp,
    sort_order: search_sort_order = search_sort_order.desc,
):
    """
    Search for cart line items by customer name and/or potion sku.

    Customer name and potion sku filter to orders that contain the 
    string (case insensitive). If the filters aren't provided, no
    filtering occurs on the respective search term.

    Search page is a cursor for pagination. The response to this
    search endpoint will return previous or next if there is a
    previous or next page of results available. The token passed
    in that search response can be passed in the next search request
    as search page to get that page of results.

    Sort col is which column to sort by and sort order is the direction
    of the search. They default to searching by timestamp of the order
    in descending order.

    The response itself contains a previous and next page token (if
    such pages exist) and the results as an array of line items. Each
    line item contains the line item id (must be unique), item sku, 
    customer name, line item total (in gold), and timestamp of the order.
    Your results must be paginated, the max results you can return at any
    time is 5 total line items.
    """

    # simulate searching through orders
    results = [
        OrderLineItem(
            line_item_id=1,
            item_sku="GREEN_POTION_0",
            customer_name="Test",
            line_item_total=50,
            timestamp="2021-01-01T00:00:00Z",
        )
    ]

    start = int(search_page) * 5
    end = start + 5

    print("Search page: %s", search_page)
    return {
        "previous": int(search_page) - 1 if int(search_page) > 0 else None,
        "next": int(search_page) + 1 if len(results[start:end]) == 5 else None,
        "results": results[start:end],
    }

class Customer(BaseModel):
    customer_name: str
    character_class: str
    level: int

@router.post("/visits/{visit_id}")
def post_visits(visit_id: int, customers: list[Customer]):
    """
    Which customers visited the shop today?
    """
    print(f"Visit {visit_id} Customers: {customers}")
    return {"success": True}

@router.post("/")
def create_cart(new_cart: Customer):
    """
    Create a new cart for the customer and store it in the database.
    """
    with db.engine.begin() as connection:
        # Insert the new cart into the `carts` table
        insert_cart_query = sqlalchemy.text("""
            INSERT INTO carts (customer_name) 
            VALUES (:customer_name)
            RETURNING id
        """)
        result = connection.execute(insert_cart_query, {"customer_name": new_cart.customer_name})
        cart_id = result.fetchone()[0]

    return {"cart_id": cart_id}

class CartItem(BaseModel):
    quantity: int

@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    """
    Add an item to the cart by SKU and quantity.
    """
    with db.engine.begin() as connection:
        # Check if the cart exists
        select_cart_query = sqlalchemy.text("""
            SELECT id FROM carts WHERE id = :cart_id
        """)
        result = connection.execute(select_cart_query, {"cart_id": cart_id})
        if not result.fetchone():
            return {"error": "Cart not found"}

        # Check if the item exists in the catalog_items table by joining with potion_types to get SKU
        select_catalog_item_query = sqlalchemy.text("""
            SELECT ci.id, pt.price FROM catalog_items ci
            JOIN potion_types pt ON ci.potion_type_id = pt.id
            WHERE pt.sku = :item_sku
        """)
        result = connection.execute(select_catalog_item_query, {"item_sku": item_sku})
        catalog_item = result.fetchone()
        if not catalog_item:
            return {"error": "Item not found in catalog_items"}

        catalog_item_id, item_price = catalog_item

        # Check if the item already exists in the cart_items table
        select_cart_item_query = sqlalchemy.text("""
            SELECT quantity FROM cart_items
            WHERE cart_id = :cart_id AND potion_type_id = :potion_type_id
        """)
        result = connection.execute(select_cart_item_query, {
            "cart_id": cart_id,
            "potion_type_id": catalog_item_id
        })
        existing_item = result.fetchone()

        if existing_item:
            # If the item exists, update the quantity
            update_item_query = sqlalchemy.text("""
                UPDATE cart_items
                SET quantity = quantity + :quantity
                WHERE cart_id = :cart_id AND potion_type_id = :potion_type_id
            """)
            connection.execute(update_item_query, {
                "cart_id": cart_id,
                "potion_type_id": catalog_item_id,
                "quantity": cart_item.quantity
            })
        else:
            # If the item does not exist, insert it
            insert_item_query = sqlalchemy.text("""
                INSERT INTO cart_items (cart_id, potion_type_id, quantity, price)
                VALUES (:cart_id, :potion_type_id, :quantity, :price)
            """)
            connection.execute(insert_item_query, {
                "cart_id": cart_id,
                "potion_type_id": catalog_item_id,
                "quantity": cart_item.quantity,
                "price": item_price
            })

    return {"success": True}





class CartCheckout(BaseModel):
    payment: str

@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    """
    Perform checkout for the cart, calculate total cost, and update catalog inventory.
    """
    with db.engine.begin() as connection:
        # Check if the cart exists
        select_cart_query = sqlalchemy.text("""
            SELECT customer_name FROM carts WHERE id = :cart_id
        """)
        result = connection.execute(select_cart_query, {"cart_id": cart_id})
        cart = result.fetchone()
        if not cart:
            return {"error": "Cart not found"}

        # Retrieve cart items and calculate total cost
        select_items_query = sqlalchemy.text("""
            SELECT ci.potion_type_id, ci.quantity, ci.price, cat.quantity as available_quantity, pt.sku
            FROM cart_items ci
            JOIN catalog_items cat ON ci.potion_type_id = cat.id
            JOIN potion_types pt ON cat.potion_type_id = pt.id
            WHERE ci.cart_id = :cart_id
        """)
        cart_items = connection.execute(select_items_query, {"cart_id": cart_id}).fetchall()

        if not cart_items:
            return {"error": "No items in cart"}

        total_potions_bought = 0
        total_gold_paid = 0

        for item in cart_items:
            potion_type_id, quantity, price, available_quantity, sku = item
            if quantity > available_quantity:
                return {"error": f"Not enough inventory for SKU {sku}. Available: {available_quantity}, Requested: {quantity}"}

            total_gold_for_item = price * quantity
            total_gold_paid += total_gold_for_item
            total_potions_bought += quantity

            # Update the catalog inventory for each item
            update_catalog_query = sqlalchemy.text("""
                UPDATE catalog_items
                SET quantity = quantity - :quantity
                WHERE id = :potion_type_id
            """)
            connection.execute(update_catalog_query, {
                "quantity": quantity,
                "potion_type_id": potion_type_id
            })

            # Remove the row if the quantity reaches 0
            delete_zero_quantity_query = sqlalchemy.text("""
                DELETE FROM catalog_items
                WHERE id = :potion_type_id AND quantity <= 0
            """)

            connection.execute(delete_zero_quantity_query, {
                "potion_type_id": potion_type_id
            })
        
        # Update the global inventory gold after successful checkout
        update_gold_query = sqlalchemy.text("""
            UPDATE global_inventory
            SET gold = gold + :total_gold_paid
        """)
        connection.execute(update_gold_query, {
            "total_gold_paid": total_gold_paid
        })

        # Delete the cart items after successful checkout
        delete_cart_items_query = sqlalchemy.text("""
            DELETE FROM cart_items WHERE cart_id = :cart_id
        """)
        connection.execute(delete_cart_items_query, {"cart_id": cart_id})

    return {
        "total_potions_bought": total_potions_bought,
        "total_gold_paid": total_gold_paid,
        "message": "Checkout successful"
    }
