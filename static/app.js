// API Base URL
const API = {
    items: '/items',
    orders: '/orders',
    statistics: '/statistics'
};

// State
let inventoryItems = [];
let ordersList = [];
let statsData = null;

// DOM Elements
const navButtons = document.querySelectorAll('.nav-btn');
const tabContents = document.querySelectorAll('.tab-content');
const toast = document.getElementById('toast');

// Dashboard elements
const statItems = document.getElementById('stat-items');
const statInventoryValue = document.getElementById('stat-inventory-value');
const statRevenue = document.getElementById('stat-revenue');
const statLowStock = document.getElementById('stat-low-stock');
const categoryList = document.getElementById('category-list');
const recentOrders = document.getElementById('recent-orders');

// Inventory elements
const addItemBtn = document.getElementById('add-item-btn');
const searchInput = document.getElementById('search-input');
const inventoryTableBody = document.getElementById('inventory-table-body');
const inventoryEmpty = document.getElementById('inventory-empty');

// Item modal
const itemModal = document.getElementById('item-modal');
const modalTitle = document.getElementById('modal-title');
const itemForm = document.getElementById('item-form');
const itemId = document.getElementById('item-id');
const itemName = document.getElementById('item-name');
const itemCategory = document.getElementById('item-category');
const itemPrice = document.getElementById('item-price');
const itemQuantity = document.getElementById('item-quantity');
const closeItemModal = document.getElementById('close-item-modal');
const cancelItemBtn = document.getElementById('cancel-item-btn');
const saveItemBtn = document.getElementById('save-item-btn');

// Orders elements
const createOrderBtn = document.getElementById('create-order-btn');
const ordersTableBody = document.getElementById('orders-table-body');
const ordersEmpty = document.getElementById('orders-empty');

// Order modal
const orderModal = document.getElementById('order-modal');
const customerName = document.getElementById('customer-name');
const orderLines = document.getElementById('order-lines');
const addOrderLineBtn = document.getElementById('add-order-line-btn');
const orderTotal = document.getElementById('order-total');
const closeOrderModal = document.getElementById('close-order-modal');
const cancelOrderBtn = document.getElementById('cancel-order-btn');
const placeOrderBtn = document.getElementById('place-order-btn');

// Order details modal
const orderDetailsModal = document.getElementById('order-details-modal');
const orderDetailsTitle = document.getElementById('order-details-title');
const detailsCustomer = document.getElementById('details-customer');
const detailsDate = document.getElementById('details-date');
const detailsId = document.getElementById('details-id');
const orderDetailsLines = document.getElementById('order-details-lines');
const detailsTotal = document.getElementById('details-total');
const closeOrderDetailsModal = document.getElementById('close-order-details-modal');
const closeOrderDetailsBtn = document.getElementById('close-order-details-btn');

// Utility Functions
const formatCurrency = (amount) => {
    return `Rs ${Number(amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
};

const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
};

const showToast = (message, type = 'success') => {
    const toastMessage = toast.querySelector('.toast-message');
    const toastIcon = toast.querySelector('.toast-icon');
    
    toastMessage.textContent = message;
    toast.className = `toast ${type} show`;
    
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
};

// Tab Navigation
navButtons.forEach(btn => {
    btn.addEventListener('click', () => {
        const tabId = btn.dataset.tab;
        navButtons.forEach(b => b.classList.remove('active'));
        tabContents.forEach(t => t.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById(tabId).classList.add('active');
    });
});

// API Calls
const fetchStats = async () => {
    try {
        const res = await fetch(API.statistics);
        if (!res.ok) throw new Error('Failed to fetch stats');
        statsData = await res.json();
        renderDashboard();
    } catch (err) {
        showToast(err.message, 'error');
    }
};

const fetchInventory = async (search = '') => {
    try {
        const url = search ? `${API.items}?search=${encodeURIComponent(search)}` : API.items;
        const res = await fetch(url);
        if (!res.ok) throw new Error('Failed to fetch inventory');
        inventoryItems = await res.json();
        renderInventory();
    } catch (err) {
        showToast(err.message, 'error');
    }
};

const fetchOrders = async () => {
    try {
        const res = await fetch(API.orders);
        if (!res.ok) throw new Error('Failed to fetch orders');
        ordersList = await res.json();
        renderOrders();
    } catch (err) {
        showToast(err.message, 'error');
    }
};

const createItem = async (data) => {
    try {
        const res = await fetch(API.items, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (!res.ok) {
            const error = await res.json();
            throw new Error(error.detail || 'Failed to create item');
        }
        showToast('Item created successfully');
        closeItemModalFunc();
        fetchInventory();
        fetchStats();
    } catch (err) {
        showToast(err.message, 'error');
    }
};

const updateItem = async (id, data) => {
    try {
        const res = await fetch(`${API.items}/${id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (!res.ok) {
            const error = await res.json();
            throw new Error(error.detail || 'Failed to update item');
        }
        showToast('Item updated successfully');
        closeItemModalFunc();
        fetchInventory();
        fetchStats();
    } catch (err) {
        showToast(err.message, 'error');
    }
};

const deleteItem = async (id) => {
    if (!confirm('Are you sure you want to delete this item?')) return;
    try {
        const res = await fetch(`${API.items}/${id}`, { method: 'DELETE' });
        if (!res.ok) throw new Error('Failed to delete item');
        showToast('Item deleted successfully');
        fetchInventory();
        fetchStats();
    } catch (err) {
        showToast(err.message, 'error');
    }
};

const createOrder = async (customer, items) => {
    try {
        const url = `${API.orders}?customer_name=${encodeURIComponent(customer)}`;
        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(items)
        });
        if (!res.ok) {
            const error = await res.json();
            throw new Error(error.detail || 'Failed to place order');
        }
        showToast('Order placed successfully');
        closeOrderModalFunc();
        fetchOrders();
        fetchInventory();
        fetchStats();
    } catch (err) {
        showToast(err.message, 'error');
    }
};

// Render Functions
const renderDashboard = () => {
    if (!statsData) return;
    statItems.textContent = statsData.total_unique_items;
    statInventoryValue.textContent = formatCurrency(statsData.total_inventory_value);
    statRevenue.textContent = formatCurrency(statsData.total_revenue);
    statLowStock.textContent = statsData.low_stock_count;

    // Category summary
    categoryList.innerHTML = '';
    const categories = Object.entries(statsData.category_summary);
    if (categories.length === 0) {
        categoryList.innerHTML = '<li>No categories found</li>';
    } else {
        categories.sort((a,b) => b[1] - a[1]).forEach(([name, count]) => {
            const li = document.createElement('li');
            li.innerHTML = `
                <span class="category-name">${name}</span>
                <span class="category-count">${count} items</span>
            `;
            categoryList.appendChild(li);
        });
    }

    // Recent orders
    recentOrders.innerHTML = '';
    const recent = [...ordersList].sort((a,b) => new Date(b.timestamp) - new Date(a.timestamp)).slice(0, 5);
    if (recent.length === 0) {
        recentOrders.innerHTML = '<li>No recent orders</li>';
    } else {
        recent.forEach(order => {
            const li = document.createElement('li');
            li.innerHTML = `
                <div class="order-main">
                    <span class="order-id">${order.order_id}</span>
                    <span class="order-customer">${order.customer_name}</span>
                </div>
                <div class="order-meta">
                    <span class="order-total">${formatCurrency(order.total)}</span>
                    <span class="order-date">${formatDate(order.timestamp)}</span>
                </div>
            `;
            recentOrders.appendChild(li);
        });
    }
};

const renderInventory = () => {
    inventoryTableBody.innerHTML = '';
    if (inventoryItems.length === 0) {
        inventoryEmpty.style.display = 'block';
        return;
    }
    inventoryEmpty.style.display = 'none';
    inventoryItems.forEach(item => {
        const tr = document.createElement('tr');
        const isLow = item.quantity <= 5;
        tr.innerHTML = `
            <td><strong>${item.item_id}</strong></td>
            <td>${item.name}</td>
            <td>${item.category}</td>
            <td>${formatCurrency(item.price)}</td>
            <td><span class="stock-badge ${isLow ? 'low' : 'normal'}">${item.quantity}</span></td>
            <td>${formatDate(item.date_added)}</td>
            <td>
                <div class="action-buttons">
                    <button class="action-btn edit" onclick="openEditModal('${item.item_id}')">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="action-btn delete" onclick="deleteItem('${item.item_id}')">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </td>
        `;
        inventoryTableBody.appendChild(tr);
    });
};

const renderOrders = () => {
    ordersTableBody.innerHTML = '';
    if (ordersList.length === 0) {
        ordersEmpty.style.display = 'block';
        return;
    }
    ordersEmpty.style.display = 'none';
    // Sort by date desc
    const sorted = [...ordersList].sort((a,b) => new Date(b.timestamp) - new Date(a.timestamp));
    sorted.forEach(order => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${order.order_id}</strong></td>
            <td>${order.customer_name}</td>
            <td>${formatDate(order.timestamp)}</td>
            <td>${order.lines.length} item(s)</td>
            <td><strong style="color: var(--success)">${formatCurrency(order.total)}</strong></td>
            <td>
                <div class="action-buttons">
                    <button class="action-btn view" onclick="openOrderDetails('${order.order_id}')">
                        <i class="fas fa-eye"></i>
                    </button>
                </div>
            </td>
        `;
        ordersTableBody.appendChild(tr);
    });
};

// Modal Functions
const openAddModal = () => {
    modalTitle.textContent = 'Add New Item';
    itemForm.reset();
    itemId.value = '';
    itemModal.classList.add('active');
};

const openEditModal = (id) => {
    const item = inventoryItems.find(i => i.item_id === id);
    if (!item) return;
    modalTitle.textContent = 'Edit Item';
    itemId.value = item.item_id;
    itemName.value = item.name;
    itemCategory.value = item.category;
    itemPrice.value = item.price;
    itemQuantity.value = item.quantity;
    itemModal.classList.add('active');
};

const closeItemModalFunc = () => {
    itemModal.classList.remove('active');
};

const closeOrderModalFunc = () => {
    orderModal.classList.remove('active');
    customerName.value = '';
    orderLines.innerHTML = '';
    updateOrderTotal();
};

const openOrderModal = () => {
    customerName.value = '';
    orderLines.innerHTML = '';
    addOrderLine();
    orderModal.classList.add('active');
};

const openOrderDetails = (id) => {
    const order = ordersList.find(o => o.order_id === id);
    if (!order) return;
    orderDetailsTitle.textContent = `Order ${order.order_id}`;
    detailsCustomer.textContent = order.customer_name;
    detailsDate.textContent = formatDate(order.timestamp);
    detailsId.textContent = order.order_id;
    orderDetailsLines.innerHTML = '';
    order.lines.forEach(line => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${line.item_name}</td>
            <td>${formatCurrency(line.unit_price)}</td>
            <td>${line.quantity}</td>
            <td><strong>${formatCurrency(line.subtotal)}</strong></td>
        `;
        orderDetailsLines.appendChild(tr);
    });
    detailsTotal.textContent = formatCurrency(order.total);
    orderDetailsModal.classList.add('active');
};

// Order Line Functions
const addOrderLine = () => {
    const line = document.createElement('div');
    line.className = 'order-line';
    // Build options
    let options = '<option value="">Select item...</option>';
    inventoryItems.forEach(item => {
        options += `<option value="${item.item_id}" data-price="${item.price}" data-stock="${item.quantity}">${item.name} (Stock: ${item.quantity})</option>`;
    });
    line.innerHTML = `
        <div class="form-group">
            <label>Item</label>
            <select class="order-item-select" required>${options}</select>
        </div>
        <div class="form-group">
            <label>Quantity</label>
            <input type="number" class="order-qty" min="1" required>
        </div>
        <button class="remove-line-btn" type="button">
            <i class="fas fa-trash"></i>
        </button>
    `;
    line.querySelector('.remove-line-btn').addEventListener('click', () => {
        line.remove();
        updateOrderTotal();
    });
    line.querySelector('.order-item-select').addEventListener('change', () => {
        const select = line.querySelector('.order-item-select');
        const qtyInput = line.querySelector('.order-qty');
        const selected = select.options[select.selectedIndex];
        if (selected.value) {
            const stock = parseInt(selected.dataset.stock);
            qtyInput.max = stock;
            qtyInput.value = 1;
        }
    });
    line.querySelector('.order-qty').addEventListener('input', updateOrderTotal);
    orderLines.appendChild(line);
};

const updateOrderTotal = () => {
    let total = 0;
    document.querySelectorAll('.order-line').forEach(line => {
        const select = line.querySelector('.order-item-select');
        const qty = parseInt(line.querySelector('.order-qty').value) || 0;
        const selected = select.options[select.selectedIndex];
        if (selected.value && qty > 0) {
            const price = parseFloat(selected.dataset.price);
            total += price * qty;
        }
    });
    orderTotal.textContent = formatCurrency(total);
};

// Event Listeners
addItemBtn.addEventListener('click', openAddModal);
closeItemModal.addEventListener('click', closeItemModalFunc);
cancelItemBtn.addEventListener('click', closeItemModalFunc);
itemModal.addEventListener('click', (e) => { if (e.target === itemModal) closeItemModalFunc(); });

saveItemBtn.addEventListener('click', () => {
    const data = {
        name: itemName.value.trim(),
        category: itemCategory.value.trim(),
        price: parseFloat(itemPrice.value),
        quantity: parseInt(itemQuantity.value)
    };
    if (!data.name || !data.category || isNaN(data.price) || isNaN(data.quantity)) {
        showToast('Please fill all fields correctly', 'warning');
        return;
    }
    if (itemId.value) {
        // Update
        updateItem(itemId.value, data);
    } else {
        // Create
        createItem(data);
    }
});

searchInput.addEventListener('input', (e) => {
    fetchInventory(e.target.value);
});

createOrderBtn.addEventListener('click', openOrderModal);
closeOrderModal.addEventListener('click', closeOrderModalFunc);
cancelOrderBtn.addEventListener('click', closeOrderModalFunc);
orderModal.addEventListener('click', (e) => { if (e.target === orderModal) closeOrderModalFunc(); });
addOrderLineBtn.addEventListener('click', addOrderLine);

placeOrderBtn.addEventListener('click', () => {
    const customer = customerName.value.trim();
    if (!customer) {
        showToast('Please enter customer name', 'warning');
        return;
    }
    const items = [];
    let valid = true;
    document.querySelectorAll('.order-line').forEach(line => {
        const select = line.querySelector('.order-item-select');
        const qty = parseInt(line.querySelector('.order-qty').value);
        if (select.value && qty > 0) {
            const selected = select.options[select.selectedIndex];
            const stock = parseInt(selected.dataset.stock);
            if (qty > stock) {
                showToast(`Insufficient stock for ${selected.text}`, 'error');
                valid = false;
                return;
            }
            items.push({ item_id: select.value, quantity: qty });
        }
    });
    if (!valid) return;
    if (items.length === 0) {
        showToast('Please add at least one item', 'warning');
        return;
    }
    createOrder(customer, items);
});

closeOrderDetailsModal.addEventListener('click', () => orderDetailsModal.classList.remove('active'));
closeOrderDetailsBtn.addEventListener('click', () => orderDetailsModal.classList.remove('active'));
orderDetailsModal.addEventListener('click', (e) => { if (e.target === orderDetailsModal) orderDetailsModal.classList.remove('active'); });

// Expose functions for inline onclick
window.openEditModal = openEditModal;
window.deleteItem = deleteItem;
window.openOrderDetails = openOrderDetails;

// Initial Load
const init = () => {
    fetchStats();
    fetchInventory();
    fetchOrders();
};

init();