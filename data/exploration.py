from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
file_path = BASE_DIR / "ecommerce_data" / "olist_customers_dataset.csv"

df = pd.read_csv(file_path)

dup_mask = df["customer_unique_id"].duplicated(keep=False)
duplicates = df[dup_mask].sort_values("customer_unique_id")

print(duplicates.head(20))