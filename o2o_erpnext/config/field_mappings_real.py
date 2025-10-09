"""
Updated Field Mappings Configuration for ERPNext <-> ProcureUAT Sync
Based on actual database structure analysis
"""

import frappe
from frappe.utils import getdate, get_datetime

# ProcureUAT Database Structure (Actual):
# - purchase_requisitions: Main invoice/order header
# - purchase_order_items: Line items with financial details  
# - vendors: Supplier information
# - purchase_billing_address: Billing address details

# ERPNext to ProcureUAT field mappings for PURCHASE_REQUISITIONS table
ERPNEXT_TO_PROCUREUAT_PURCHASE_REQUISITIONS = {
    # Basic invoice/order fields
    'name': 'order_name',                        # ERPNext invoice ID -> ProcureUAT order name
    'posting_date': 'created_at',                # Invoice date -> creation date
    'due_date': 'delivery_date',                 # Due date -> delivery date
    'supplier': 'entity',                        # Supplier -> Entity (via lookup)
    'supplier_name': None,                       # Handle via vendor lookup
    'bill_no': 'invoice_number',                 # Supplier bill number -> invoice number
    'bill_date': 'invoice_generated_at',         # Supplier bill date -> invoice generated date
    'remarks': 'remark',                         # Invoice description/remarks
    'custom_gst_percentage': 'gst_percentage',   # GST percentage
    'custom_external_order_id': 'id',            # External order ID (for updates)
    'status': 'order_status',                    # Status mapping needed
}

# ERPNext to ProcureUAT field mappings for PURCHASE_ORDER_ITEMS table
ERPNEXT_TO_PROCUREUAT_PURCHASE_ORDER_ITEMS = {
    # Line item fields
    'item_code': 'product_id',                   # Item code -> Product ID (via lookup)
    'item_name': None,                           # Handle via product lookup
    'qty': 'quantity',                           # Quantity
    'rate': 'unit_rate',                         # Unit rate
    'amount': 'cost',                            # Line total (before tax)
    'base_amount': 'total_amt',                  # Line total (after tax)
    'custom_gst_amount': 'gst_amt',              # GST amount for line
    'uom': 'uom',                                # Unit of measure
    'custom_vendor_id': 'vendor_id',             # Vendor ID for line item
}

# ProcureUAT to ERPNext field mappings (reverse mapping)
PROCUREUAT_TO_ERPNEXT_PURCHASE_REQUISITIONS = {
    'id': 'custom_external_order_id',            # ProcureUAT ID -> ERPNext custom field
    'order_name': 'name',                        # Order name (for lookup)
    'created_at': 'posting_date',                # Creation date -> Invoice date
    'delivery_date': 'due_date',                 # Delivery date -> Due date
    'entity': 'supplier',                        # Entity -> Supplier (via lookup)
    'invoice_number': 'bill_no',                 # Invoice number -> Bill number
    'invoice_generated_at': 'bill_date',         # Invoice date -> Bill date
    'remark': 'remarks',                         # Remarks
    'gst_percentage': 'custom_gst_percentage',   # GST percentage
    'order_status': 'status',                    # Status (needs conversion)
    'requisition_at': None,                      # Info only
    'approved_at': None,                         # Info only
}

PROCUREUAT_TO_ERPNEXT_PURCHASE_ORDER_ITEMS = {
    'product_id': 'item_code',                   # Product ID -> Item code (via lookup)
    'quantity': 'qty',                           # Quantity
    'unit_rate': 'rate',                         # Unit rate
    'cost': 'amount',                            # Line total (before tax)
    'total_amt': 'base_amount',                  # Line total (after tax)
    'gst_amt': 'custom_gst_amount',              # GST amount
    'uom': 'uom',                                # Unit of measure
    'vendor_id': 'custom_vendor_id',             # Vendor ID
}

# Status mappings between systems
STATUS_MAPPING_ERPNEXT_TO_PROCUREUAT = {
    'Draft': 1,                                  # order_status = 1
    'Submitted': 2,                              # order_status = 2  
    'Paid': 3,                                   # order_status = 3
    'Cancelled': 4,                              # order_status = 4
    'Return': 5,                                 # order_status = 5
}

STATUS_MAPPING_PROCUREUAT_TO_ERPNEXT = {
    1: 'Draft',
    2: 'Submitted', 
    3: 'Paid',
    4: 'Cancelled',
    5: 'Return',
}

# Database table configuration
PROCUREUAT_TABLES = {
    'purchase_requisitions': {
        'primary_key': 'id',
        'name_field': 'order_name',
        'date_field': 'created_at',
        'status_field': 'order_status',
        'vendor_field': 'entity',
    },
    'purchase_order_items': {
        'primary_key': 'id',
        'parent_key': 'purchase_order_id',  # Links to purchase_requisitions.id
        'vendor_field': 'vendor_id',
        'product_field': 'product_id',
    },
    'vendors': {
        'primary_key': 'id',
        'name_field': 'name',
        'code_field': 'code',
        'email_field': 'email',
    }
}

def get_vendor_id_from_supplier(supplier_name):
    """
    Get ProcureUAT vendor ID from ERPNext supplier name
    Uses custom field or database lookup
    """
    if not supplier_name:
        return None
        
    try:
        # First check if supplier has external vendor ID
        supplier_doc = frappe.get_doc("Supplier", supplier_name)
        if hasattr(supplier_doc, 'custom_external_vendor_id') and supplier_doc.custom_external_vendor_id:
            return supplier_doc.custom_external_vendor_id
        
        # If not found, try to lookup in external database
        from o2o_erpnext.config.external_db import get_external_db_connection
        
        with get_external_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id FROM vendors 
                    WHERE name = %s OR email = %s 
                    LIMIT 1
                """, (supplier_name, supplier_name))
                
                result = cursor.fetchone()
                if result:
                    vendor_id = result['id']
                    
                    # Update supplier with external vendor ID
                    supplier_doc.custom_external_vendor_id = vendor_id
                    supplier_doc.save()
                    
                    return vendor_id
                    
    except Exception as e:
        frappe.log_error(f"Error getting vendor ID for supplier {supplier_name}: {str(e)}")
        
    return None

def get_supplier_from_vendor_id(vendor_id):
    """
    Get ERPNext supplier name from ProcureUAT vendor ID
    """
    if not vendor_id:
        return None
        
    try:
        # First try to find supplier with this external vendor ID
        suppliers = frappe.get_all("Supplier", 
                                 filters={"custom_external_vendor_id": vendor_id},
                                 fields=["name"])
        if suppliers:
            return suppliers[0].name
        
        # If not found, lookup in external database and create/update supplier
        from o2o_erpnext.config.external_db import get_external_db_connection
        
        with get_external_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT name, code, email, gstn, address, contact_number
                    FROM vendors 
                    WHERE id = %s
                """, (vendor_id,))
                
                vendor = cursor.fetchone()
                if vendor:
                    supplier_name = vendor['name']
                    
                    # Check if supplier exists by name
                    if frappe.db.exists("Supplier", supplier_name):
                        supplier_doc = frappe.get_doc("Supplier", supplier_name)
                        supplier_doc.custom_external_vendor_id = vendor_id
                        supplier_doc.save()
                        return supplier_name
                    else:
                        # Create new supplier
                        supplier_doc = frappe.new_doc("Supplier")
                        supplier_doc.supplier_name = supplier_name
                        supplier_doc.supplier_group = "All Supplier Groups"
                        supplier_doc.custom_external_vendor_id = vendor_id
                        
                        if vendor['email']:
                            supplier_doc.email_id = vendor['email']
                        if vendor['gstn']:
                            supplier_doc.tax_id = vendor['gstn']
                            
                        supplier_doc.save()
                        return supplier_name
                        
    except Exception as e:
        frappe.log_error(f"Error getting supplier for vendor ID {vendor_id}: {str(e)}")
        
    return None

def convert_procureuat_status_to_erpnext(procureuat_status):
    """Convert ProcureUAT order status to ERPNext status"""
    return STATUS_MAPPING_PROCUREUAT_TO_ERPNEXT.get(procureuat_status, 'Draft')

def convert_erpnext_status_to_procureuat(erpnext_status):
    """Convert ERPNext status to ProcureUAT order status"""
    return STATUS_MAPPING_ERPNEXT_TO_PROCUREUAT.get(erpnext_status, 1)

def get_procureuat_purchase_requisition_data(erpnext_invoice):
    """
    Convert ERPNext Purchase Invoice to ProcureUAT purchase_requisitions format
    """
    data = {}
    
    for erpnext_field, procureuat_field in ERPNEXT_TO_PROCUREUAT_PURCHASE_REQUISITIONS.items():
        if procureuat_field and hasattr(erpnext_invoice, erpnext_field):
            value = getattr(erpnext_invoice, erpnext_field)
            
            # Special handling for specific fields
            if erpnext_field == 'supplier':
                # Convert supplier to entity/vendor_id
                data['entity'] = get_vendor_id_from_supplier(value)
            elif erpnext_field == 'status':
                data[procureuat_field] = convert_erpnext_status_to_procureuat(value)
            elif erpnext_field in ['posting_date', 'bill_date']:
                # Convert date to datetime string
                if value:
                    data[procureuat_field] = value.strftime('%Y-%m-%d %H:%M:%S')
            else:
                data[procureuat_field] = value
    
    return data

def get_procureuat_purchase_order_items_data(erpnext_invoice):
    """
    Convert ERPNext Purchase Invoice items to ProcureUAT purchase_order_items format
    """
    items = []
    
    for item in erpnext_invoice.items:
        item_data = {}
        
        for erpnext_field, procureuat_field in ERPNEXT_TO_PROCUREUAT_PURCHASE_ORDER_ITEMS.items():
            if procureuat_field and hasattr(item, erpnext_field):
                value = getattr(item, erpnext_field)
                item_data[procureuat_field] = value
        
        # Add vendor_id from supplier
        item_data['vendor_id'] = get_vendor_id_from_supplier(erpnext_invoice.supplier)
        
        items.append(item_data)
    
    return items