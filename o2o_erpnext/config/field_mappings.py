"""
Field Mappings Configuration for ERPNext <-> ProcureUAT Sync
Defines mapping between ERPNext Purchase Invoice fields and ProcureUAT invoice fields
"""

import frappe
from frappe.utils import getdate, get_datetime

# ERPNext to ProcureUAT field mappings
ERPNEXT_TO_PROCUREUAT_MAPPING = {
    # Basic invoice fields
    'name': 'invoice_number',                    # ERPNext invoice ID -> ProcureUAT invoice number
    'posting_date': 'invoice_date',              # Invoice date
    'due_date': 'due_date',                      # Due date
    'grand_total': 'total_amount',               # Final total amount
    'net_total': 'invoice_amount',               # Pre-tax amount
    'total_taxes_and_charges': 'gst_amount',     # Tax amount
    'status': 'payment_status',                  # Payment status (needs conversion)
    'supplier': 'vendor_id',                     # Supplier -> Vendor (via lookup)
    'supplier_name': 'vendor_name',              # Supplier name
    'bill_no': 'bill_number',                    # Supplier bill number
    'bill_date': 'bill_date',                    # Supplier bill date
    'remarks': 'description',                    # Invoice description/remarks
    'custom_gst_percentage': 'gst_percentage',   # GST percentage
    'custom_external_invoice_id': 'id',          # External invoice ID (for updates)
}

# ProcureUAT to ERPNext field mappings (reverse mapping)
PROCUREUAT_TO_ERPNEXT_MAPPING = {
    'id': 'custom_external_invoice_id',          # ProcureUAT ID -> ERPNext custom field
    'invoice_number': 'name',                    # Invoice number (for lookup)
    'invoice_date': 'posting_date',              # Invoice date
    'due_date': 'due_date',                      # Due date
    'total_amount': 'grand_total',               # Total amount
    'invoice_amount': 'net_total',               # Pre-tax amount
    'gst_amount': 'total_taxes_and_charges',     # Tax amount
    'payment_status': 'status',                  # Payment status (needs conversion)
    'vendor_id': 'supplier',                     # Vendor -> Supplier (via lookup)
    'vendor_name': 'supplier_name',              # Vendor name
    'bill_number': 'bill_no',                    # Bill number
    'bill_date': 'bill_date',                    # Bill date
    'description': 'remarks',                    # Description/remarks
    'gst_percentage': 'custom_gst_percentage',   # GST percentage
    'created_at': None,                          # Creation timestamp (info only)
    'updated_at': None,                          # Update timestamp (info only)
}

# Status mappings between systems
STATUS_MAPPING_ERPNEXT_TO_PROCUREUAT = {
    'Draft': 'pending',
    'Submitted': 'pending',
    'Paid': 'paid',
    'Partly Paid': 'partially_paid',
    'Overdue': 'overdue',
    'Cancelled': 'cancelled',
    'Return': 'cancelled',
    'Unpaid': 'pending'
}

STATUS_MAPPING_PROCUREUAT_TO_ERPNEXT = {
    'pending': 'Submitted',
    'paid': 'Paid',
    'partially_paid': 'Partly Paid',
    'overdue': 'Overdue',
    'cancelled': 'Cancelled',
    'draft': 'Draft'
}

# Company mapping (ERPNext to ProcureUAT)
COMPANY_MAPPING = {
    # Add your company mappings here
    # 'ERPNext Company Name': 'ProcureUAT Entity ID'
}

# Supplier to Vendor ID mappings
SUPPLIER_VENDOR_MAPPING = {}  # Will be populated dynamically

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
                    WHERE vname = %s OR email = %s 
                    LIMIT 1
                """, (supplier_name, supplier_doc.email_id or ''))
                
                result = cursor.fetchone()
                if result:
                    vendor_id = result['id']
                    
                    # Update supplier with vendor ID for future reference
                    supplier_doc.custom_external_vendor_id = vendor_id
                    supplier_doc.save(ignore_permissions=True)
                    frappe.db.commit()
                    
                    return vendor_id
        
        return None
        
    except Exception as e:
        frappe.logger().error(f"Error getting vendor ID for supplier {supplier_name}: {str(e)}")
        return None

def get_supplier_from_vendor_id(vendor_id):
    """
    Get ERPNext supplier from ProcureUAT vendor ID
    """
    if not vendor_id:
        return None
        
    try:
        # First check if any supplier has this vendor ID
        suppliers = frappe.get_all("Supplier", 
                                 filters={"custom_external_vendor_id": vendor_id},
                                 fields=["name"])
        
        if suppliers:
            return suppliers[0].name
        
        # If not found, lookup vendor details and create/match supplier
        from o2o_erpnext.config.external_db import get_external_db_connection
        
        with get_external_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT vname, email, gstn, address 
                    FROM vendors 
                    WHERE id = %s
                """, (vendor_id,))
                
                vendor = cursor.fetchone()
                if vendor:
                    # Try to find existing supplier by name or email
                    supplier_name = None
                    
                    if vendor['vname']:
                        existing = frappe.get_all("Supplier",
                                                filters={"supplier_name": vendor['vname']},
                                                fields=["name"])
                        if existing:
                            supplier_name = existing[0].name
                    
                    if not supplier_name and vendor['email']:
                        existing = frappe.get_all("Supplier",
                                                filters={"email_id": vendor['email']},
                                                fields=["name"])
                        if existing:
                            supplier_name = existing[0].name
                    
                    if supplier_name:
                        # Update existing supplier with vendor ID
                        supplier_doc = frappe.get_doc("Supplier", supplier_name)
                        supplier_doc.custom_external_vendor_id = vendor_id
                        supplier_doc.save(ignore_permissions=True)
                        frappe.db.commit()
                        return supplier_name
        
        return None
        
    except Exception as e:
        frappe.logger().error(f"Error getting supplier for vendor ID {vendor_id}: {str(e)}")
        return None

def map_erpnext_to_procureuat(doc):
    """
    Map ERPNext Purchase Invoice document to ProcureUAT invoice data
    
    Args:
        doc: ERPNext Purchase Invoice document
        
    Returns:
        dict: Mapped data for ProcureUAT
    """
    try:
        mapped_data = {}
        
        for erpnext_field, procureuat_field in ERPNEXT_TO_PROCUREUAT_MAPPING.items():
            if hasattr(doc, erpnext_field):
                value = getattr(doc, erpnext_field)
                
                # Handle special field mappings
                if erpnext_field == 'supplier':
                    # Convert supplier to vendor_id
                    mapped_data['vendor_id'] = get_vendor_id_from_supplier(value)
                elif erpnext_field == 'status':
                    # Convert status
                    mapped_data[procureuat_field] = STATUS_MAPPING_ERPNEXT_TO_PROCUREUAT.get(value, 'pending')
                elif erpnext_field in ['posting_date', 'due_date', 'bill_date']:
                    # Convert dates to string format
                    if value:
                        mapped_data[procureuat_field] = str(getdate(value))
                elif erpnext_field == 'custom_external_invoice_id':
                    # Only include if it exists and is not 0
                    if value and value != 0:
                        mapped_data[procureuat_field] = value
                else:
                    # Direct mapping
                    if value is not None:
                        mapped_data[procureuat_field] = value
        
        # Add additional fields
        mapped_data['sync_source'] = 'erpnext'
        mapped_data['last_sync'] = frappe.utils.now()
        
        return mapped_data
        
    except Exception as e:
        frappe.logger().error(f"Error mapping ERPNext to ProcureUAT: {str(e)}")
        return {}

def map_procureuat_to_erpnext(invoice_data):
    """
    Map ProcureUAT invoice data to ERPNext Purchase Invoice fields
    
    Args:
        invoice_data (dict): ProcureUAT invoice data
        
    Returns:
        dict: Mapped data for ERPNext
    """
    try:
        mapped_data = {}
        
        for procureuat_field, erpnext_field in PROCUREUAT_TO_ERPNEXT_MAPPING.items():
            if erpnext_field and procureuat_field in invoice_data:
                value = invoice_data[procureuat_field]
                
                # Handle special field mappings
                if procureuat_field == 'vendor_id':
                    # Convert vendor_id to supplier
                    mapped_data['supplier'] = get_supplier_from_vendor_id(value)
                elif procureuat_field == 'payment_status':
                    # Convert status
                    mapped_data[erpnext_field] = STATUS_MAPPING_PROCUREUAT_TO_ERPNEXT.get(value, 'Draft')
                elif procureuat_field in ['invoice_date', 'due_date', 'bill_date']:
                    # Convert dates
                    if value:
                        mapped_data[erpnext_field] = getdate(value)
                else:
                    # Direct mapping
                    if value is not None:
                        mapped_data[erpnext_field] = value
        
        return mapped_data
        
    except Exception as e:
        frappe.logger().error(f"Error mapping ProcureUAT to ERPNext: {str(e)}")
        return {}

def get_procureuat_table_schema():
    """
    Get the expected ProcureUAT invoices table schema
    Used for validation and documentation
    """
    return {
        'table_name': 'invoices',
        'fields': {
            'id': 'INT AUTO_INCREMENT PRIMARY KEY',
            'invoice_number': 'VARCHAR(100)',
            'invoice_date': 'DATE',
            'due_date': 'DATE', 
            'total_amount': 'DECIMAL(15,2)',
            'invoice_amount': 'DECIMAL(15,2)',
            'gst_amount': 'DECIMAL(15,2)',
            'gst_percentage': 'DECIMAL(5,2)',
            'payment_status': 'VARCHAR(50)',
            'vendor_id': 'INT',
            'vendor_name': 'VARCHAR(255)',
            'bill_number': 'VARCHAR(100)',
            'bill_date': 'DATE',
            'description': 'TEXT',
            'sync_source': 'VARCHAR(50)',
            'last_sync': 'DATETIME',
            'created_at': 'DATETIME',
            'updated_at': 'DATETIME'
        }
    }

def validate_mapping_data(data, mapping_type="erpnext_to_procureuat"):
    """
    Validate mapped data before sync
    
    Args:
        data (dict): Mapped data
        mapping_type (str): Type of mapping validation
        
    Returns:
        tuple: (is_valid, error_message)
    """
    try:
        if mapping_type == "erpnext_to_procureuat":
            # Required fields for ProcureUAT
            required_fields = ['invoice_number', 'invoice_date', 'total_amount']
            
            for field in required_fields:
                if not data.get(field):
                    return False, f"Required field '{field}' is missing or empty"
            
            # Validate vendor_id
            if not data.get('vendor_id'):
                return False, "Vendor ID is required but not found. Please ensure supplier is mapped to a vendor."
                
        elif mapping_type == "procureuat_to_erpnext":
            # Required fields for ERPNext
            required_fields = ['supplier', 'posting_date']
            
            for field in required_fields:
                if not data.get(field):
                    return False, f"Required field '{field}' is missing or empty"
        
        return True, "Validation successful"
        
    except Exception as e:
        return False, f"Validation error: {str(e)}"