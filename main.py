#!/usr/bin/env python3
"""
====================================================
   SHOP MANAGEMENT SYSTEM
   A complete CLI-based inventory & order manager
====================================================
"""

import json
import csv
import os
import sys
import logging
import subprocess
import platform
from datetime import datetime
from dataclasses import dataclass, asdict, field
from typing import List, Optional, Dict

# ─── ANSI Color Codes ────────────────────────────────────────────────────────

class Color:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN    = "\033[96m"
    WHITE   = "\033[97m"
    BG_BLUE = "\033[44m"

def c(text: str, color: str) -> str:
    """Wrap text in ANSI color codes."""
    return f"{color}{text}{Color.RESET}"

# ─── Logging Setup ───────────────────────────────────────────────────────────

logging.basicConfig(
    filename="shop_log.txt",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ─── Constants ───────────────────────────────────────────────────────────────

INVENTORY_JSON = "inventory.json"
INVENTORY_CSV  = "inventory.csv"
ORDERS_JSON    = "orders.json"
ORDERS_CSV     = "orders.csv"
LOW_STOCK_THRESHOLD = 5

# ─── Data Classes ────────────────────────────────────────────────────────────

@dataclass
class Item:
    """Represents a single inventory item."""
    item_id:    str
    name:       str
    category:   str
    price:      float
    quantity:   int
    date_added: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> "Item":
        return Item(
            item_id=data["item_id"],
            name=data["name"],
            category=data["category"],
            price=float(data["price"]),
            quantity=int(data["quantity"]),
            date_added=data.get("date_added", "N/A"),
        )


@dataclass
class OrderLine:
    """A single line in an order (item + quantity purchased)."""
    item_id:   str
    item_name: str
    quantity:  int
    unit_price: float

    @property
    def subtotal(self) -> float:
        return round(self.quantity * self.unit_price, 2)

    def to_dict(self) -> dict:
        return {**asdict(self), "subtotal": self.subtotal}


@dataclass
class Order:
    """Represents a customer order."""
    order_id:      str
    customer_name: str
    lines:         List[OrderLine]
    timestamp:     str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    @property
    def total(self) -> float:
        return round(sum(line.subtotal for line in self.lines), 2)

    def to_dict(self) -> dict:
        return {
            "order_id":      self.order_id,
            "customer_name": self.customer_name,
            "timestamp":     self.timestamp,
            "lines":         [l.to_dict() for l in self.lines],
            "total":         self.total,
        }

    @staticmethod
    def from_dict(data: dict) -> "Order":
        lines = [
            OrderLine(
                item_id=l["item_id"],
                item_name=l["item_name"],
                quantity=int(l["quantity"]),
                unit_price=float(l["unit_price"]),
            )
            for l in data["lines"]
        ]
        o = Order(
            order_id=data["order_id"],
            customer_name=data["customer_name"],
            lines=lines,
            timestamp=data.get("timestamp", "N/A"),
        )
        return o


# ─── Inventory Manager ───────────────────────────────────────────────────────

class InventoryManager:
    """Handles all inventory CRUD operations and persistence."""

    def __init__(self):
        self.items: Dict[str, Item] = {}
        self._next_id: int = 1
        self._load()

    # ── Persistence ──────────────────────────────────────────────────────────

    def _load(self):
        """Load inventory from JSON (preferred) or CSV on startup."""
        if os.path.exists(INVENTORY_JSON):
            try:
                with open(INVENTORY_JSON, "r") as f:
                    raw = json.load(f)
                for record in raw:
                    item = Item.from_dict(record)
                    self.items[item.item_id] = item
                # Sync next ID counter
                ids = [int(k.split("-")[1]) for k in self.items if k.startswith("ITM-")]
                self._next_id = max(ids, default=0) + 1
                logger.info(f"Inventory loaded: {len(self.items)} items.")
            except Exception as e:
                logger.error(f"Failed to load inventory JSON: {e}")
        else:
            self._save()  # Create empty files

    def _save(self):
        """Persist inventory to both JSON and CSV."""
        records = [item.to_dict() for item in self.items.values()]
        # JSON
        try:
            with open(INVENTORY_JSON, "w") as f:
                json.dump(records, f, indent=2)
        except Exception as e:
            logger.error(f"JSON save error: {e}")
        # CSV
        try:
            fieldnames = ["item_id", "name", "category", "price", "quantity", "date_added"]
            with open(INVENTORY_CSV, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(records)
        except Exception as e:
            logger.error(f"CSV save error: {e}")

    # ── ID Generation ─────────────────────────────────────────────────────────

    def _generate_id(self) -> str:
        iid = f"ITM-{self._next_id:04d}"
        self._next_id += 1
        return iid

    # ── CRUD ─────────────────────────────────────────────────────────────────

    def add_item(self, name: str, category: str, price: float, quantity: int) -> Item:
        """Add a new item to inventory."""
        item = Item(
            item_id=self._generate_id(),
            name=name,
            category=category,
            price=price,
            quantity=quantity,
        )
        self.items[item.item_id] = item
        self._save()
        logger.info(f"Item added: {item.item_id} – {item.name}")
        return item

    def remove_item(self, item_id: str) -> Optional[Item]:
        """Remove an item by ID. Returns removed item or None."""
        item = self.items.pop(item_id, None)
        if item:
            self._save()
            logger.info(f"Item removed: {item_id}")
        return item

    def get_item(self, item_id: str) -> Optional[Item]:
        return self.items.get(item_id)

    def search(self, query: str) -> List[Item]:
        """Search by ID, name (partial), or category (partial)."""
        q = query.strip().lower()
        results = []
        for item in self.items.values():
            if (q == item.item_id.lower() or
                    q in item.name.lower() or
                    q in item.category.lower()):
                results.append(item)
        return results

    def update_item(self, item_id: str, **kwargs) -> Optional[Item]:
        """Update fields of an existing item."""
        item = self.items.get(item_id)
        if not item:
            return None
        for key, value in kwargs.items():
            if hasattr(item, key) and value is not None:
                setattr(item, key, value)
        self._save()
        logger.info(f"Item updated: {item_id} – {kwargs}")
        return item

    def reduce_stock(self, item_id: str, qty: int) -> bool:
        """Reduce stock after a purchase. Returns False if insufficient stock."""
        item = self.items.get(item_id)
        if not item or item.quantity < qty:
            return False
        item.quantity -= qty
        self._save()
        return True

    # ── Statistics ────────────────────────────────────────────────────────────

    def all_items(self) -> List[Item]:
        return list(self.items.values())

    def total_value(self) -> float:
        return round(sum(i.price * i.quantity for i in self.items.values()), 2)

    def low_stock_items(self) -> List[Item]:
        return [i for i in self.items.values() if i.quantity <= LOW_STOCK_THRESHOLD]

    def category_summary(self) -> Dict[str, int]:
        summary: Dict[str, int] = {}
        for item in self.items.values():
            summary[item.category] = summary.get(item.category, 0) + 1
        return summary


# ─── Order Manager ───────────────────────────────────────────────────────────

class OrderManager:
    """Handles order creation, storage and retrieval."""

    def __init__(self):
        self.orders: List[Order] = []
        self._next_id: int = 1
        self._load()

    # ── Persistence ──────────────────────────────────────────────────────────

    def _load(self):
        if os.path.exists(ORDERS_JSON):
            try:
                with open(ORDERS_JSON, "r") as f:
                    raw = json.load(f)
                self.orders = [Order.from_dict(r) for r in raw]
                ids = [int(o.order_id.split("-")[1]) for o in self.orders if o.order_id.startswith("ORD-")]
                self._next_id = max(ids, default=0) + 1
                logger.info(f"Orders loaded: {len(self.orders)} orders.")
            except Exception as e:
                logger.error(f"Failed to load orders: {e}")
        else:
            self._save()

    def _save(self):
        records = [o.to_dict() for o in self.orders]
        # JSON
        try:
            with open(ORDERS_JSON, "w") as f:
                json.dump(records, f, indent=2)
        except Exception as e:
            logger.error(f"Orders JSON save error: {e}")
        # CSV (flat – one row per order line)
        try:
            fieldnames = ["order_id", "customer_name", "timestamp", "item_id",
                          "item_name", "quantity", "unit_price", "subtotal", "order_total"]
            with open(ORDERS_CSV, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for order in self.orders:
                    for line in order.lines:
                        writer.writerow({
                            "order_id":      order.order_id,
                            "customer_name": order.customer_name,
                            "timestamp":     order.timestamp,
                            "item_id":       line.item_id,
                            "item_name":     line.item_name,
                            "quantity":      line.quantity,
                            "unit_price":    line.unit_price,
                            "subtotal":      line.subtotal,
                            "order_total":   order.total,
                        })
        except Exception as e:
            logger.error(f"Orders CSV save error: {e}")

    # ── Order Operations ─────────────────────────────────────────────────────

    def _generate_id(self) -> str:
        oid = f"ORD-{self._next_id:05d}"
        self._next_id += 1
        return oid

    def place_order(self, customer_name: str, lines: List[OrderLine]) -> Order:
        order = Order(
            order_id=self._generate_id(),
            customer_name=customer_name,
            lines=lines,
        )
        self.orders.append(order)
        self._save()
        logger.info(f"Order placed: {order.order_id} by {customer_name}, total Rs {int(round(order.total)):,}")
        return order

    def all_orders(self) -> List[Order]:
        return self.orders


# ─── UI Helpers ──────────────────────────────────────────────────────────────

def clear():
    command = 'cls' if platform.system() == 'Windows' else 'clear'
    subprocess.call(command, shell=True)

def pause():
    input(c("\n  Press Enter to continue...", Color.CYAN))

def divider(char="═", width=60, color=Color.BLUE):
    print(c(char * width, color))

def header(title: str):
    clear()
    divider()
    print(c(f"  {title.upper()}", Color.BOLD + Color.CYAN))
    divider()
    print()

def success(msg: str):
    print(c(f"\n  ✔  {msg}", Color.GREEN))

def error(msg: str):
    print(c(f"\n  ✘  {msg}", Color.RED))

def warn(msg: str):
    print(c(f"\n  ⚠  {msg}", Color.YELLOW))

def prompt(label: str) -> str:
    return input(c(f"  › {label}: ", Color.YELLOW)).strip()

def fmt_price(value: float) -> str:
    return c(f"Rs {int(round(value)):,}", Color.GREEN)


def print_item_table(items: List[Item]):
    """Print items in a formatted ASCII table."""
    if not items:
        warn("No items to display.")
        return

    col_w = [10, 22, 16, 10, 10, 21]
    headers = ["ID", "Name", "Category", "Price", "Qty", "Date Added"]

    row_fmt = "  {:<%d} {:<%d} {:<%d} {:>%d} {:>%d} {:<%d}" % tuple(col_w)
    sep = "  " + "─" * (sum(col_w) + len(col_w) * 1 + 1)

    print(c(row_fmt.format(*headers), Color.BOLD + Color.WHITE))
    print(c(sep, Color.BLUE))

    for item in items:
        qty_str = str(item.quantity)
        qty_col = c(qty_str, Color.RED if item.quantity <= LOW_STOCK_THRESHOLD else Color.RESET)
        print(
            "  "
            + c(f"{item.item_id:<{col_w[0]}}", Color.CYAN)
            + f" {item.name:<{col_w[1]}}"
            + f" {item.category:<{col_w[2]}}"
            + f" {fmt_price(item.price):>{col_w[3]+9}}"  # +9 for color codes
            + f" {qty_col:>{col_w[4]+9}}"
            + f" {item.date_added:<{col_w[5]}}"
        )
    print(c(sep, Color.BLUE))
    print(c(f"  Total items: {len(items)}", Color.MAGENTA))


def print_order_receipt(order: Order):
    """Print a formatted receipt for an order."""
    w = 52
    print()
    print(c("╔" + "═" * w + "╗", Color.CYAN))
    print(c(f"║{'SHOP MANAGEMENT SYSTEM':^{w}}║", Color.BOLD + Color.CYAN))
    print(c(f"║{'ORDER RECEIPT':^{w}}║", Color.CYAN))
    print(c("╠" + "═" * w + "╣", Color.CYAN))
    print(c(f"║  Order ID   : {order.order_id:<{w-15}}║", Color.WHITE))
    print(c(f"║  Customer   : {order.customer_name:<{w-15}}║", Color.WHITE))
    print(c(f"║  Date/Time  : {order.timestamp:<{w-15}}║", Color.WHITE))
    print(c("╠" + "═" * w + "╣", Color.CYAN))
    print(c(f"║  {'Item':<20} {'Qty':>5} {'Price':>9} {'Subtotal':>10}  ║", Color.BOLD + Color.WHITE))
    print(c("╠" + "─" * w + "╣", Color.CYAN))
    for line in order.lines:
        name = line.item_name[:20]
        row = f"║  {name:<20} {line.quantity:>5} {int(round(line.unit_price)):>9,} {int(round(line.subtotal)):>10,}  ║"
        print(c(row, Color.WHITE))
    print(c("╠" + "═" * w + "╣", Color.CYAN))
    total_row = f"║  {'TOTAL':>{w-14}} Rs {int(round(order.total)):>8,}  ║"
    print(c(total_row, Color.BOLD + Color.GREEN))
    print(c("╠" + "═" * w + "╣", Color.CYAN))
    print(c(f"║{'Thank you for your purchase!':^{w}}║", Color.YELLOW))
    print(c("╚" + "═" * w + "╝", Color.CYAN))


def print_order_table(orders: List[Order]):
    """Print a summary table of all orders."""
    if not orders:
        warn("No orders found.")
        return

    col_w = [12, 22, 21, 10]
    headers = ["Order ID", "Customer", "Date/Time", "Total"]
    row_fmt = "  {:<%d} {:<%d} {:<%d} {:>%d}" % tuple(col_w)
    sep = "  " + "─" * (sum(col_w) + len(col_w))

    print(c(row_fmt.format(*headers), Color.BOLD + Color.WHITE))
    print(c(sep, Color.BLUE))
    for order in orders:
        print(
            "  "
            + c(f"{order.order_id:<{col_w[0]}}", Color.CYAN)
            + f" {order.customer_name:<{col_w[1]}}"
            + f" {order.timestamp:<{col_w[2]}}"
            + f" {fmt_price(order.total):>{col_w[3]+9}}"
        )
    print(c(sep, Color.BLUE))
    grand_total = sum(o.total for o in orders)
    print(c(f"  Orders: {len(orders)}   Grand Total: {fmt_price(grand_total)}", Color.MAGENTA))


# ─── Input Validators ─────────────────────────────────────────────────────────

def get_float(label: str, min_val: float = 0.0) -> Optional[float]:
    while True:
        raw = prompt(label)
        if raw == "":
            return None
        try:
            val = float(raw)
            if val < min_val:
                error(f"Value must be ≥ {min_val}.")
                continue
            return val
        except ValueError:
            error("Please enter a valid number.")

def get_int(label: str, min_val: int = 0) -> Optional[int]:
    while True:
        raw = prompt(label)
        if raw == "":
            return None
        try:
            val = int(raw)
            if val < min_val:
                error(f"Value must be ≥ {min_val}.")
                continue
            return val
        except ValueError:
            error("Please enter a valid integer.")

def get_non_empty(label: str) -> Optional[str]:
    while True:
        val = prompt(label)
        if val == "":
            return None
        if val.strip():
            return val.strip()
        error("Field cannot be empty.")


# ─── Shop Management System ──────────────────────────────────────────────────

class ShopManagementSystem:
    """Top-level controller that wires together all subsystems."""

    def __init__(self):
        self.inventory = InventoryManager()
        self.orders    = OrderManager()

    # ── Main Menu ─────────────────────────────────────────────────────────────

    def run(self):
        while True:
            self._main_menu()
            choice = prompt("Enter choice")
            actions = {
                "1": self._add_item,
                "2": self._remove_item,
                "3": self._search_item,
                "4": self._view_all_items,
                "5": self._update_item,
                "6": self._place_order,
                "7": self._view_orders,
                "8": self._statistics,
                "9": self._exit,
            }
            action = actions.get(choice)
            if action:
                try:
                    action()
                except KeyboardInterrupt:
                    print()
                    warn("Operation cancelled.")
                    pause()
            else:
                error("Invalid choice. Please select 1–9.")
                pause()

    def _main_menu(self):
        clear()
        low = self.inventory.low_stock_items()
        print(c("╔══════════════════════════════════════════╗", Color.CYAN))
        print(c("║       SHOP MANAGEMENT SYSTEM  v1.0       ║", Color.BOLD + Color.CYAN))
        print(c("║            BY SHAYAN SAMI                ║", Color.CYAN))
        print(c("╠══════════════════════════════════════════╣", Color.CYAN))
        print(c("║                                          ║", Color.CYAN))
        print(c("║   1.  Add Item                           ║", Color.WHITE))
        print(c("║   2.  Remove Item                        ║", Color.WHITE))
        print(c("║   3.  Search Item                        ║", Color.WHITE))
        print(c("║   4.  View All Items                     ║", Color.WHITE))
        print(c("║   5.  Update Item                        ║", Color.WHITE))
        print(c("║   6.  Place Order                        ║", Color.WHITE))
        print(c("║   7.  View Orders                        ║", Color.WHITE))
        print(c("║   8.  Inventory Statistics               ║", Color.WHITE))
        print(c("║   9.  Exit                               ║", Color.WHITE))
        print(c("║                                          ║", Color.CYAN))
        print(c("╚══════════════════════════════════════════╝", Color.CYAN))
        inv_count = len(self.inventory.all_items())
        ord_count = len(self.orders.all_orders())
        print(c(f"\n  Items: {inv_count}  |  Orders: {ord_count}  |  "
                f"Inventory Value: {fmt_price(self.inventory.total_value())}", Color.MAGENTA))
        if low:
            print(c(f"  ⚠  {len(low)} item(s) low on stock (≤{LOW_STOCK_THRESHOLD} units)!", Color.YELLOW))
        print()

    # ── 1. Add Item ───────────────────────────────────────────────────────────

    def _add_item(self):
        header("Add New Item")
        name = get_non_empty("Item Name")
        if name is None: return
        category = get_non_empty("Category")
        if category is None: return
        price = get_float("Price (Rs)", min_val=0.01)
        if price is None: return
        quantity = get_int("Quantity", min_val=0)
        if quantity is None: return

        item = self.inventory.add_item(name, category, price, quantity)
        success(f"Item added successfully!")
        print(c(f"\n  ID: {item.item_id}  |  {item.name}  |  {item.category}  |  "
                f"{fmt_price(item.price)}  |  Qty: {item.quantity}", Color.WHITE))
        pause()

    # ── 2. Remove Item ────────────────────────────────────────────────────────

    def _remove_item(self):
        header("Remove Item")
        item_id = get_non_empty("Enter Item ID to remove (e.g. 0003 or ITM-0003)")
        if item_id is None: return
        item_id = item_id.upper()
        if not item_id.startswith("ITM-"):
            item_id = f"ITM-{item_id.zfill(4)}"

        item = self.inventory.get_item(item_id)
        if not item:
            error(f"Item '{item_id}' not found.")
            pause()
            return

        print(c(f"\n  Found: {item.name} ({item.category}) – {fmt_price(item.price)} – Qty: {item.quantity}", Color.WHITE))
        confirm = prompt("Are you sure you want to delete this item? (yes/no)").lower()
        if confirm in ("yes", "y"):
            self.inventory.remove_item(item_id)
            success(f"Item {item_id} removed.")
        else:
            warn("Deletion cancelled.")
        pause()

    # ── 3. Search Item ────────────────────────────────────────────────────────

    def _search_item(self):
        header("Search Item")
        query = get_non_empty("Search by ID, Name, or Category")
        if query is None: return

        results = self.inventory.search(query)
        print()
        if results:
            print(c(f"  Found {len(results)} result(s) for '{query}':\n", Color.GREEN))
            print_item_table(results)
        else:
            warn(f"No items found matching '{query}'.")
        pause()

    # ── 4. View All Items ─────────────────────────────────────────────────────

    def _view_all_items(self):
        header("All Inventory Items")
        items = self.inventory.all_items()
        print_item_table(items)

        low = self.inventory.low_stock_items()
        if low:
            print(c(f"\n  ⚠  Low stock items: {', '.join(i.item_id for i in low)}", Color.YELLOW))
        pause()

    # ── 5. Update Item ────────────────────────────────────────────────────────

    def _update_item(self):
        header("Update Item")
        item_id = get_non_empty("Enter Item ID to update (e.g. 0003 or ITM-0003)")
        if item_id is None: return
        item_id = item_id.upper()
        if not item_id.startswith("ITM-"):
            item_id = f"ITM-{item_id.zfill(4)}"

        item = self.inventory.get_item(item_id)
        if not item:
            error(f"Item '{item_id}' not found.")
            pause()
            return

        print(c(f"\n  Current: {item.name} | {item.category} | "
                f"{fmt_price(item.price)} | Qty: {item.quantity}", Color.WHITE))
        print(c("  (Leave blank to keep current value)\n", Color.CYAN))

        name     = prompt(f"New Name [{item.name}]") or None
        category = prompt(f"New Category [{item.category}]") or None
        price    = get_float(f"New Price [{item.price}] (Rs)")
        quantity = get_int(f"New Quantity [{item.quantity}]")

        updates = {}
        if name:     updates["name"]     = name
        if category: updates["category"] = category
        if price is not None:    updates["price"]    = price
        if quantity is not None: updates["quantity"] = quantity

        if updates:
            self.inventory.update_item(item_id, **updates)
            success("Item updated successfully.")
        else:
            warn("No changes made.")
        pause()

    # ── 6. Place Order ────────────────────────────────────────────────────────

    def _place_order(self):
        header("Place New Order")
        customer = get_non_empty("Customer Name")
        if customer is None: return

        lines: List[OrderLine] = []
        print(c("\n  Add items to order. Enter blank Item ID when done.\n", Color.CYAN))

        while True:
            item_id = prompt("Item ID (blank to finish)").upper()
            if not item_id:
                break
            if not item_id.startswith("ITM-"):
                item_id = f"ITM-{item_id.zfill(4)}"

            item = self.inventory.get_item(item_id)
            if not item:
                error(f"Item '{item_id}' not found.")
                continue

            print(c(f"  → {item.name} | {fmt_price(item.price)} | Stock: {item.quantity}", Color.WHITE))
            if item.quantity == 0:
                warn("Out of stock. Choose a different item.")
                continue

            qty = get_int(f"Quantity (max {item.quantity})", min_val=1)
            if qty is None:
                continue
            if qty > item.quantity:
                error(f"Insufficient stock. Only {item.quantity} available.")
                continue

            lines.append(OrderLine(
                item_id=item.item_id,
                item_name=item.name,
                quantity=qty,
                unit_price=item.price,
            ))
            success(f"Added {qty}x {item.name}")

        if not lines:
            warn("No items selected. Order cancelled.")
            pause()
            return

        # Show summary before confirming
        print(c("\n  ─── Order Summary ───────────────────────", Color.CYAN))
        for line in lines:
            print(f"    {line.item_name:<24} x{line.quantity:>3}  →  {fmt_price(line.subtotal)}")
        total = sum(l.subtotal for l in lines)
        print(c(f"\n  {'TOTAL':>32}  →  {fmt_price(total)}", Color.BOLD + Color.GREEN))

        confirm = prompt("\n  Confirm order? (yes/no)").lower()
        if confirm not in ("yes", "y"):
            warn("Order cancelled.")
            pause()
            return

        # Deduct stock
        for line in lines:
            self.inventory.reduce_stock(line.item_id, line.quantity)

        order = self.orders.place_order(customer, lines)
        print_order_receipt(order)
        pause()

    # ── 7. View Orders ────────────────────────────────────────────────────────

    def _view_orders(self):
        header("Order History")
        all_orders = self.orders.all_orders()
        print_order_table(all_orders)

        if all_orders:
            print()
            detail_id = prompt("Enter Order ID to view receipt (blank to skip)").upper()
            if detail_id:
                match = next((o for o in all_orders if o.order_id == detail_id), None)
                if match:
                    print_order_receipt(match)
                else:
                    error(f"Order '{detail_id}' not found.")
        pause()

    # ── 8. Inventory Statistics ───────────────────────────────────────────────

    def _statistics(self):
        header("Inventory Statistics")
        items   = self.inventory.all_items()
        orders  = self.orders.all_orders()

        total_items    = len(items)
        total_value    = self.inventory.total_value()
        total_qty      = sum(i.quantity for i in items)
        low_stock      = self.inventory.low_stock_items()
        categories     = self.inventory.category_summary()
        total_orders   = len(orders)
        total_revenue  = round(sum(o.total for o in orders), 2)

        def stat_row(label, value):
            print(f"  {c(label+':', Color.CYAN):<35} {c(str(value), Color.WHITE)}")

        divider("─")
        print(c("  INVENTORY", Color.BOLD + Color.YELLOW))
        divider("─")
        stat_row("Total Unique Items",   total_items)
        stat_row("Total Units in Stock", total_qty)
        stat_row("Total Inventory Value", fmt_price(total_value))
        stat_row("Low Stock Items",       len(low_stock))

        if low_stock:
            print(c("\n  Low Stock Details:", Color.YELLOW))
            for i in low_stock:
                print(c(f"    • {i.item_id}  {i.name:<22}  Qty: {i.quantity}", Color.RED))

        divider("─")
        print(c("  CATEGORIES", Color.BOLD + Color.YELLOW))
        divider("─")
        for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
            stat_row(cat, f"{count} item(s)")

        divider("─")
        print(c("  ORDERS", Color.BOLD + Color.YELLOW))
        divider("─")
        stat_row("Total Orders Placed", total_orders)
        stat_row("Total Revenue",        fmt_price(total_revenue))
        if total_orders:
            stat_row("Average Order Value",  fmt_price(total_revenue / total_orders))

        divider("─")
        pause()

    # ── 9. Exit ───────────────────────────────────────────────────────────────

    def _exit(self):
        clear()
        print(c("\n  Thank you for using Shop Management System!", Color.BOLD + Color.GREEN))
        print(c("  All data has been saved. Goodbye!\n", Color.CYAN))
        logger.info("Application exited cleanly.")
        sys.exit(0)


# ─── Entry Point ─────────────────────────────────────────────────────────────

def main():
    try:
        app = ShopManagementSystem()
        app.run()
    except KeyboardInterrupt:
        print(c("\n\n  Interrupted. Goodbye!\n", Color.YELLOW))
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Unhandled exception: {e}", exc_info=True)
        print(c(f"\n  Fatal error: {e}", Color.RED))
        sys.exit(1)

if __name__ == "__main__":
    main()