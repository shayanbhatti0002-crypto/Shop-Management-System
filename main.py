import os
import json
import logging
from datetime import datetime
from typing import List, Optional, Dict
from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel, Field
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# --- Logging & Constants ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

INVENTORY_JSON = "inventory.json"
ORDERS_JSON = "orders.json"
LOW_STOCK_THRESHOLD = 5

app = FastAPI(title="Shop Management API", version="1.0")
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- Pydantic Models (Schemas) ---

class ItemBase(BaseModel):
    name: str
    category: str
    price: float = Field(gt=0)
    quantity: int = Field(ge=0)

class ItemResponse(ItemBase):
    item_id: str
    date_added: str

class UpdateItemRequest(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    quantity: Optional[int] = Field(None, ge=0)

class OrderLineRequest(BaseModel):
    item_id: str
    quantity: int = Field(gt=0)

class OrderLineResponse(BaseModel):
    item_id: str
    item_name: str
    quantity: int
    unit_price: float
    subtotal: float

class OrderResponse(BaseModel):
    order_id: str
    customer_name: str
    timestamp: str
    lines: List[OrderLineResponse]
    total: float

class StatsResponse(BaseModel):
    total_unique_items: int
    total_inventory_value: float
    total_revenue: float
    low_stock_count: int
    category_summary: Dict[str, int]

# --- Logic Managers (Modified for FastAPI) ---

class InventoryManager:
    def __init__(self):
        self.items: Dict[str, ItemResponse] = {}
        self._next_id: int = 1
        self._load()

    def _load(self):
        if os.path.exists(INVENTORY_JSON):
            with open(INVENTORY_JSON, "r") as f:
                data = json.load(f)
                for d in data:
                    self.items[d["item_id"]] = ItemResponse(**d)
                ids = [int(k.split("-")[1]) for k in self.items if k.startswith("ITM-")]
                self._next_id = max(ids, default=0) + 1

    def _save(self):
        with open(INVENTORY_JSON, "w") as f:
            json.dump([item.dict() for item in self.items.values()], f, indent=2)

    def add(self, data: ItemBase) -> ItemResponse:
        iid = f"ITM-{self._next_id:04d}"
        self._next_id += 1
        new_item = ItemResponse(
            item_id=iid,
            **data.dict(),
            date_added=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        self.items[iid] = new_item
        self._save()
        return new_item

    def update(self, item_id: str, data: UpdateItemRequest) -> Optional[ItemResponse]:
        if item_id not in self.items: return None
        item_dict = self.items[item_id].dict()
        update_data = data.dict(exclude_unset=True)
        item_dict.update(update_data)
        self.items[item_id] = ItemResponse(**item_dict)
        self._save()
        return self.items[item_id]

class OrderManager:
    def __init__(self):
        self.orders: List[OrderResponse] = []
        self._next_id: int = 1
        self._load()

    def _load(self):
        if os.path.exists(ORDERS_JSON):
            with open(ORDERS_JSON, "r") as f:
                data = json.load(f)
                self.orders = [OrderResponse(**o) for o in data]
                ids = [int(o.order_id.split("-")[1]) for o in self.orders if o.order_id.startswith("ORD-")]
                self._next_id = max(ids, default=0) + 1

    def _save(self):
        with open(ORDERS_JSON, "w") as f:
            json.dump([o.dict() for o in self.orders], f, indent=2)

    def create(self, customer: str, lines: List[OrderLineResponse]) -> OrderResponse:
        oid = f"ORD-{self._next_id:05d}"
        self._next_id += 1
        total = sum(line.subtotal for line in lines)
        order = OrderResponse(
            order_id=oid,
            customer_name=customer,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            lines=lines,
            total=round(total, 2)
        )
        self.orders.append(order)
        self._save()
        return order

# Instantiate Managers
im = InventoryManager()
om = OrderManager()

# --- API Endpoints ---


# Serve index.html at root
@app.get("/")
async def serve_index():
    return FileResponse("static/index.html")

@app.get("/items", response_model=List[ItemResponse])
def get_items(search: Optional[str] = None):
    """Retrieve all items or filter by name/category."""
    if search:
        q = search.lower()
        return [i for i in im.items.values() if q in i.name.lower() or q in i.category.lower()]
    return list(im.items.values())

@app.post("/items", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
def create_item(item: ItemBase):
    return im.add(item)

@app.get("/items/{item_id}", response_model=ItemResponse)
def get_item(item_id: str):
    if item_id not in im.items:
        raise HTTPException(status_code=404, detail="Item not found")
    return im.items[item_id]

@app.patch("/items/{item_id}", response_model=ItemResponse)
def update_item(item_id: str, data: UpdateItemRequest):
    updated = im.update(item_id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="Item not found")
    return updated

@app.delete("/items/{item_id}")
def delete_item(item_id: str):
    if item_id not in im.items:
        raise HTTPException(status_code=404, detail="Item not found")
    del im.items[item_id]
    im._save()
    return {"message": f"Item {item_id} deleted"}

@app.post("/orders", response_model=OrderResponse)
def place_order(customer_name: str, items_requested: List[OrderLineRequest]):
    """Process an order and reduce stock."""
    processed_lines = []
    
    for req in items_requested:
        item = im.items.get(req.item_id)
        if not item:
            raise HTTPException(status_code=404, detail=f"Item {req.item_id} not found")
        if item.quantity < req.quantity:
            raise HTTPException(status_code=400, detail=f"Insufficient stock for {item.name}")
        
        line = OrderLineResponse(
            item_id=item.item_id,
            item_name=item.name,
            quantity=req.quantity,
            unit_price=item.price,
            subtotal=round(item.price * req.quantity, 2)
        )
        processed_lines.append(line)

    # Deduct stock after validation
    for line in processed_lines:
        im.items[line.item_id].quantity -= line.quantity
    
    im._save()
    return om.create(customer_name, processed_lines)

@app.get("/orders", response_model=List[OrderResponse])
def get_orders():
    return om.orders

@app.get("/statistics", response_model=StatsResponse)
def get_stats():
    items = list(im.items.values())
    cat_summary = {}
    for i in items:
        cat_summary[i.category] = cat_summary.get(i.category, 0) + 1
        
    return StatsResponse(
        total_unique_items=len(items),
        total_inventory_value=sum(i.price * i.quantity for i in items),
        total_revenue=sum(o.total for o in om.orders),
        low_stock_count=len([i for i in items if i.quantity <= LOW_STOCK_THRESHOLD]),
        category_summary=cat_summary
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)