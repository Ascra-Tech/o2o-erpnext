import frappe

def execute(filters=None):
    columns = [
        {"label": "Supplier", "fieldname": "supplier", "fieldtype": "Link", "options": "Supplier", "width": 200},
        {"label": "Order Number", "fieldname": "name", "fieldtype": "Link", "options": "Purchase Order", "width": 200},
        {"label": "Date", "fieldname": "transaction_date", "fieldtype": "Date", "width": 100},
    ]
    
    # Get current user
    user = frappe.session.user
    
    # Get supplier linked to this user
    supplier = None
    if not frappe.user.has_role("Administrator"):
        supplier_list = frappe.db.sql_list("""
            SELECT name FROM `tabSupplier` WHERE custom_user = %s
        """, user)
        if supplier_list:
            supplier = supplier_list[0]
    
    # Build where clause
    where_clause = "1=1"
    if supplier:
        where_clause += f" AND supplier = '{supplier}'"
    
    # Get data
    data = frappe.db.sql(f"""
        SELECT name, supplier, transaction_date
        FROM `tabPurchase Order`
        WHERE {where_clause}
        ORDER BY transaction_date DESC
    """, as_dict=1)
    
    return columns, data