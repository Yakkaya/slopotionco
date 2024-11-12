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
    search_page: int = 1,
    sort_col: SearchSortOptions = SearchSortOptions.timestamp,
    sort_order: SearchSortOrder = SearchSortOrder.desc,
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

    limit = 5
    offset = (search_page - 1) * limit

    with db.engine.begin() as connection:
        order_search_query = sqlalchemy.text("""
            SELECT potion_types.sku, carts.customer_name, cart_items.quantity, to_char(carts.created_at::timestamp, 'MM/DD/YYYY, HH12:MI:SS PM') as created_at
            FROM carts
            JOIN cart_items ON carts.id = cart_items.cart_id
            JOIN potion_types ON potion_types.id = cart_items.potion_type_id
            WHERE carts.customer_name ILIKE :customer_name
            AND potion_types.sku ILIKE :potion_sku
            ORDER BY 
                CASE WHEN :sort_col = 'customer_name' AND :sort_order = 'asc' THEN carts.customer_name END ASC,
                CASE WHEN :sort_col = 'customer_name' AND :sort_order = 'desc' THEN carts.customer_name END DESC,
                CASE WHEN :sort_col = 'item_sku' AND :sort_order = 'asc' THEN potion_types.sku END ASC,
                CASE WHEN :sort_col = 'item_sku' AND :sort_order = 'desc' THEN potion_types.sku END DESC,
                CASE WHEN :sort_col = 'line_item_total' AND :sort_order = 'asc' THEN cart_items.quantity END ASC,
                CASE WHEN :sort_col = 'line_item_total' AND :sort_order = 'desc' THEN cart_items.quantity END DESC,
                CASE WHEN :sort_col = 'timestamp' AND :sort_order = 'asc' THEN carts.created_at END ASC,
                CASE WHEN :sort_col = 'timestamp' AND :sort_order = 'desc' THEN carts.created_at END DESC
            LIMIT :limit OFFSET :offset
        """)
        params = {
            "customer_name": f"%{customer_name}%", 
            "potion_sku": f"%{potion_sku}%", 
            "sort_col": sort_col.value, 
            "sort_order": sort_order.value, 
            "limit": limit, 
            "offset": offset
        }
        result = connection.execute(order_search_query, params)
        orders = [
            OrderLineItem(line_item_id=i, item_sku=row[0], customer_name=row[1], line_item_total=row[2], timestamp=row[3])
            for i, row in enumerate(result)
        ]

    previous_page = search_page - 1 if search_page > 1 else None
    next_page = search_page + 1 if len(orders) == limit else None

    return {
        "previous": previous_page,
        "next": next_page,
        "results": orders,
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


