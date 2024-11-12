---------------------------------
------ INVENTORY MANAGEMENT -----
---------------------------------

----------------------
-- POTION TYPES --
-----------------------
-- Defines each potion type (SKU, name, and price)
CREATE TABLE potion_types (
    id SERIAL PRIMARY KEY,
    sku VARCHAR(50) UNIQUE NOT NULL,  -- SKU for each potion (e.g., GREEN_POTION_0)
    name VARCHAR(100) NOT NULL,       -- Potion name (e.g., 'green potion')
    red INT DEFAULT 0,                -- Percentage of red for this potion type
    green INT DEFAULT 0,              -- Percentage of green for this potion type
    blue INT DEFAULT 0,               -- Percentage of blue for this potion type
    dark INT DEFAULT 0,               -- Percentage of dark for this potion type
    price INT DEFAULT 0               -- Potion price
);

----------------------
-- INVENTORY LEDGER --
-----------------------
-- Append-only ledger that records all changes to inventory
CREATE TABLE inventory_ledger (
    id SERIAL PRIMARY KEY,  -- Unique ID for each ledger entry
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- Time of the transaction
    transaction_type VARCHAR(50) NOT NULL,  -- Type of transaction ('bottling', 'purchase', 'barrel delivery', etc.)
    potion_type_id INT REFERENCES potion_types(id),  -- Potion type that was affected (nullable if it's an element change)
    num_red_ml_change INT DEFAULT 0,  -- Change in the number of red milliliters
    num_blue_ml_change INT DEFAULT 0,  -- Change in the number of blue milliliters
    num_green_ml_change INT DEFAULT 0,  -- Change in the number of green milliliters
    num_dark_ml_change INT DEFAULT 0,  -- Change in the number of dark milliliters
    gold_change INT DEFAULT 0,  -- Change in gold amount
    potion_quantity_change INT DEFAULT 0  -- Change in potion quantity (+ for restock, - for sale)
);


-------------------------
-- CARTS TABLE --
-------------------------
CREATE TABLE carts (
    id SERIAL PRIMARY KEY,  -- Unique cart ID
    customer_name VARCHAR(100) NOT NULL,  -- Name of the customer
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- Time the cart was created
);

-------------------------
-- CART ITEMS TABLE --
-------------------------
CREATE TABLE cart_items (
    id SERIAL PRIMARY KEY,  -- Unique cart item ID
    cart_id INT REFERENCES carts(id) ON DELETE CASCADE,  -- Foreign key to carts
    potion_type_id INT REFERENCES potion_types(id) ON DELETE CASCADE,  -- Foreign key to potion types
    quantity INT NOT NULL,  -- Quantity of the item in the cart
    price INT NOT NULL,  -- Price of the item at the time it was added to the cart
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- Time the item was added to the cart
);

-- Initial values for potion_types
INSERT INTO potion_types (sku, name, red, green, blue, dark, price) 
VALUES 
('GREEN_POTION_0', 'Green Potion', 0, 100, 0, 0, 50),
('RED_POTION_0', 'Red Potion', 100, 0, 0, 0, 50),
('BLUE_POTION_0', 'Blue Potion', 0, 0, 100, 0, 50),
('DARK_POTION_0', 'Dark Potion', 0, 0, 0, 100, 50),
('TURQUOISE_POTION_0', 'Turquoise Potion', 0, 50, 50, 0, 5),
('RAINBOW_POTION_0', 'Rainbow Potion', 25, 25, 25, 25, 5);


----------------------
-- GLOBAL INVENTORY VIEW --
-----------------------
-- This view provides the current inventory state by aggregating the ledger
CREATE VIEW current_global_inventory AS
SELECT 
    SUM(num_red_ml_change) AS num_red_ml,
    SUM(num_blue_ml_change) AS num_blue_ml,
    SUM(num_green_ml_change) AS num_green_ml,
    SUM(num_dark_ml_change) AS num_dark_ml,
    SUM(gold_change) AS gold
FROM 
    inventory_ledger;


------------------------
-- CATALOG ITEMS VIEW --
------------------------
-- Tracks the current quantity of each potion available in the catalog by aggregating the ledger
CREATE VIEW current_catalog_items AS
SELECT 
    pt.id AS potion_type_id,
    pt.sku,
    pt.name,
    SUM(il.potion_quantity_change) AS quantity
FROM 
    potion_types pt
LEFT JOIN 
    inventory_ledger il ON pt.id = il.potion_type_id
GROUP BY 
    pt.id, pt.sku, pt.name;


----------------------------------------------
--  VERSION 5: MOCK CUSTOMER DATA INSERTION --
----------------------------------------------
INSERT INTO carts (customer_name, created_at) VALUES
('Alice', '2023-01-01 10:00:00'),
('Bob', '2023-01-02 11:00:00'),
('Charlie', '2023-01-03 12:00:00'),
('David', '2023-01-04 13:00:00'),
('Eve', '2023-01-05 14:00:00');

INSERT INTO cart_items (cart_id, potion_type_id, quantity, price, added_at) VALUES
(8, 1, 2, 100, '2023-01-01 10:05:00'),
(9, 2, 1, 50, '2023-01-02 11:05:00'),
(10, 3, 3, 150, '2023-01-03 12:05:00'),
(11, 4, 1, 50, '2023-01-04 13:05:00'),
(12, 5, 2, 10, '2023-01-05 14:05:00');
