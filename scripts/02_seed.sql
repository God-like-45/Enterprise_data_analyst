-- 02_seed.sql

INSERT INTO categories (name, description) VALUES
('Electronics', 'Gadgets, phones, and laptops'),
('Office Supplies', 'Desks, chairs, and stationery'),
('Apparel', 'Clothing and accessories');

INSERT INTO products (name, category_id, price, stock_quantity) VALUES
('Laptop Pro 15', 1, 1299.99, 50),
('Wireless Mouse', 1, 49.99, 200),
('Ergonomic Chair', 2, 299.50, 20),
('Mechanical Keyboard', 1, 149.00, 75),
('Cotton T-Shirt', 3, 19.99, 500);

INSERT INTO customers (first_name, last_name, email, country, signup_date) VALUES
('Alice', 'Smith', 'alice@example.com', 'USA', '2023-01-15 10:00:00'),
('Bob', 'Jones', 'bob@example.com', 'UK', '2023-03-22 14:30:00'),
('Charlie', 'Brown', 'charlie@example.com', 'Canada', '2023-06-10 09:15:00'),
('Priya', 'Patel', 'priya@example.in', 'India', '2023-11-05 16:45:00');

INSERT INTO employees (first_name, last_name, role, hire_date) VALUES
('John', 'Doe', 'Sales Manager', '2020-05-10'),
('Jane', 'Smith', 'Data Analyst', '2021-08-15');

INSERT INTO orders (customer_id, order_date, total_amount, status) VALUES
(1, '2023-12-01 10:30:00', 1349.98, 'Delivered'),
(4, '2023-12-05 11:15:00', 299.50, 'Shipped'),
(2, '2023-12-10 15:45:00', 149.00, 'Processing'),
(1, '2024-01-15 09:00:00', 39.98, 'Delivered');

INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
(1, 1, 1, 1299.99),
(1, 2, 1, 49.99),
(2, 3, 1, 299.50),
(3, 4, 1, 149.00),
(4, 5, 2, 19.99);

INSERT INTO payments (order_id, payment_date, amount, payment_method, status) VALUES
(1, '2023-12-01 10:35:00', 1349.98, 'Credit Card', 'Completed'),
(2, '2023-12-05 11:20:00', 299.50, 'PayPal', 'Completed'),
(3, '2023-12-10 15:50:00', 149.00, 'Credit Card', 'Completed'),
(4, '2024-01-15 09:05:00', 39.98, 'Debit Card', 'Completed');