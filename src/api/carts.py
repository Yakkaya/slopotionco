import sqlalchemy
from src import database as db
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
from src.api.catalog import CatalogItem
from enum import Enum

router = APIRouter(
    prefix="/carts",
    tags=["cart"],
    dependencies=[Depends(auth.get_api_key)],
)

INVENTORY_TABLE_NAME = "global_inventory"

class search_sort_options(str, Enum):
    customer_name = "customer_name"
    item_sku = "item_sku"
    line_item_total = "line_item_total"
    timestamp = "timestamp"

class search_sort_order(str, Enum):
    asc = "asc"
    desc = "desc"  

cart_store = {}
order_store = {}
catalog_store = [
    CatalogItem(sku="GREEN_POTION_0", name="green potion", quantity=1, price=50, potion_type=[0, 100, 0, 0])
] 

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
    """ """
    cart_id = len(cart_store) + 1
    cart_store[cart_id] = {"customer": new_cart, "items": []}
    return {"cart_id": cart_id}


class CartItem(BaseModel):
    quantity: int


@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    if cart_id not in cart_store:
        return {"error": "Cart not found"}
    
    cart_items = cart_store[cart_id]["items"]
    cart_items.append({"sku": item_sku, "quantity": cart_item.quantity})
    return {"success": True}


class CartCheckout(BaseModel):
    payment: str

@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    """ """
    if cart_id not in cart_store:
        return {"error": "Cart not found"}
    
    cart = cart_store[cart_id]
    customer = cart["customer"]
    items = cart["items"]
    
    total_potions_bought = sum(item["quantity"] for item in items)
    total_gold_paid = total_potions_bought * 50 
    
    with db.engine.begin() as connection:
        for item in items:
            # Version 1: only updating green potion inventory
            if item["sku"] == "GREEN_POTION_0":
                update_expression = sqlalchemy.text(f"""
                    UPDATE {INVENTORY_TABLE_NAME}
                    SET num_green_potions = num_green_potions - :quantity, gold = gold + :total_gold_paid
                """)
                
                result = connection.execute(update_expression, {
                    "quantity": item["quantity"],
                    "total_gold_paid": total_gold_paid
                })

    order_id = len(order_store) + 1
    order_store[order_id] = {
        "customer_name": customer.customer_name,
        "items": items,
        "total_gold_paid": total_gold_paid
    }
    
    return {"total_potions_bought": total_potions_bought, "total_gold_paid": total_gold_paid}
