"""
Mayura Bakery — Retail Sales Dashboard & Management System
Developed by A Sachchit

Beginner-friendly desktop application using Tkinter, Pandas, Matplotlib and CSV.
Run: python main.py
"""

import csv
import os
import shutil
import tempfile
from datetime import date, datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import pandas as pd
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


APP_TITLE = "Mayura Bakery — Retail Sales Dashboard & Management System"
BASE_DIR = Path(__file__).resolve().parent
PRODUCTS_FILE = BASE_DIR / "products.csv"
SALES_FILE = BASE_DIR / "sales.csv"

PRODUCT_COLUMNS = [
    "product_id", "product_name", "category", "price", "stock",
    "low_stock_threshold", "active"
]
SALE_COLUMNS = [
    "sale_id", "sale_date", "product_id", "product_name", "category",
    "quantity", "unit_price", "total_amount"
]
MONEY = "₹{:,.2f}"
COLORS = {
    "cream": "#F7F2E8",
    "paper": "#FFFCF6",
    "brown": "#624631",
    "brown_dark": "#3E2B20",
    "green": "#6F8061",
    "green_dark": "#526447",
    "muted": "#817568",
    "line": "#DCCFBC",
    "warning": "#A94F35",
    "white": "#FFFFFF",
}


def ensure_csv_files():
    """Create the required CSV files with headers if they do not exist."""
    if not PRODUCTS_FILE.exists():
        pd.DataFrame(columns=PRODUCT_COLUMNS).to_csv(PRODUCTS_FILE, index=False)
    if not SALES_FILE.exists():
        pd.DataFrame(columns=SALE_COLUMNS).to_csv(SALES_FILE, index=False)


def read_csv_safely(path, required_columns):
    """Load a CSV and show a clear error if it cannot be read safely."""
    try:
        frame = pd.read_csv(path, dtype=str, keep_default_na=False)
        missing = [column for column in required_columns if column not in frame.columns]
        if missing:
            raise ValueError("Missing required column(s): " + ", ".join(missing))
        return frame[required_columns].copy()
    except pd.errors.EmptyDataError:
        raise ValueError(f"{path.name} is empty or has no header row.")
    except (OSError, UnicodeError, pd.errors.ParserError) as exc:
        raise ValueError(f"Could not read {path.name}: {exc}")


def clean_products(frame):
    """Validate product CSV data and return normalized values."""
    result = frame.copy()
    for column in PRODUCT_COLUMNS:
        if column not in result.columns:
            raise ValueError(f"Products data is missing column: {column}")
    result = result[PRODUCT_COLUMNS].fillna("")
    if result.empty:
        return pd.DataFrame(columns=PRODUCT_COLUMNS)

    result["product_id"] = result["product_id"].astype(str).str.strip()
    result["product_name"] = result["product_name"].astype(str).str.strip()
    result["category"] = result["category"].astype(str).str.strip()
    if (result["product_id"] == "").any() or result["product_id"].duplicated().any():
        raise ValueError("Product IDs must be present and unique.")
    if (result["product_name"] == "").any():
        raise ValueError("Every product needs a name.")
    if (result["category"] == "").any():
        raise ValueError("Every product needs a category.")
    result["price"] = pd.to_numeric(result["price"], errors="raise")
    result["stock"] = pd.to_numeric(result["stock"], errors="raise")
    result["low_stock_threshold"] = pd.to_numeric(result["low_stock_threshold"], errors="raise")
    if (result["price"] < 0).any():
        raise ValueError("Product prices cannot be negative.")
    for col in ["stock", "low_stock_threshold"]:
        if (result[col] < 0).any() or ((result[col] % 1) != 0).any():
            raise ValueError(f"{col} must contain non-negative whole numbers.")
    result["stock"] = result["stock"].astype(int)
    result["low_stock_threshold"] = result["low_stock_threshold"].astype(int)
    result["active"] = result["active"].astype(str).str.strip().str.lower().map(
        lambda value: "False" if value in ("false", "0", "no", "inactive") else "True"
    )
    return result


def clean_sales(frame):
    """Validate sales CSV data and return normalized values."""
    result = frame.copy()
    for column in SALE_COLUMNS:
        if column not in result.columns:
            raise ValueError(f"Sales data is missing column: {column}")
    result = result[SALE_COLUMNS].fillna("")
    if result.empty:
        return pd.DataFrame(columns=SALE_COLUMNS)
    result["sale_id"] = result["sale_id"].astype(str).str.strip()
    if (result["sale_id"] == "").any() or result["sale_id"].duplicated().any():
        raise ValueError("Sale IDs must be present and unique.")
    dates = pd.to_datetime(result["sale_date"], errors="coerce")
    if dates.isna().any():
        raise ValueError("Sales contain invalid dates. Use YYYY-MM-DD.")
    result["sale_date"] = dates.dt.strftime("%Y-%m-%d")
    for col in ["product_id", "product_name", "category"]:
        result[col] = result[col].astype(str).str.strip()
    if (result["product_name"] == "").any():
        raise ValueError("Every sale needs a product name.")
    result["quantity"] = pd.to_numeric(result["quantity"], errors="raise")
    result["unit_price"] = pd.to_numeric(result["unit_price"], errors="raise")
    result["total_amount"] = pd.to_numeric(result["total_amount"], errors="raise")
    if (result["quantity"] <= 0).any() or ((result["quantity"] % 1) != 0).any():
        raise ValueError("Sale quantities must be positive whole numbers.")
    if (result["unit_price"] < 0).any() or (result["total_amount"] < 0).any():
        raise ValueError("Sale prices and totals cannot be negative.")
    result["quantity"] = result["quantity"].astype(int)
    # Use the saved unit price and quantity as the source of truth for totals.
    result["total_amount"] = (result["quantity"] * result["unit_price"]).round(2)
    return result


def atomic_save(frame, path):
    """Write to a temporary file first, then replace the target CSV."""
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", newline="", encoding="utf-8-sig",
            dir=path.parent, delete=False, suffix=".tmp"
        ) as temp_file:
            temp_name = temp_file.name
            frame.to_csv(temp_file, index=False)
        os.replace(temp_name, path)
    except Exception:
        if temp_name and os.path.exists(temp_name):
            try:
                os.remove(temp_name)
            except OSError:
                pass
        raise


class MayuraBakeryApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1450x900")
        self.root.minsize(1120, 720)
        self.root.configure(bg=COLORS["cream"])

        ensure_csv_files()
        try:
            self.products = clean_products(read_csv_safely(PRODUCTS_FILE, PRODUCT_COLUMNS))
            self.sales = clean_sales(read_csv_safely(SALES_FILE, SALE_COLUMNS))
        except Exception as exc:
            messagebox.showerror(
                "CSV data problem",
                f"{exc}\n\nFix the CSV file and restart the application. "
                "The original file has not been overwritten."
            )
            self.products = pd.DataFrame(columns=PRODUCT_COLUMNS)
            self.sales = pd.DataFrame(columns=SALE_COLUMNS)

        self.selected_product_id = None
        self.selected_sale_id = None
        self._build_style()
        self._build_header()
        self._build_tabs()
        self.refresh_all()

    # ------------------------- Styling and layout -------------------------
    def _build_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(".", font=("Segoe UI", 10))
        style.configure("TFrame", background=COLORS["cream"])
        style.configure("Card.TFrame", background=COLORS["paper"], relief="flat")
        style.configure("TLabel", background=COLORS["cream"], foreground=COLORS["brown_dark"])
        style.configure("Heading.TLabel", font=("Segoe UI", 17, "bold"), foreground=COLORS["brown_dark"])
        style.configure("Subheading.TLabel", font=("Segoe UI", 11, "bold"), foreground=COLORS["brown"])
        style.configure("TButton", padding=(11, 7), background=COLORS["green"], foreground="white")
        style.map("TButton", background=[("active", COLORS["green_dark"])])
        style.configure("Accent.TButton", padding=(12, 8), background=COLORS["brown"], foreground="white")
        style.map("Accent.TButton", background=[("active", COLORS["brown_dark"])])
        style.configure("Treeview", background=COLORS["paper"], fieldbackground=COLORS["paper"],
                        foreground=COLORS["brown_dark"], rowheight=27)
        style.configure("Treeview.Heading", background="#E9DFCE", foreground=COLORS["brown_dark"],
                        font=("Segoe UI", 10, "bold"))
        style.map("Treeview", background=[("selected", "#D8E0CE")],
                  foreground=[("selected", COLORS["brown_dark"])])
        style.configure("TNotebook", background=COLORS["cream"], borderwidth=0)
        style.configure("TNotebook.Tab", padding=(18, 10), background="#E9DFCE")
        style.map("TNotebook.Tab", background=[("selected", COLORS["paper"])],
                  foreground=[("selected", COLORS["brown_dark"])])

    def _build_header(self):
        header = tk.Frame(self.root, bg=COLORS["brown_dark"], padx=22, pady=15)
        header.pack(fill="x")
        left = tk.Frame(header, bg=COLORS["brown_dark"])
        left.pack(side="left", fill="x", expand=True)
        tk.Label(left, text="MAYURA BAKERY", bg=COLORS["brown_dark"], fg="#FFF8EB",
                 font=("Segoe UI", 22, "bold")).pack(anchor="w")
        tk.Label(left, text="Retail Sales Dashboard & Management System",
                 bg=COLORS["brown_dark"], fg="#E8D9C5",
                 font=("Segoe UI", 10)).pack(anchor="w", pady=(2, 0))
        tk.Label(header, text="BAKERY MANAGEMENT  •  CSV + PYTHON",
                 bg=COLORS["brown_dark"], fg="#D9C7AE",
                 font=("Segoe UI", 9, "bold")).pack(side="right", anchor="e")

    def _build_tabs(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=16, pady=(12, 6))

        self.dashboard_tab = ttk.Frame(self.notebook, padding=12)
        self.products_tab = ttk.Frame(self.notebook, padding=12)
        self.sales_tab = ttk.Frame(self.notebook, padding=12)
        self.records_tab = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.dashboard_tab, text="Dashboard")
        self.notebook.add(self.products_tab, text="Products")
        self.notebook.add(self.sales_tab, text="Sales")
        self.notebook.add(self.records_tab, text="Sales Records")

        self._build_dashboard_tab()
        self._build_products_tab()
        self._build_sales_tab()
        self._build_records_tab()

        footer = tk.Frame(self.root, bg=COLORS["cream"], padx=20, pady=7)
        footer.pack(fill="x")
        tk.Label(footer, text="Designed & Developed by A Sachchit",
                 bg=COLORS["cream"], fg=COLORS["brown"],
                 font=("Segoe UI", 10, "bold")).pack(side="right")

    # ------------------------- Shared helpers -------------------------
    def _label(self, parent, text, row, column, **kwargs):
        ttk.Label(parent, text=text).grid(row=row, column=column, sticky="w", padx=5, pady=5, **kwargs)

    def _entry(self, parent, variable, row, column, width=24, **kwargs):
        entry = ttk.Entry(parent, textvariable=variable, width=width, **kwargs)
        entry.grid(row=row, column=column, sticky="ew", padx=5, pady=5)
        return entry

    def _make_tree(self, parent, columns, headings, widths=None, height=12):
        container = ttk.Frame(parent)
        container.pack(fill="both", expand=True)
        tree = ttk.Treeview(container, columns=columns, show="headings", height=height)
        yscroll = ttk.Scrollbar(container, orient="vertical", command=tree.yview)
        xscroll = ttk.Scrollbar(container, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)
        for i, column in enumerate(columns):
            tree.heading(column, text=headings[i])
            tree.column(column, width=(widths[i] if widths else 120), anchor="w")
        tree.tag_configure("low", foreground=COLORS["warning"])
        return tree

    def _product_row(self, product_id):
        matches = self.products[self.products["product_id"] == product_id]
        return None if matches.empty else matches.iloc[0]

    def _active_products(self):
        if self.products.empty:
            return self.products.copy()
        return self.products[self.products["active"] == "True"].copy()

    def _next_id(self, prefix, existing, width=4):
        numbers = []
        for value in existing:
            text = str(value)
            if text.startswith(prefix):
                suffix = text[len(prefix):]
                if suffix.isdigit():
                    numbers.append(int(suffix))
        return f"{prefix}{max(numbers, default=0) + 1:0{width}d}"

    def _save_pair(self, new_products, new_sales):
        """Save related CSV changes together as safely as practical."""
        product_temp = PRODUCTS_FILE.with_suffix(".csv.pending")
        sales_temp = SALES_FILE.with_suffix(".csv.pending")
        product_backup = PRODUCTS_FILE.with_suffix(".csv.backup")
        sales_backup = SALES_FILE.with_suffix(".csv.backup")
        try:
            new_products[PRODUCT_COLUMNS].to_csv(product_temp, index=False, encoding="utf-8-sig")
            new_sales[SALE_COLUMNS].to_csv(sales_temp, index=False, encoding="utf-8-sig")
            shutil.copy2(PRODUCTS_FILE, product_backup)
            shutil.copy2(SALES_FILE, sales_backup)
            os.replace(product_temp, PRODUCTS_FILE)
            try:
                os.replace(sales_temp, SALES_FILE)
            except Exception:
                shutil.copy2(product_backup, PRODUCTS_FILE)
                raise
        except Exception:
            if product_temp.exists():
                product_temp.unlink()
            if sales_temp.exists():
                sales_temp.unlink()
            raise
        finally:
            for backup in (product_backup, sales_backup):
                if backup.exists():
                    backup.unlink()

    def _commit(self, new_products=None, new_sales=None):
        products = clean_products(new_products if new_products is not None else self.products)
        sales = clean_sales(new_sales if new_sales is not None else self.sales)
        # Ensure every saved sale total agrees with its saved quantity and unit price.
        self._save_pair(products, sales)
        self.products, self.sales = products, sales
        self.refresh_all()

    def refresh_all(self):
        self.refresh_products_table()
        self.refresh_product_dropdowns()
        self.refresh_sales_table()
        self.refresh_dashboard()

    # ------------------------- Products tab -------------------------
    def _build_products_tab(self):
        ttk.Label(self.products_tab, text="Product Catalogue", style="Heading.TLabel").pack(anchor="w", pady=(0, 8))
        form = ttk.LabelFrame(self.products_tab, text="Product details", padding=10)
        form.pack(fill="x", pady=(0, 10))
        self.p_id = tk.StringVar()
        self.p_name = tk.StringVar()
        self.p_category = tk.StringVar()
        self.p_price = tk.StringVar()
        self.p_stock = tk.StringVar()
        self.p_threshold = tk.StringVar(value="5")
        self.p_active = tk.BooleanVar(value=True)

        fields = [
            ("Product ID", self.p_id), ("Product Name", self.p_name),
            ("Category", self.p_category), ("Selling Price (₹)", self.p_price),
            ("Current Stock", self.p_stock), ("Low-stock Threshold", self.p_threshold)
        ]
        for index, (label, variable) in enumerate(fields):
            row, col = divmod(index, 3)
            self._label(form, label, row * 2, col)
            self._entry(form, variable, row * 2 + 1, col, width=27)
        ttk.Checkbutton(form, text="Active product", variable=self.p_active).grid(
            row=4, column=0, sticky="w", padx=5, pady=5)
        buttons = ttk.Frame(form)
        buttons.grid(row=4, column=1, columnspan=2, sticky="e", padx=5, pady=5)
        ttk.Button(buttons, text="Add Product", style="Accent.TButton", command=self.add_product).pack(side="left", padx=3)
        ttk.Button(buttons, text="Update Selected", command=self.update_product).pack(side="left", padx=3)
        ttk.Button(buttons, text="Delete / Deactivate", command=self.delete_product).pack(side="left", padx=3)
        ttk.Button(buttons, text="Clear Form", command=self.clear_product_form).pack(side="left", padx=3)

        tools = ttk.Frame(self.products_tab)
        tools.pack(fill="x", pady=(0, 8))
        self.product_search = tk.StringVar()
        self.product_category_filter = tk.StringVar(value="All categories")
        ttk.Label(tools, text="Search").pack(side="left", padx=(0, 5))
        search_entry = ttk.Entry(tools, textvariable=self.product_search, width=28)
        search_entry.pack(side="left", padx=(0, 12))
        search_entry.bind("<KeyRelease>", lambda _event: self.refresh_products_table())
        ttk.Label(tools, text="Category").pack(side="left", padx=(0, 5))
        self.product_category_combo = ttk.Combobox(tools, textvariable=self.product_category_filter,
                                                    state="readonly", width=23)
        self.product_category_combo.pack(side="left")
        self.product_category_combo.bind("<<ComboboxSelected>>", lambda _event: self.refresh_products_table())
        ttk.Button(tools, text="Import Products CSV", command=self.import_products).pack(side="right", padx=3)
        ttk.Button(tools, text="Export Products CSV", command=self.export_products).pack(side="right", padx=3)

        columns = ("product_id", "product_name", "category", "price", "stock", "threshold", "active", "status")
        headings = ("Product ID", "Product Name", "Category", "Price", "Stock", "Low-stock At", "Active", "Stock Status")
        widths = (95, 210, 165, 95, 75, 95, 75, 115)
        self.products_tree = self._make_tree(self.products_tab, columns, headings, widths, height=12)
        self.products_tree.bind("<<TreeviewSelect>>", self.on_product_select)

    def clear_product_form(self):
        self.selected_product_id = None
        for variable in (self.p_id, self.p_name, self.p_category, self.p_price, self.p_stock):
            variable.set("")
        self.p_threshold.set("5")
        self.p_active.set(True)
        self.p_id.set(self._next_id("MB", self.products["product_id"].tolist(), 3))
        self.products_tree.selection_remove(self.products_tree.selection())

    def _validate_product_form(self):
        product_id = self.p_id.get().strip()
        name = self.p_name.get().strip()
        category = self.p_category.get().strip()
        if not product_id or not name or not category:
            raise ValueError("Product ID, product name and category are required.")
        try:
            price = float(self.p_price.get())
            stock = int(self.p_stock.get())
            threshold = int(self.p_threshold.get())
        except ValueError:
            raise ValueError("Price must be numeric; stock and threshold must be whole numbers.")
        if price < 0:
            raise ValueError("Price cannot be negative.")
        if stock < 0 or threshold < 0:
            raise ValueError("Stock and low-stock threshold cannot be negative.")
        if not self.p_stock.get().strip() or str(stock) != self.p_stock.get().strip():
            raise ValueError("Stock must be a non-negative whole number.")
        if not self.p_threshold.get().strip() or str(threshold) != self.p_threshold.get().strip():
            raise ValueError("Low-stock threshold must be a non-negative whole number.")
        if not product_id.replace("-", "").replace("_", "").isalnum():
            raise ValueError("Product ID may contain letters, numbers, hyphens and underscores.")
        return {
            "product_id": product_id, "product_name": name, "category": category,
            "price": round(price, 2), "stock": stock, "low_stock_threshold": threshold,
            "active": "True" if self.p_active.get() else "False"
        }

    def add_product(self):
        try:
            item = self._validate_product_form()
            if item["product_id"] in self.products["product_id"].tolist():
                raise ValueError("That Product ID already exists. Choose a unique ID.")
            if not self.products.empty and item["product_name"].casefold() in self.products["product_name"].str.casefold().tolist():
                if not messagebox.askyesno("Similar product name", "A product with this name already exists. Add another anyway?"):
                    return
            new_products = pd.concat([self.products, pd.DataFrame([item])], ignore_index=True)
            self._commit(new_products, self.sales)
            messagebox.showinfo("Product added", f"{item['product_name']} was added successfully.")
            self.clear_product_form()
        except Exception as exc:
            messagebox.showerror("Could not add product", str(exc))

    def update_product(self):
        try:
            if not self.selected_product_id:
                raise ValueError("Select a product from the table first.")
            item = self._validate_product_form()
            if item["product_id"] != self.selected_product_id and item["product_id"] in self.products["product_id"].tolist():
                raise ValueError("That Product ID already exists.")
            old = self._product_row(self.selected_product_id)
            if old is None:
                raise ValueError("The selected product no longer exists.")
            # Stock may be changed only by the amount already in stock; sales history stays unchanged.
            new_products = self.products.copy()
            index = new_products.index[new_products["product_id"] == self.selected_product_id][0]
            for column in PRODUCT_COLUMNS:
                new_products.at[index, column] = item[column]
            # Update product ID references for future reconciliation, but keep historical names/prices.
            if item["product_id"] != self.selected_product_id:
                new_sales = self.sales.copy()
                new_sales.loc[new_sales["product_id"] == self.selected_product_id, "product_id"] = item["product_id"]
            else:
                new_sales = self.sales.copy()
            self._commit(new_products, new_sales)
            messagebox.showinfo("Product updated", "Product details were updated. Historical sale names and prices were preserved.")
            self.clear_product_form()
        except Exception as exc:
            messagebox.showerror("Could not update product", str(exc))

    def delete_product(self):
        if not self.selected_product_id:
            messagebox.showerror("Select a product", "Select a product from the table first.")
            return
        product_id = self.selected_product_id
        has_sales = not self.sales.empty and (self.sales["product_id"] == product_id).any()
        product = self._product_row(product_id)
        if product is None:
            return
        if has_sales:
            if not messagebox.askyesno("Historical sales exist",
                f"{product['product_name']} has historical sales.\n\n"
                "It cannot be permanently deleted. Mark it inactive instead?"):
                return
            new_products = self.products.copy()
            new_products.loc[new_products["product_id"] == product_id, "active"] = "False"
            try:
                self._commit(new_products, self.sales)
                messagebox.showinfo("Product deactivated", "The product is now inactive. Historical sales are preserved.")
            except Exception as exc:
                messagebox.showerror("Could not deactivate", str(exc))
        else:
            if not messagebox.askyesno("Confirm deletion", f"Permanently delete {product['product_name']}?"):
                return
            new_products = self.products[self.products["product_id"] != product_id].copy()
            try:
                self._commit(new_products, self.sales)
                messagebox.showinfo("Product deleted", "Product deleted.")
            except Exception as exc:
                messagebox.showerror("Could not delete product", str(exc))
        self.clear_product_form()

    def on_product_select(self, _event=None):
        selection = self.products_tree.selection()
        if not selection:
            return
        values = self.products_tree.item(selection[0], "values")
        self.selected_product_id = values[0]
        item = self._product_row(self.selected_product_id)
        if item is None:
            return
        self.p_id.set(item["product_id"])
        self.p_name.set(item["product_name"])
        self.p_category.set(item["category"])
        self.p_price.set(str(item["price"]))
        self.p_stock.set(str(item["stock"]))
        self.p_threshold.set(str(item["low_stock_threshold"]))
        self.p_active.set(item["active"] == "True")

    def refresh_products_table(self):
        if not hasattr(self, "products_tree"):
            return
        for row in self.products_tree.get_children():
            self.products_tree.delete(row)
        search = self.product_search.get().strip().casefold()
        category = self.product_category_filter.get()
        categories = sorted(self.products["category"].dropna().astype(str).unique().tolist()) if not self.products.empty else []
        if hasattr(self, "product_category_combo"):
            self.product_category_combo["values"] = ["All categories"] + categories
            if category not in ["All categories"] + categories:
                self.product_category_filter.set("All categories")
                category = "All categories"
        view = self.products.copy()
        if search:
            mask = view.apply(lambda row: search in " ".join(map(str, row.values)).casefold(), axis=1)
            view = view[mask]
        if category != "All categories":
            view = view[view["category"] == category]
        for _, item in view.iterrows():
            status = "Low stock" if int(item["stock"]) <= int(item["low_stock_threshold"]) else "In stock"
            self.products_tree.insert("", "end", values=(
                item["product_id"], item["product_name"], item["category"],
                MONEY.format(float(item["price"])), int(item["stock"]),
                int(item["low_stock_threshold"]), item["active"], status
            ), tags=("low",) if status == "Low stock" else ())

    # ------------------------- Sales tab -------------------------
    def _build_sales_tab(self):
        ttk.Label(self.sales_tab, text="Record a Sale", style="Heading.TLabel").pack(anchor="w", pady=(0, 8))
        card = ttk.LabelFrame(self.sales_tab, text="One product per transaction", padding=18)
        card.pack(fill="x", anchor="n")
        self.sale_date_var = tk.StringVar(value=date.today().isoformat())
        self.sale_product_var = tk.StringVar()
        self.sale_quantity_var = tk.StringVar(value="1")
        self.sale_unit_price_var = tk.StringVar()
        self.sale_total_var = tk.StringVar(value=MONEY.format(0))
        self.sale_id_preview = tk.StringVar(value="Generated automatically")

        self._label(card, "Sale ID", 0, 0)
        ttk.Label(card, textvariable=self.sale_id_preview, font=("Segoe UI", 10, "bold")).grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self._label(card, "Sale Date (YYYY-MM-DD)", 0, 1)
        self._entry(card, self.sale_date_var, 1, 1, width=28)
        self._label(card, "Product", 0, 2)
        self.sale_product_combo = ttk.Combobox(card, textvariable=self.sale_product_var, state="readonly", width=32)
        self.sale_product_combo.grid(row=1, column=2, sticky="ew", padx=5, pady=5)
        self.sale_product_combo.bind("<<ComboboxSelected>>", self.on_sale_product_change)
        self._label(card, "Quantity", 2, 0)
        quantity_entry = self._entry(card, self.sale_quantity_var, 3, 0, width=28)
        quantity_entry.bind("<KeyRelease>", lambda _event: self.calculate_sale_total())
        self._label(card, "Unit Price (₹)", 2, 1)
        ttk.Label(card, textvariable=self.sale_unit_price_var, font=("Segoe UI", 12, "bold")).grid(row=3, column=1, sticky="w", padx=5, pady=5)
        self._label(card, "Total Sale Amount", 2, 2)
        ttk.Label(card, textvariable=self.sale_total_var, font=("Segoe UI", 16, "bold"),
                  foreground=COLORS["green_dark"]).grid(row=3, column=2, sticky="w", padx=5, pady=5)
        action_row = ttk.Frame(card)
        action_row.grid(row=4, column=0, columnspan=3, sticky="w", padx=5, pady=(15, 5))
        ttk.Button(action_row, text="Record Sale", style="Accent.TButton", command=self.record_sale).pack(side="left", padx=(0, 8))
        ttk.Button(action_row, text="Clear Form", command=self.clear_sale_form).pack(side="left")
        ttk.Label(self.sales_tab,
                  text="Stock is reduced only after the date, product, quantity and available stock have all been validated.",
                  wraplength=900).pack(anchor="w", pady=14)

    def refresh_product_dropdowns(self):
        if not hasattr(self, "sale_product_combo"):
            return
        active = self._active_products()
        labels = [f"{row['product_id']} — {row['product_name']}" for _, row in active.iterrows()]
        self.sale_product_combo["values"] = labels
        if self.sale_product_var.get() not in labels:
            self.sale_product_var.set("")
            self.sale_unit_price_var.set("")
            self.sale_total_var.set(MONEY.format(0))
        if hasattr(self, "record_product_filter"):
            record_labels = ["All products"] + sorted(self.sales["product_name"].astype(str).unique().tolist()) if not self.sales.empty else ["All products"]
            self.record_product_filter_combo["values"] = record_labels
            if self.record_product_filter.get() not in record_labels:
                self.record_product_filter.set("All products")
            cats = sorted(set(self.sales["category"].astype(str).tolist())) if not self.sales.empty else []
            self.record_category_filter_combo["values"] = ["All categories"] + cats
            if self.record_category_filter.get() not in ["All categories"] + cats:
                self.record_category_filter.set("All categories")

    def on_sale_product_change(self, _event=None):
        label = self.sale_product_var.get()
        product_id = label.split(" — ", 1)[0] if " — " in label else ""
        item = self._product_row(product_id)
        if item is not None:
            self.sale_unit_price_var.set(MONEY.format(float(item["price"])))
        self.calculate_sale_total()

    def calculate_sale_total(self):
        try:
            label = self.sale_product_var.get()
            product_id = label.split(" — ", 1)[0] if " — " in label else ""
            item = self._product_row(product_id)
            quantity = int(self.sale_quantity_var.get())
            if item is None or quantity <= 0:
                raise ValueError
            total = quantity * float(item["price"])
            self.sale_total_var.set(MONEY.format(total))
        except (ValueError, TypeError):
            self.sale_total_var.set("—")

    def clear_sale_form(self):
        self.sale_date_var.set(date.today().isoformat())
        self.sale_product_var.set("")
        self.sale_quantity_var.set("1")
        self.sale_unit_price_var.set("")
        self.sale_total_var.set(MONEY.format(0))
        self.sale_id_preview.set("Generated automatically")

    def record_sale(self):
        try:
            product_label = self.sale_product_var.get()
            product_id = product_label.split(" — ", 1)[0] if " — " in product_label else ""
            product = self._product_row(product_id)
            if product is None or product["active"] != "True":
                raise ValueError("Choose an active product.")
            sale_date = pd.to_datetime(self.sale_date_var.get().strip(), errors="raise").strftime("%Y-%m-%d")
            quantity_text = self.sale_quantity_var.get().strip()
            quantity = int(quantity_text)
            if str(quantity) != quantity_text or quantity <= 0:
                raise ValueError("Quantity must be a positive whole number.")
            if quantity > int(product["stock"]):
                raise ValueError(f"Insufficient stock. Available stock: {int(product['stock'])}.")
            unit_price = round(float(product["price"]), 2)
            sale = {
                "sale_id": self._next_id("S", self.sales["sale_id"].tolist(), 5),
                "sale_date": sale_date, "product_id": product_id,
                "product_name": product["product_name"], "category": product["category"],
                "quantity": quantity, "unit_price": unit_price,
                "total_amount": round(quantity * unit_price, 2)
            }
            new_products = self.products.copy()
            new_products.loc[new_products["product_id"] == product_id, "stock"] = int(product["stock"]) - quantity
            new_sales = pd.concat([self.sales, pd.DataFrame([sale])], ignore_index=True)
            self._commit(new_products, new_sales)
            messagebox.showinfo("Sale recorded", f"Sale {sale['sale_id']} saved.\nTotal: {MONEY.format(sale['total_amount'])}")
            self.clear_sale_form()
        except Exception as exc:
            messagebox.showerror("Could not record sale", str(exc))

    # ------------------------- Sales records tab -------------------------
    def _build_records_tab(self):
        ttk.Label(self.records_tab, text="Sales Records", style="Heading.TLabel").pack(anchor="w", pady=(0, 8))
        filters = ttk.LabelFrame(self.records_tab, text="Search and filters", padding=8)
        filters.pack(fill="x", pady=(0, 8))
        self.record_search = tk.StringVar()
        self.record_product_filter = tk.StringVar(value="All products")
        self.record_category_filter = tk.StringVar(value="All categories")
        self.record_from_date = tk.StringVar()
        self.record_to_date = tk.StringVar()
        ttk.Label(filters, text="Search").grid(row=0, column=0, padx=4, pady=4, sticky="w")
        search = ttk.Entry(filters, textvariable=self.record_search, width=22)
        search.grid(row=1, column=0, padx=4, pady=4)
        search.bind("<KeyRelease>", lambda _event: self.refresh_sales_table())
        ttk.Label(filters, text="Product").grid(row=0, column=1, padx=4, pady=4, sticky="w")
        self.record_product_filter_combo = ttk.Combobox(filters, textvariable=self.record_product_filter, state="readonly", width=20)
        self.record_product_filter_combo.grid(row=1, column=1, padx=4, pady=4)
        self.record_product_filter_combo.bind("<<ComboboxSelected>>", lambda _event: self.refresh_sales_table())
        ttk.Label(filters, text="Category").grid(row=0, column=2, padx=4, pady=4, sticky="w")
        self.record_category_filter_combo = ttk.Combobox(filters, textvariable=self.record_category_filter, state="readonly", width=20)
        self.record_category_filter_combo.grid(row=1, column=2, padx=4, pady=4)
        self.record_category_filter_combo.bind("<<ComboboxSelected>>", lambda _event: self.refresh_sales_table())
        ttk.Label(filters, text="From date").grid(row=0, column=3, padx=4, pady=4, sticky="w")
        ttk.Entry(filters, textvariable=self.record_from_date, width=13).grid(row=1, column=3, padx=4, pady=4)
        ttk.Label(filters, text="To date").grid(row=0, column=4, padx=4, pady=4, sticky="w")
        ttk.Entry(filters, textvariable=self.record_to_date, width=13).grid(row=1, column=4, padx=4, pady=4)
        ttk.Button(filters, text="Apply Filters", command=self.refresh_sales_table).grid(row=1, column=5, padx=4)
        ttk.Button(filters, text="View All", command=self.clear_record_filters).grid(row=1, column=6, padx=4)

        actions = ttk.Frame(self.records_tab)
        actions.pack(fill="x", pady=(0, 8))
        ttk.Button(actions, text="Edit Selected Sale", command=self.edit_sale).pack(side="left", padx=(0, 5))
        ttk.Button(actions, text="Delete Selected Sale", command=self.delete_sale).pack(side="left", padx=5)
        ttk.Button(actions, text="Export Records CSV", command=self.export_sales).pack(side="right", padx=5)
        ttk.Button(actions, text="Import Sales CSV", command=self.import_sales).pack(side="right", padx=5)

        columns = ("sale_id", "sale_date", "product_name", "category", "quantity", "unit_price", "total_amount")
        headings = ("Sale ID", "Date", "Product Name", "Category", "Quantity", "Unit Price", "Total Amount")
        self.sales_tree = self._make_tree(self.records_tab, columns, headings,
                                          (100, 100, 220, 160, 80, 110, 120), height=15)
        self.sales_tree.bind("<<TreeviewSelect>>", self.on_sale_select)

    def clear_record_filters(self):
        self.record_search.set("")
        self.record_product_filter.set("All products")
        self.record_category_filter.set("All categories")
        self.record_from_date.set("")
        self.record_to_date.set("")
        self.refresh_sales_table()

    def _filtered_sales(self, show_errors=False):
        view = self.sales.copy()
        if view.empty:
            return view
        search = self.record_search.get().strip().casefold()
        if search:
            view = view[view.apply(lambda row: search in " ".join(map(str, row.values)).casefold(), axis=1)]
        product = self.record_product_filter.get()
        if product and product != "All products":
            view = view[view["product_name"] == product]
        category = self.record_category_filter.get()
        if category and category != "All categories":
            view = view[view["category"] == category]
        start = self.record_from_date.get().strip()
        end = self.record_to_date.get().strip()
        try:
            if start:
                start = pd.to_datetime(start, errors="raise").strftime("%Y-%m-%d")
                view = view[view["sale_date"] >= start]
            if end:
                end = pd.to_datetime(end, errors="raise").strftime("%Y-%m-%d")
                view = view[view["sale_date"] <= end]
            if start and end and start > end:
                raise ValueError("From date must be on or before To date.")
        except Exception as exc:
            if show_errors:
                messagebox.showerror("Invalid date filter", str(exc))
            return self.sales.iloc[0:0].copy()
        return view

    def refresh_sales_table(self):
        if not hasattr(self, "sales_tree"):
            return
        for row in self.sales_tree.get_children():
            self.sales_tree.delete(row)
        view = self._filtered_sales()
        for _, item in view.sort_values("sale_date", ascending=False).iterrows():
            self.sales_tree.insert("", "end", values=(
                item["sale_id"], item["sale_date"], item["product_name"], item["category"],
                int(item["quantity"]), MONEY.format(float(item["unit_price"])),
                MONEY.format(float(item["total_amount"]))
            ))

    def on_sale_select(self, _event=None):
        selection = self.sales_tree.selection()
        self.selected_sale_id = self.sales_tree.item(selection[0], "values")[0] if selection else None

    def edit_sale(self):
        if not self.selected_sale_id:
            messagebox.showerror("Select a sale", "Select a sale record first.")
            return
        sale = self.sales[self.sales["sale_id"] == self.selected_sale_id]
        if sale.empty:
            messagebox.showerror("Sale not found", "The selected sale no longer exists.")
            return
        sale = sale.iloc[0]
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Edit {sale['sale_id']}")
        dialog.configure(bg=COLORS["cream"])
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)
        date_var = tk.StringVar(value=str(sale["sale_date"]))
        qty_var = tk.StringVar(value=str(int(sale["quantity"])))
        price_var = tk.StringVar(value=str(float(sale["unit_price"])))
        ttk.Label(dialog, text=f"Edit Sale {sale['sale_id']}", style="Heading.TLabel").grid(row=0, column=0, columnspan=2, padx=14, pady=12)
        ttk.Label(dialog, text="Date (YYYY-MM-DD)").grid(row=1, column=0, padx=12, pady=7, sticky="w")
        ttk.Entry(dialog, textvariable=date_var, width=24).grid(row=1, column=1, padx=12, pady=7)
        ttk.Label(dialog, text="Quantity").grid(row=2, column=0, padx=12, pady=7, sticky="w")
        ttk.Entry(dialog, textvariable=qty_var, width=24).grid(row=2, column=1, padx=12, pady=7)
        ttk.Label(dialog, text="Unit price (₹)").grid(row=3, column=0, padx=12, pady=7, sticky="w")
        ttk.Entry(dialog, textvariable=price_var, width=24).grid(row=3, column=1, padx=12, pady=7)
        ttk.Label(dialog, text="Price defaults to the original transaction price. Change only if correcting the record.",
                  wraplength=340).grid(row=4, column=0, columnspan=2, padx=12, pady=7)

        def save_edit():
            try:
                new_date = pd.to_datetime(date_var.get().strip(), errors="raise").strftime("%Y-%m-%d")
                qty_text = qty_var.get().strip()
                new_qty = int(qty_text)
                if str(new_qty) != qty_text or new_qty <= 0:
                    raise ValueError("Quantity must be a positive whole number.")
                new_price = float(price_var.get())
                if new_price < 0:
                    raise ValueError("Unit price cannot be negative.")
                product = self._product_row(str(sale["product_id"]))
                if product is None:
                    raise ValueError("The linked product no longer exists, so stock cannot be reconciled safely.")
                old_qty = int(sale["quantity"])
                available_after_return = int(product["stock"]) + old_qty
                if new_qty > available_after_return:
                    raise ValueError(f"Not enough stock to change this sale. Maximum quantity for this edit: {available_after_return}.")
                if not messagebox.askyesno("Confirm sale edit",
                    f"Update quantity from {old_qty} to {new_qty} and save the corrected transaction?"):
                    return
                new_products = self.products.copy()
                new_products.loc[new_products["product_id"] == product["product_id"], "stock"] = available_after_return - new_qty
                new_sales = self.sales.copy()
                idx = new_sales.index[new_sales["sale_id"] == sale["sale_id"]][0]
                new_sales.at[idx, "sale_date"] = new_date
                new_sales.at[idx, "quantity"] = new_qty
                new_sales.at[idx, "unit_price"] = round(new_price, 2)
                new_sales.at[idx, "total_amount"] = round(new_qty * new_price, 2)
                self._commit(new_products, new_sales)
                dialog.destroy()
                messagebox.showinfo("Sale updated", "Sale updated and stock reconciled.")
            except Exception as exc:
                messagebox.showerror("Could not edit sale", str(exc), parent=dialog)

        ttk.Button(dialog, text="Save Changes", style="Accent.TButton", command=save_edit).grid(row=5, column=0, padx=12, pady=14)
        ttk.Button(dialog, text="Cancel", command=dialog.destroy).grid(row=5, column=1, padx=12, pady=14)

    def delete_sale(self):
        if not self.selected_sale_id:
            messagebox.showerror("Select a sale", "Select a sale record first.")
            return
        sale = self.sales[self.sales["sale_id"] == self.selected_sale_id]
        if sale.empty:
            return
        sale = sale.iloc[0]
        if not messagebox.askyesno("Confirm deletion",
            f"Delete sale {sale['sale_id']} for {sale['product_name']}?\n"
            "The sold quantity will be returned to stock."):
            return
        product = self._product_row(str(sale["product_id"]))
        if product is None:
            messagebox.showerror("Cannot safely delete", "The linked product is missing. No data was changed.")
            return
        try:
            new_products = self.products.copy()
            new_products.loc[new_products["product_id"] == product["product_id"], "stock"] = int(product["stock"]) + int(sale["quantity"])
            new_sales = self.sales[self.sales["sale_id"] != sale["sale_id"]].copy()
            self._commit(new_products, new_sales)
            self.selected_sale_id = None
            messagebox.showinfo("Sale deleted", "Sale deleted and stock returned.")
        except Exception as exc:
            messagebox.showerror("Could not delete sale", str(exc))

    # ------------------------- Dashboard and analytics -------------------------
    def _build_dashboard_tab(self):
        ttk.Label(self.dashboard_tab, text="Sales Dashboard", style="Heading.TLabel").pack(anchor="w", pady=(0, 8))
        filters = ttk.LabelFrame(self.dashboard_tab, text="Analytics filters", padding=8)
        filters.pack(fill="x", pady=(0, 8))
        self.analytics_from = tk.StringVar()
        self.analytics_to = tk.StringVar()
        self.analytics_category = tk.StringVar(value="All categories")
        ttk.Label(filters, text="From date").pack(side="left", padx=(3, 5))
        ttk.Entry(filters, textvariable=self.analytics_from, width=13).pack(side="left", padx=(0, 12))
        ttk.Label(filters, text="To date").pack(side="left", padx=(0, 5))
        ttk.Entry(filters, textvariable=self.analytics_to, width=13).pack(side="left", padx=(0, 12))
        ttk.Label(filters, text="Category").pack(side="left", padx=(0, 5))
        self.analytics_category_combo = ttk.Combobox(filters, textvariable=self.analytics_category, state="readonly", width=23)
        self.analytics_category_combo.pack(side="left", padx=(0, 12))
        self.analytics_category_combo.bind("<<ComboboxSelected>>", lambda _event: self.refresh_dashboard())
        ttk.Button(filters, text="Apply", command=self.refresh_dashboard).pack(side="left", padx=3)
        ttk.Button(filters, text="Reset", command=self.reset_analytics_filters).pack(side="left", padx=3)

        self.kpi_frame = ttk.Frame(self.dashboard_tab)
        self.kpi_frame.pack(fill="x", pady=(0, 8))
        self.kpi_values = {}
        for i, (key, title) in enumerate([
            ("revenue", "TOTAL REVENUE"), ("transactions", "SALES TRANSACTIONS"),
            ("units", "TOTAL UNITS SOLD"), ("average", "AVERAGE TRANSACTION")
        ]):
            card = tk.Frame(self.kpi_frame, bg=COLORS["paper"], highlightbackground=COLORS["line"], highlightthickness=1, padx=13, pady=10)
            card.grid(row=0, column=i, sticky="nsew", padx=5)
            self.kpi_frame.columnconfigure(i, weight=1)
            tk.Label(card, text=title, bg=COLORS["paper"], fg=COLORS["muted"],
                     font=("Segoe UI", 9, "bold")).pack(anchor="w")
            value_label = tk.Label(card, text="—", bg=COLORS["paper"], fg=COLORS["brown_dark"],
                                   font=("Segoe UI", 18, "bold"))
            value_label.pack(anchor="w", pady=(5, 0))
            self.kpi_values[key] = value_label

        insights = ttk.LabelFrame(self.dashboard_tab, text="Sales insights", padding=8)
        insights.pack(fill="x", pady=(0, 8))
        self.insights_label = ttk.Label(insights, text="No sales recorded yet.", wraplength=1200, justify="left")
        self.insights_label.pack(anchor="w")

        charts = ttk.Frame(self.dashboard_tab)
        charts.pack(fill="both", expand=True)
        charts.columnconfigure(0, weight=1)
        charts.columnconfigure(1, weight=1)
        charts.rowconfigure(0, weight=1)
        charts.rowconfigure(1, weight=1)
        self.figures = []
        self.canvases = []
        chart_specs = [
            ("monthly", "Monthly Revenue Trend"),
            ("category", "Revenue by Product Category"),
            ("pie", "Revenue Distribution by Category"),
            ("top", "Top 5 Best-Selling Products")
        ]
        for index, (key, title) in enumerate(chart_specs):
            figure = Figure(figsize=(5.5, 2.45), dpi=90, facecolor=COLORS["paper"])
            axes = figure.add_subplot(111)
            axes.set_title(title, fontsize=10, color=COLORS["brown_dark"])
            canvas = FigureCanvasTkAgg(figure, master=charts)
            widget = canvas.get_tk_widget()
            widget.configure(bg=COLORS["paper"], highlightthickness=1, highlightbackground=COLORS["line"])
            widget.grid(row=index // 2, column=index % 2, sticky="nsew", padx=4, pady=4)
            self.figures.append((key, figure, axes))
            self.canvases.append(canvas)

    def reset_analytics_filters(self):
        self.analytics_from.set("")
        self.analytics_to.set("")
        self.analytics_category.set("All categories")
        self.refresh_dashboard()

    def _analytics_sales(self, show_errors=False):
        view = self.sales.copy()
        if view.empty:
            return view
        start = self.analytics_from.get().strip()
        end = self.analytics_to.get().strip()
        try:
            if start:
                start = pd.to_datetime(start, errors="raise").strftime("%Y-%m-%d")
                view = view[view["sale_date"] >= start]
            if end:
                end = pd.to_datetime(end, errors="raise").strftime("%Y-%m-%d")
                view = view[view["sale_date"] <= end]
            if start and end and start > end:
                raise ValueError("From date must be on or before To date.")
        except Exception as exc:
            if show_errors:
                messagebox.showerror("Invalid analytics date", str(exc))
            return self.sales.iloc[0:0].copy()
        category = self.analytics_category.get()
        if category and category != "All categories":
            view = view[view["category"] == category]
        return view

    def refresh_dashboard(self):
        if not hasattr(self, "kpi_values"):
            return
        categories = sorted(set(self.sales["category"].astype(str).tolist())) if not self.sales.empty else []
        self.analytics_category_combo["values"] = ["All categories"] + categories
        if self.analytics_category.get() not in ["All categories"] + categories:
            self.analytics_category.set("All categories")
        view = self._analytics_sales()
        revenue = float(view["total_amount"].sum()) if not view.empty else 0.0
        transactions = int(len(view))
        units = int(view["quantity"].sum()) if not view.empty else 0
        average = revenue / transactions if transactions else 0.0
        self.kpi_values["revenue"].config(text=MONEY.format(revenue))
        self.kpi_values["transactions"].config(text=f"{transactions:,}")
        self.kpi_values["units"].config(text=f"{units:,}")
        self.kpi_values["average"].config(text=MONEY.format(average))

        if view.empty:
            best_product = "N/A"
            best_category = "N/A"
            best_month = "N/A"
        else:
            by_product = view.groupby("product_name")["quantity"].sum().sort_values(ascending=False)
            best_product = str(by_product.index[0]) if not by_product.empty else "N/A"
            by_category = view.groupby("category")["total_amount"].sum().sort_values(ascending=False)
            best_category = str(by_category.index[0]) if not by_category.empty else "N/A"
            monthly = view.assign(month=pd.to_datetime(view["sale_date"]).dt.to_period("M").astype(str)).groupby("month")["total_amount"].sum()
            best_month = str(monthly.idxmax()) if not monthly.empty else "N/A"
        period_text = f"Revenue for selected period: {MONEY.format(revenue)}"
        low_stock = int(((self.products["stock"] <= self.products["low_stock_threshold"]) &
                         (self.products["active"] == "True")).sum()) if not self.products.empty else 0
        self.insights_label.config(text=(
            f"Best-selling product by quantity: {best_product}     |     "
            f"Highest-revenue category: {best_category}     |     "
            f"Month with highest revenue: {best_month}     |     "
            f"{period_text}     |     Products with low stock: {low_stock}"
        ))

        for key, figure, axes in self.figures:
            axes.clear()
            axes.set_facecolor(COLORS["paper"])
            axes.set_title({
                "monthly": "Monthly Revenue Trend",
                "category": "Revenue by Product Category",
                "pie": "Revenue Distribution by Category",
                "top": "Top 5 Best-Selling Products"
            }[key], fontsize=10, color=COLORS["brown_dark"])
            if view.empty:
                axes.text(0.5, 0.5, "No sales data for this selection",
                          ha="center", va="center", transform=axes.transAxes, color=COLORS["muted"])
                axes.set_xticks([])
                axes.set_yticks([])
            elif key == "monthly":
                data = view.assign(month=pd.to_datetime(view["sale_date"]).dt.to_period("M").astype(str)).groupby("month")["total_amount"].sum().sort_index()
                axes.plot(data.index.tolist(), data.values.tolist(), marker="o", linewidth=2, color=COLORS["green"])
                axes.set_ylabel("Revenue (₹)", fontsize=8)
                axes.tick_params(axis="x", labelrotation=35, labelsize=7)
                axes.tick_params(axis="y", labelsize=7)
                axes.grid(axis="y", alpha=0.25)
            elif key == "category":
                data = view.groupby("category")["total_amount"].sum().sort_values(ascending=False)
                axes.bar(data.index.astype(str), data.values, color=COLORS["green"])
                axes.set_ylabel("Revenue (₹)", fontsize=8)
                axes.tick_params(axis="x", labelrotation=35, labelsize=7)
                axes.tick_params(axis="y", labelsize=7)
                axes.grid(axis="y", alpha=0.2)
            elif key == "pie":
                data = view.groupby("category")["total_amount"].sum()
                data = data[data > 0]
                if data.empty:
                    axes.text(0.5, 0.5, "No positive revenue to display", ha="center", va="center", transform=axes.transAxes)
                else:
                    axes.pie(data.values, labels=data.index.astype(str), autopct="%1.0f%%",
                             startangle=90, textprops={"fontsize": 7})
            elif key == "top":
                data = view.groupby("product_name")["quantity"].sum().sort_values(ascending=True).tail(5)
                axes.barh(data.index.astype(str), data.values, color=COLORS["green"])
                axes.set_xlabel("Units sold", fontsize=8)
                axes.tick_params(axis="x", labelsize=7)
                axes.tick_params(axis="y", labelsize=7)
                axes.grid(axis="x", alpha=0.2)
            figure.tight_layout()
            # Find the corresponding canvas in the same order as figure specs.
            canvas_index = [item[0] for item in self.figures].index(key)
            self.canvases[canvas_index].draw_idle()

    # ------------------------- CSV import/export -------------------------
    def export_products(self):
        path = filedialog.asksaveasfilename(title="Export products", defaultextension=".csv",
                                            filetypes=[("CSV files", "*.csv")], initialfile="products_export.csv")
        if not path:
            return
        try:
            self.products[PRODUCT_COLUMNS].to_csv(path, index=False, encoding="utf-8-sig")
            messagebox.showinfo("Export complete", f"Products exported to:\n{path}")
        except Exception as exc:
            messagebox.showerror("Export failed", str(exc))

    def export_sales(self):
        path = filedialog.asksaveasfilename(title="Export sales records", defaultextension=".csv",
                                            filetypes=[("CSV files", "*.csv")], initialfile="sales_export.csv")
        if not path:
            return
        try:
            self.sales[SALE_COLUMNS].to_csv(path, index=False, encoding="utf-8-sig")
            messagebox.showinfo("Export complete", f"Sales records exported to:\n{path}")
        except Exception as exc:
            messagebox.showerror("Export failed", str(exc))

    def import_products(self):
        path = filedialog.askopenfilename(title="Import products CSV", filetypes=[("CSV files", "*.csv")])
        if not path:
            return
        try:
            incoming_raw = pd.read_csv(path, dtype=str, keep_default_na=False)
            # Accept the application's schema, or the user's original Excel-exported headers.
            rename_map = {
                "Product ID": "product_id", "Product name": "product_name", "Category": "category",
                "Selling price (₹)": "price", "Current stock quantity": "stock",
                "Low-stock threshold": "low_stock_threshold", "Active": "active"
            }
            incoming_raw = incoming_raw.rename(columns=rename_map)
            if "product_id" not in incoming_raw.columns:
                incoming_raw["product_id"] = ""
            if "active" not in incoming_raw.columns:
                incoming_raw["active"] = "True"
            incoming_raw = incoming_raw[PRODUCT_COLUMNS]
            incoming = clean_products(incoming_raw)
            if incoming.empty:
                raise ValueError("The selected file contains no products.")
            duplicate_ids = set(incoming["product_id"]) & set(self.products["product_id"])
            if duplicate_ids:
                raise ValueError("Import cancelled: these Product IDs already exist: " + ", ".join(sorted(duplicate_ids)))
            if incoming["product_id"].eq("").any():
                raise ValueError("Each imported product must have a unique Product ID.")
            if not messagebox.askyesno("Confirm import", f"Import {len(incoming)} products? Existing products will be kept; duplicate IDs are rejected."):
                return
            self._commit(pd.concat([self.products, incoming], ignore_index=True), self.sales)
            messagebox.showinfo("Import complete", f"Imported {len(incoming)} products.")
        except Exception as exc:
            messagebox.showerror("Import failed", str(exc))

    def import_sales(self):
        path = filedialog.askopenfilename(title="Import sales CSV", filetypes=[("CSV files", "*.csv")])
        if not path:
            return
        try:
            incoming = clean_sales(pd.read_csv(path, dtype=str, keep_default_na=False))
            if incoming.empty:
                raise ValueError("The selected file contains no sales.")
            duplicate_ids = set(incoming["sale_id"]) & set(self.sales["sale_id"])
            if duplicate_ids:
                raise ValueError("Import cancelled: these Sale IDs already exist: " + ", ".join(sorted(duplicate_ids)))
            # Importing sales must reconcile stock; every product must exist and have enough stock.
            new_products = self.products.copy()
            for _, sale in incoming.iterrows():
                matches = new_products.index[new_products["product_id"] == sale["product_id"]].tolist()
                if not matches:
                    raise ValueError(f"Product ID {sale['product_id']} for sale {sale['sale_id']} does not exist.")
                index = matches[0]
                if new_products.at[index, "active"] != "True":
                    raise ValueError(f"Product {sale['product_id']} is inactive.")
                available = int(new_products.at[index, "stock"])
                qty = int(sale["quantity"])
                if qty > available:
                    raise ValueError(f"Not enough stock for {sale['product_name']}. Available {available}, imported sale needs {qty}.")
                new_products.at[index, "stock"] = available - qty
            if not messagebox.askyesno("Confirm import", f"Import {len(incoming)} sales and deduct their quantities from stock?"):
                return
            self._commit(new_products, pd.concat([self.sales, incoming], ignore_index=True))
            messagebox.showinfo("Import complete", f"Imported {len(incoming)} sales and updated stock.")
        except Exception as exc:
            messagebox.showerror("Import failed", str(exc))


def main():
    root = tk.Tk()
    app = MayuraBakeryApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
