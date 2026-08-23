import os
import psycopg2

# Grab the database URL from the environment (GitHub Actions will provide this)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ai_analyst:secure_password_123@localhost:5432/enterprise_db")

def initialize_database():
    print(f"Connecting to database at {DATABASE_URL}...")
    try:
        # Connect to Postgres
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        cursor = conn.cursor()

        print("Dropping existing tables to start fresh...")
        cursor.execute("DROP TABLE IF EXISTS order_items, orders, customers, products, categories CASCADE;")

        print("Creating tables...")
        cursor.execute("""
            CREATE TABLE categories (
                category_id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL
            );

            CREATE TABLE products (
                product_id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                price DECIMAL(10, 2) NOT NULL,
                category_id INTEGER REFERENCES categories(category_id)
            );

            CREATE TABLE customers (
                customer_id SERIAL PRIMARY KEY,
                first_name VARCHAR(50) NOT NULL,
                last_name VARCHAR(50) NOT NULL,
                email VARCHAR(100) NOT NULL,
                country VARCHAR(50)
            );

            CREATE TABLE orders (
                order_id SERIAL PRIMARY KEY,
                customer_id INTEGER REFERENCES customers(customer_id),
                total_amount DECIMAL(10, 2) NOT NULL
            );

            CREATE TABLE order_items (
                order_item_id SERIAL PRIMARY KEY,
                order_id INTEGER REFERENCES orders(order_id),
                product_id INTEGER REFERENCES products(product_id),
                quantity INTEGER NOT NULL,
                unit_price DECIMAL(10, 2) NOT NULL
            );
        """)

        print("Inserting seed data for tests...")
        cursor.execute("""
            INSERT INTO categories (name) VALUES 
                ('Electronics'), 
                ('Office Supplies'), 
                ('Apparel');
                
            INSERT INTO products (name, price, category_id) VALUES 
                ('Laptop', 1200.00, 1), 
                ('Desk', 299.50, 2);
                
            INSERT INTO customers (first_name, last_name, email, country) VALUES 
                ('John', 'Doe', 'john@example.com', 'USA'),
                ('Jane', 'Smith', 'jane@example.com', 'Canada');
                
            INSERT INTO orders (customer_id, total_amount) VALUES 
                (1, 1499.50),
                (2, 299.50);
        """)

        print("✅ Database initialized successfully!")
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    initialize_database()