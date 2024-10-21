---------------------------------
------ INVENTORY MANAGEMENT -----
---------------------------------

----------------------
-- GLOBAL INVENTORY --
-----------------------
-- This table tracks the available milliliters of each element (red, blue, green, dark) and gold
CREATE TABLE global_inventory (
    id SERIAL PRIMARY KEY,
    num_red_ml INT DEFAULT 0,   -- Available milliliters of red element
    num_blue_ml INT DEFAULT 0,  -- Available milliliters of blue element
    num_green_ml INT DEFAULT 0, -- Available milliliters of green element
    num_dark_ml INT DEFAULT 0,  -- Available milliliters of dark element
    gold INT DEFAULT 0         -- Global gold
);


----------------------
-- POTION TYPES --
-----------------------
-- Defines each potion type (SKU, name, and price)
CREATE TABLE potion_types (
    id SERIAL PRIMARY KEY,
    sku VARCHAR(50) UNIQUE NOT NULL, -- SKU for each potion (e.g., GREEN_POTION_0)
    name VARCHAR(100) NOT NULL,      -- Potion name (e.g., 'green potion')
    price INT DEFAULT 0              -- Potion price
);

-- Initial values
INSERT INTO potion_types (sku, name, price) 
VALUES 
('GREEN_POTION_0', 'Green Potion', 50),
('RED_POTION_0', 'Red Potion', 50),
('BLUE_POTION_0', 'Blue Potion', 50),
('DARK_POTION_0', 'Dark Potion', 50),
('TURQUOISE_POTION_0', 'Turquoise Potion', 60),
('RAINBOW_POTION_0', 'Rainbow Potion', 70);


----------------------
-- CATALOG ITEMS --
-----------------------
-- Tracks the quantity of each potion available in the catalog
CREATE TABLE catalog_items (
    id SERIAL PRIMARY KEY,
    potion_type_id INT REFERENCES potion_types(id), -- References the potion in potion_types
    quantity INT DEFAULT 0                          -- Quantity of the potion in stock
);

-- Populate with initial values
INSERT INTO catalog_items (potion_type_id, quantity)
VALUES
((SELECT id FROM potion_types WHERE sku = 'GREEN_POTION_0'), 0),
((SELECT id FROM potion_types WHERE sku = 'RED_POTION_0'), 0),
((SELECT id FROM potion_types WHERE sku = 'BLUE_POTION_0'), 0),
((SELECT id FROM potion_types WHERE sku = 'DARK_POTION_0'), 0),
((SELECT id FROM potion_types WHERE sku = 'TURQUOISE_POTION_0'), 0),
((SELECT id FROM potion_types WHERE sku = 'RAINBOW_POTION_0'), 0);


-------------------------
-- POTION COMPOSITIONS --
-------------------------
-- Tracks how each potion is composed of the four elements (red, blue, green, dark)
CREATE TABLE potion_compositions (
    id SERIAL PRIMARY KEY,
    potion_type_id INT REFERENCES potion_types(id), -- References potion from potion_types
    element VARCHAR(50) NOT NULL,                   -- Potion element (e.g., 'red', 'blue', 'green', 'dark')
    percentage INT CHECK (percentage >= 0 AND percentage <= 100) -- Percentage of the element
);

-- Potion Compositions: Define composition for each potion
-- Green Potion: 100% Green
INSERT INTO potion_compositions (potion_type_id, element, percentage)
VALUES
((SELECT id FROM potion_types WHERE sku = 'GREEN_POTION_0'), 'green', 100);

-- Red Potion: 100% Red
INSERT INTO potion_compositions (potion_type_id, element, percentage)
VALUES
((SELECT id FROM potion_types WHERE sku = 'RED_POTION_0'), 'red', 100);

-- Blue Potion: 100% Blue
INSERT INTO potion_compositions (potion_type_id, element, percentage)
VALUES
((SELECT id FROM potion_types WHERE sku = 'BLUE_POTION_0'), 'blue', 100);

-- Dark Potion: 100% Dark
INSERT INTO potion_compositions (potion_type_id, element, percentage)
VALUES
((SELECT id FROM potion_types WHERE sku = 'DARK_POTION_0'), 'dark', 100);

-- Turquoise Potion: 50% Green, 50% Blue
INSERT INTO potion_compositions (potion_type_id, element, percentage)
VALUES
((SELECT id FROM potion_types WHERE sku = 'TURQUOISE_POTION_0'), 'green', 50),
((SELECT id FROM potion_types WHERE sku = 'TURQUOISE_POTION_0'), 'blue', 50);

-- Rainbow Potion: 25% Red, 25% Green, 25% Blue, 25% Dark
INSERT INTO potion_compositions (potion_type_id, element, percentage)
VALUES
((SELECT id FROM potion_types WHERE sku = 'RAINBOW_POTION_0'), 'red', 25),
((SELECT id FROM potion_types WHERE sku = 'RAINBOW_POTION_0'), 'green', 25),
((SELECT id FROM potion_types WHERE sku = 'RAINBOW_POTION_0'), 'blue', 25),
((SELECT id FROM potion_types WHERE sku = 'RAINBOW_POTION_0'), 'dark', 25);


---------------------------------
------ ORDER MANAGEMENT ---------
---------------------------------


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