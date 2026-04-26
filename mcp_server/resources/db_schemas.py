from mcp_server.server import mcp

@mcp.resource("db://olist_schema")
def get_olist_schemas():
    return """
Database: Olist E-commerce

Tables:

1. olist_orders
- order_id (PK, string)
- customer_id (FK → olist_customers.customer_id)
- order_status (string)
- order_purchase_timestamp (datetime)
- order_approved_at (datetime, nullable)
- order_delivered_carrier_date (datetime, nullable)
- order_delivered_customer_date (datetime, nullable)
- order_estimated_delivery_date (datetime, nullable)

2. olist_order_items
- order_id (PK, FK → olist_orders.order_id)
- order_item_id (PK, int)
- product_id (FK → olist_products.product_id)
- seller_id (FK → olist_sellers.seller_id)
- shipping_limit_date (datetime)
- price (float)
- freight_value (float)

3. olist_order_payments
- order_id (PK, FK → olist_orders.order_id)
- payment_sequential (PK, int)
- payment_type (string)
- payment_installments (int)
- payment_value (float)

4. olist_customers
- customer_id (PK, string)
- customer_unique_id (string)
- customer_zip_code_prefix (string)
- customer_city (string)
- customer_state (string)

5. olist_sellers
- seller_id (PK, string)
- seller_zip_code_prefix (string)
- seller_city (string)
- seller_state (string)

6. olist_geolocation
- id (PK, int)
- geolocation_zip_code_prefix (string)
- geolocation_lat (float)
- geolocation_lng (float)
- geolocation_city (string)
- geolocation_state (string)

Relationships:

- orders.customer_id → customers.customer_id
- order_items.order_id → orders.order_id
- order_items.seller_id → sellers.seller_id
- order_payments.order_id → orders.order_id

Business Notes:

- Revenue = SUM(payment_value) from olist_order_payments
- Order value can also be approximated via SUM(price + freight_value) from olist_order_items
- Use DATE_TRUNC('month', order_purchase_timestamp) for monthly aggregation
- Join orders ↔ payments ↔ items for full analysis

Guidelines for SQL:
- Always use explicit JOIN
- Prefer aggregations on payment_value for revenue
- Limit results when exploring (LIMIT 100)
"""