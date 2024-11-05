import sqlalchemy
from src import database as db
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
from enum import Enum

router = APIRouter(
    prefix="/carts",
    tags=["cart"],
    dependencies=[Depends(auth.get_api_key)],
)

class SearchSortOptions(str, Enum):
    customer_name = "customer_name"
    item_sku = "item_sku"
    line_item_total = "line_item_total"
    timestamp = "timestamp"

class SearchSortOrder(str, Enum):
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
    sort_col: SearchSortOptions = SearchSortOptions.timestamp,
    sort_order: SearchSortOrder = SearchSortOrder.desc,
):
    """
    Search for cart line items by customer name and/or potion sku.
    """
    # simulate searching through orders (pagination limit: 5 results per page)
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
    Track which customers visited the shop today.
    """
    print(f"Visit {visit_id} Customers: {customers}")
    return {"success": True}

@router.post("/")
def create_cart(new_cart: Customer):
    """
    Create a new cart for the customer and store it in the database.
    """
    with db.engine.begin() as connection:
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
        # check if the cart exists
        select_cart_query = sqlalchemy.text("""
            SELECT id FROM carts WHERE id = :cart_id
        """)
        result = connection.execute(select_cart_query, {"cart_id": cart_id})
        if not result.fetchone():
            return {"error": "Cart not found"}

        # check if the item exists in the potion_types table by SKU
        select_potion_query = sqlalchemy.text("""
            SELECT id, price FROM potion_types WHERE sku = :item_sku
        """)
        result = connection.execute(select_potion_query, {"item_sku": item_sku})
        potion = result.fetchone()
        if not potion:
            return {"error": "Item not found in potion_types"}

        potion_type_id, item_price = potion

        # check if the item already exists in the cart_items table
        select_cart_item_query = sqlalchemy.text("""
            SELECT quantity FROM cart_items
            WHERE cart_id = :cart_id AND potion_type_id = :potion_type_id
        """)
        result = connection.execute(select_cart_item_query, {
            "cart_id": cart_id,
            "potion_type_id": potion_type_id
        })
        existing_item = result.fetchone()

        if existing_item:
            # if the item exists, update the quantity
            update_item_query = sqlalchemy.text("""
                UPDATE cart_items
                SET quantity = quantity + :quantity
                WHERE cart_id = :cart_id AND potion_type_id = :potion_type_id
            """)
            connection.execute(update_item_query, {
                "cart_id": cart_id,
                "potion_type_id": potion_type_id,
                "quantity": cart_item.quantity
            })
        else:
            # if the item does not exist, insert it
            insert_item_query = sqlalchemy.text("""
                INSERT INTO cart_items (cart_id, potion_type_id, quantity, price)
                VALUES (:cart_id, :potion_type_id, :quantity, :price)
            """)
            connection.execute(insert_item_query, {
                "cart_id": cart_id,
                "potion_type_id": potion_type_id,
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
        # check if the cart exists
        select_cart_query = sqlalchemy.text("""
            SELECT customer_name FROM carts WHERE id = :cart_id
        """)
        result = connection.execute(select_cart_query, {"cart_id": cart_id})
        cart = result.fetchone()
        if not cart:
            return {"error": "Cart not found"}

        # retrieve cart items and calculate total cost
        select_items_query = sqlalchemy.text("""
            SELECT ci.potion_type_id, ci.quantity, ci.price, pt.sku
            FROM cart_items ci
            JOIN potion_types pt ON ci.potion_type_id = pt.id
            WHERE ci.cart_id = :cart_id
        """)
        cart_items = connection.execute(select_items_query, {"cart_id": cart_id}).fetchall()

        if not cart_items:
            return {"error": "No items in cart"}

        total_potions_bought = 0
        total_gold_paid = 0

        for item in cart_items:
            potion_type_id, quantity, price, sku = item
            total_gold_for_item = price * quantity
            total_gold_paid += total_gold_for_item
            total_potions_bought += quantity

            # insert a ledger entry for the purchased items
            insert_ledger_entry = sqlalchemy.text("""
                INSERT INTO inventory_ledger (
                    transaction_type, potion_type_id, potion_quantity_change, gold_change
                )
                VALUES ('purchase', :potion_type_id, -:quantity, :gold_change)
            """)
            connection.execute(insert_ledger_entry, {
                "potion_type_id": potion_type_id,
                "quantity": quantity,
                "gold_change": total_gold_for_item
            })
        
        # delete the cart items and the cart after successful checkout
        delete_cart_and_items_query = sqlalchemy.text("""
            DELETE FROM cart_items WHERE cart_id = :cart_id;
            DELETE FROM carts WHERE id = :cart_id;
        """)
        connection.execute(delete_cart_and_items_query, {"cart_id": cart_id})

    return {
        "total_potions_bought": total_potions_bought,
        "total_gold_paid": total_gold_paid,
        "message": "Checkout successful"
    }


