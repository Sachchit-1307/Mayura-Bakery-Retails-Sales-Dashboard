MAYURA BAKERY — RETAIL SALES DASHBOARD & MANAGEMENT SYSTEM
Designed & Developed by A Sachchit

PROJECT FILES
-------------
main.py          Main Tkinter desktop application
products.csv     Product catalogue and current stock
sales.csv        Saved sales transactions
requirements.txt Third-party Python packages
README.txt       Setup and user guide

TECHNOLOGIES
------------
Python, Tkinter/ttk, Pandas, Matplotlib (TkAgg), CSV files.
No database and no web server are used.

WINDOWS + VS CODE SETUP
-----------------------
1. Install Python 3.10 or newer from https://www.python.org/downloads/
   During installation, enable "Add Python to PATH".
2. Open the MayuraBakery folder in VS Code.
3. Open Terminal > New Terminal.
4. (Optional but recommended) Create a virtual environment:
       py -m venv .venv
       .venv\Scripts\activate
5. Install dependencies:
       py -m pip install -r requirements.txt
6. Run the application:
       py main.py

If the `py` command is unavailable, use `python` instead.

INITIAL CATALOGUE
-----------------
products.csv was created from the uploaded bengaluru_bakery_inventory.xlsx
workbook, sheet "Bakery Inventory". The workbook contained 50 products and
these columns: Product name, Category, Selling price (₹), Current stock
quantity, Low-stock threshold. Product IDs MB001–MB050 were assigned because
the workbook did not include Product IDs. No product prices or quantities
were invented. sales.csv starts empty because the workbook contained no sales.

HOW TO USE
----------
Dashboard:
- Shows revenue, number of transactions, units sold and average transaction.
- Use YYYY-MM-DD dates and category filter, then press Apply.
- Charts and insights are calculated from saved sales.

Products:
- Add a product by entering a unique ID, name, category, price, stock and
  low-stock threshold, then click Add Product.
- Select a row to load it into the form; change details and click Update Selected.
- Search and filter by category.
- If a product has sales history, Delete / Deactivate marks it inactive instead
  of permanently deleting it.

Sales:
- Choose an active product. Its current price fills automatically.
- Enter date and a positive whole-number quantity, then record the sale.
- The program checks stock and only saves the transaction after validation.

Sales Records:
- Search/filter records and use YYYY-MM-DD date ranges.
- Edit a sale to correct its date, quantity or transaction unit price.
- Deleting a sale returns its quantity to stock.
- Import/export CSV files using the provided buttons.

CSV FORMAT
----------
products.csv columns:
product_id, product_name, category, price, stock, low_stock_threshold, active

sales.csv columns:
sale_id, sale_date, product_id, product_name, category, quantity, unit_price, total_amount

IMPORTANT NOTES
---------------
- Keep products.csv and sales.csv in the same folder as main.py.
- Make a backup copy of both CSV files before manually editing or importing data.
- Sales history stores product name, category and unit price at transaction time.
- Revenue is sales revenue, not profit. Purchase costs are not tracked.
- Imported product CSVs need unique product_id values and the documented columns
  or the original workbook's column names. Missing IDs are not automatically
  guessed during import.
- Imported sales require the documented sales columns, unique sale IDs, existing
  product IDs, and enough stock. Import validation runs before saving.
