import pandas as pd
from rapidfuzz import process, fuzz
import unicodedata
import os
import re
from datetime import datetime

PRODUCTS_FILE = 'products.csv'
ORDERS_FILE = 'manual_orders.csv'
OUTPUT_FOLDER = 'purchase_orders'
FUZZY_MATCH_THRESHOLD = 70  

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def normalize_product_name(name):
    if pd.isna(name):
        return ""
    cleaned = ' '.join(str(name).replace('\n', ' ').split()).strip().lower()
    cleaned = re.sub(r'[^\w\s]', '', cleaned)
    return unicodedata.normalize('NFKD', cleaned).encode('ASCII', 'ignore').decode()

def match_product(order_name, product_names):
    normalized_products = product_names.apply(normalize_product_name)
    normalized_order = normalize_product_name(order_name)

    match, score, _ = process.extractOne(
        normalized_order,
        normalized_products,
        scorer=fuzz.token_set_ratio
    )

    print(f"Matching '{order_name}' → '{match}' with score {score}")

    if score >= FUZZY_MATCH_THRESHOLD:
        return product_names[normalized_products == match].values[0]
    else:
        return None

products_df = pd.read_csv(PRODUCTS_FILE)

with open(ORDERS_FILE, 'r', encoding='utf-8-sig') as f:
    lines = f.readlines()

order_number = lines[0].strip().split(',')[1]
delivery_date = lines[1].strip().split(',')[1]

orders_df = pd.read_csv(ORDERS_FILE, skiprows=4)

products_df.columns = products_df.columns.str.strip()
orders_df.columns = orders_df.columns.str.strip()

products_df.rename(columns={
    'ID': 'ProductID',
    'Nom': 'ProductName',
    'Fournisseurs': 'Supplier',
    'Catégorie de produits/Nom': 'Category',
    'Prix de vente': 'Unit Price'
}, inplace=True)

matched_rows = []

for idx, order_row in orders_df.iterrows():
    raw_name = order_row['Name']
    quantity = order_row['Quantity']
    comment = order_row.get('Comments', '')

    matched_name = match_product(raw_name, products_df['ProductName'])

    if matched_name:
        matched_product = products_df[products_df['ProductName'] == matched_name].iloc[0]
        matched_rows.append({
            'ProductID': matched_product['ProductID'],
            'ProductName': matched_product['ProductName'],
            'Quantity': quantity,
            'Supplier': matched_product['Supplier'],
            'Category': matched_product.get('Category', ''),
            'Unit Price': matched_product.get('Unit Price', 0.0),
            'Comments': comment
        })
        print(f"[✅] Matched: '{raw_name}' → '{matched_name}'")
    else:
        print(f"[⚠️] No match found for: '{raw_name}'")

final_df = pd.DataFrame(matched_rows)

if final_df.empty:
    print("[❌] No matches were found. Please check the input data.")
else:
    today_str = datetime.today().strftime('%d/%m/%Y')

    for supplier, group in final_df.groupby('Supplier'):
        safe_supplier = supplier.replace(' ', '_').replace('/', '_')
        filename = f"PO_{order_number}_{safe_supplier}.csv"
        output_path = os.path.join(OUTPUT_FOLDER, filename)

    
        header_rows = [
            ['Client:', 'Froggy Gourmet'],
            ['Order Number:', order_number],
            ['Date Created:', today_str],
            ['Delivery Date:', delivery_date],
            ['Supplier:', supplier],
            [],
            []
        ]

        product_table = group[['ProductID', 'ProductName', 'Quantity', 'Comments']]

        with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
            for row in header_rows:
                f.write(','.join(map(str, row)) + '\n')
            product_table.to_csv(f, index=False)

        print(f"[📦] Written: {output_path}")

    quote_df = final_df[['ProductID', 'ProductName', 'Category', 'Quantity', 'Unit Price']].copy()

    quote_df['Quantity'] = pd.to_numeric(quote_df['Quantity'], errors='coerce')
    quote_df['Unit Price'] = pd.to_numeric(quote_df['Unit Price'], errors='coerce')

    quote_df['Total Price'] = quote_df['Quantity'] * quote_df['Unit Price']

    quote_df[['Unit Price', 'Total Price']] = quote_df[['Unit Price', 'Total Price']].round(2)

    grand_total = quote_df['Total Price'].sum().round(2)

    total_row = pd.DataFrame([{
        'ProductID': '',
        'ProductName': 'TOTAL (€)',
        'Category': '',
        'Quantity': '',
        'Unit Price (€)': '',
        'Total Price (€)': grand_total
    }])

    quote_df = pd.concat([quote_df, total_row], ignore_index=True)

    quote_output_path = os.path.join(OUTPUT_FOLDER, f"Quote_{order_number}.csv")
    quote_df.to_csv(quote_output_path, index=False)

    print(f"[📄] Quote CSV created: {quote_output_path}")
