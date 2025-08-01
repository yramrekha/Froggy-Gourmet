import pandas as pd
from rapidfuzz import process, fuzz
import unicodedata
import os
import re
from datetime import datetime
from langdetect import detect
import argostranslate.translate

# --- CONFIGURATION ---
PRODUCTS_FILE = 'products.csv'
ORDERS_FILE = 'manual_orders.csv'
OUTPUT_FOLDER = 'purchase_orders'
FUZZY_MATCH_THRESHOLD = 70

# --- Setup ---
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# --- Translation Function ---
def translate_comment(comment):
    if pd.isna(comment) or str(comment).strip() == "":
        return ""
    
    try:
        comment_str = str(comment).strip()

        # Detect language
        detected_lang = detect(comment_str)
        if detected_lang != 'en':
            print(f"[🌐] Skipping non-English comment: '{comment_str}' (lang: {detected_lang})")
            return comment_str

        # Translate English to French
        installed_languages = argostranslate.translate.get_installed_languages()
        from_lang = next(filter(lambda x: x.code == "en", installed_languages), None)
        to_lang = next(filter(lambda x: x.code == "fr", installed_languages), None)

        if from_lang and to_lang:
            translation = from_lang.get_translation(to_lang)
            translated = translation.translate(comment_str)
            print(f"[🔁] Translated: '{comment_str}' → '{translated}'")
            return translated
        else:
            print("[⚠️] Language models not found.")
            return comment_str

    except Exception as e:
        print(f"[❌] Translation error for '{comment}': {e}")
        return comment

# --- Name normalization ---
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

    print(f"Matching '{order_name}' → '{match}' (score: {score})")

    if score >= FUZZY_MATCH_THRESHOLD:
        return product_names[normalized_products == match].values[0]
    else:
        return None

# --- Load Data ---
products_df = pd.read_csv(PRODUCTS_FILE)

# Read first few lines manually to get order number and delivery date
with open(ORDERS_FILE, 'r', encoding='utf-8-sig') as f:
    lines = f.readlines()

order_number = lines[0].strip().split(',')[1]
delivery_date = lines[1].strip().split(',')[1]

# Load the product list starting at row 4
orders_df = pd.read_csv(ORDERS_FILE, skiprows=4)

# Clean column names
products_df.columns = products_df.columns.str.strip()
orders_df.columns = orders_df.columns.str.strip()

# Standardize product column names
products_df.rename(columns={
    'ID': 'ProductID',
    'Nom': 'ProductName',
    'Fournisseurs': 'Supplier'
}, inplace=True)

# --- Match Orders ---
matched_rows = []

for idx, order_row in orders_df.iterrows():
    raw_name = order_row['Name']
    quantity = order_row['Quantity']
    raw_comment = order_row.get('Comments', '')
    comment = translate_comment(raw_comment)

    matched_name = match_product(raw_name, products_df['ProductName'])

    if matched_name:
        matched_product = products_df[products_df['ProductName'] == matched_name].iloc[0]
        matched_rows.append({
            'ProductID': matched_product['ProductID'],
            'ProductName': matched_product['ProductName'],
            'Quantity': quantity,
            'Supplier': matched_product['Supplier'],
            'Comments': comment
        })
        print(f"[✅] Matched: '{raw_name}' → '{matched_name}'")
    else:
        print(f"[⚠️] No match found for: '{raw_name}'")

# --- Output per Supplier ---
final_df = pd.DataFrame(matched_rows)

if final_df.empty:
    print("[❌] No matches were found. Please check the input data.")
else:
    today_str = datetime.today().strftime('%d/%m/%Y')

    for supplier, group in final_df.groupby('Supplier'):
        safe_supplier = supplier.replace(' ', '_').replace('/', '_')
        filename = f"PO_{order_number}_{safe_supplier}.csv"
        output_path = os.path.join(OUTPUT_FOLDER, filename)

        # Write header info
        header_rows = [
            ['Client:', 'Froggy Gourmet'],
            ['Order Number:', order_number],
            ['Date Created:', today_str],
            ['Delivery Date:', delivery_date],
            ['Supplier:', supplier],
            [],
            []
        ]

        # Remove Supplier from table
        product_table = group[['ProductID', 'ProductName', 'Quantity', 'Comments']]

        with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
            for row in header_rows:
                f.write(','.join(map(str, row)) + '\n')
            product_table.to_csv(f, index=False)

        print(f"[📦] Written: {output_path}")
