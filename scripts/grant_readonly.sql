GRANT CONNECT ON DATABASE ecommerce TO readonly_user;

GRANT USAGE ON SCHEMA public TO readonly_user;

REVOKE ALL ON ALL TABLES IN SCHEMA public FROM readonly_user;

REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM readonly_user;

GRANT SELECT ON TABLE 
  olist_geolocation, 
  olist_customers, 
  olist_order_items, 
  olist_order_payments, 
  olist_orders, 
  olist_products, 
  olist_sellers 
TO readonly_user;