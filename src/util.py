# Global Inventory
INVENTORY_TABLE_NAME = "global_inventory"
INVENTORY_ML_TYPES = ["num_green_ml", "num_red_ml", "num_blue_ml", "num_dark_ml"]
INVENTORY_POTION_TYPES = ["num_green_potions", "num_red_potions", "num_blue_potions", "num_dark_potions"]
POTION_TYPES = [
    [0, 100, 0, 0],  # Green potion
    [100, 0, 0, 0],  # Red potion
    [0, 0, 100, 0],  # Blue potion
    [0, 0, 0, 100]   # Dark potion
]

# Catalog Items
CATALOG_TABLE_NAME = "catalog_items"
POTION_SKUS = ["GREEN_POTION_0", "RED_POTION_0", "BLUE_POTION_0", "DARK_POTION_0"]
POTION_NAMES = ["green potion", "red potion", "blue potion", "dark potion"]
POTION_SKU_TO_INVENTORY_TYPE_MAP = {
    "GREEN_POTION_0": "num_green_potions",
    "RED_POTION_0": "num_red_potions",
    "BLUE_POTION_0": "num_blue_potions",
    "DARK_POTION_0": "num_dark_potions"
}

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


def get_potion_type_barrel(potion_type: list[int]) -> str:
    if potion_type == [1, 0, 0, 0]:
        return INVENTORY_POTION_TYPES[1]
    elif potion_type == [0, 1, 0, 0]:
        return INVENTORY_POTION_TYPES[0]
    elif potion_type == [0, 0, 1, 0]:
        return INVENTORY_POTION_TYPES[2]
    elif potion_type == [0, 0, 0, 1]:
        return INVENTORY_POTION_TYPES[3]
    else:
        raise ValueError(f"Invalid potion type: {potion_type} is not a valid potion type")


def get_potion_type_bottle(potion_type: list[int]) -> str:
    if potion_type == [100, 0, 0, 0]:
        return INVENTORY_POTION_TYPES[1]
    elif potion_type == [0, 100, 0, 0]:
        return INVENTORY_POTION_TYPES[0]
    elif potion_type == [0, 0, 100, 0]:
        return INVENTORY_POTION_TYPES[2]
    elif potion_type == [0, 0, 0, 100]:
        return INVENTORY_POTION_TYPES[3]
    else:
        raise ValueError(f"Invalid potion type: {potion_type} is not a valid potion type")


def get_potion_type_from_ml(ml_type: str) -> str:
    if ml_type == INVENTORY_ML_TYPES[0]:
        return POTION_TYPES[0]
    elif ml_type == INVENTORY_ML_TYPES[1]:
        return POTION_TYPES[1]
    elif ml_type == INVENTORY_ML_TYPES[2]:
        return POTION_TYPES[2]
    elif ml_type == INVENTORY_ML_TYPES[3]:
        return POTION_TYPES[3]
    else:
        raise ValueError(f"Invalid ml type: {ml_type} is not a valid ml type") 