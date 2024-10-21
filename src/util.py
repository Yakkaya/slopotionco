# Table Names

# Inventory Management Tables
INVENTORY_TABLE_NAME = "global_inventory"
POTION_TYPES_TABLE_NAME = "potion_types"
CATALOG_TABLE_NAME = "catalog_items"
POTION_COMPOSITIONS_TABLE_NAME = "potion_compositions"

# Order Management Tables
CARTS_TABLE_NAME = "carts"
CART_ITEMS_TABLE_NAME = "cart_items"

INVENTORY_ML_TYPES = ["num_green_ml", "num_red_ml", "num_blue_ml", "num_dark_ml"]

def get_ml_attribute_from_sku(barrel_sku: str) -> str:
    if "red" in barrel_sku.lower():
        return INVENTORY_ML_TYPES[1]
    elif "green" in barrel_sku.lower():
        return INVENTORY_ML_TYPES[0]
    elif "blue" in barrel_sku.lower():
        return INVENTORY_ML_TYPES[2]
    elif "dark" in barrel_sku.lower():
        return INVENTORY_ML_TYPES[3]
    else:
        raise ValueError(f"Invalid SKU: {barrel_sku} does not contain a valid color")
