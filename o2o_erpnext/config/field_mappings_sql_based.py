"""
Definitive Field Mappings Configuration for ERPNext <-> ProcureUAT Sync
Based on actual SQL dump schema analysis
Generated from procureuat.sql dump dated 2025-09-24
"""

import frappe
from frappe.utils import getdate, get_datetime, flt
from datetime import datetime

# =============================================================================
# PROCUREUAT DATABASE SCHEMA (from actual SQL dump)
# =============================================================================

# purchase_requisitions table (647 records) - Main invoice/order header
PURCHASE_REQUISITIONS_SCHEMA = {
    'id': 'int(11) AUTO_INCREMENT PRIMARY KEY',
    'entity': 'varchar(255) NOT NULL',                      # Entity/Company ID
    'subentity_id': 'varchar(255)',                         # Sub-entity ID
    'order_name': 'varchar(255) NOT NULL',                  # Order identifier
    'delivery_date': 'datetime',                            # Delivery date
    'validity_date': 'datetime',                            # Validity date
    'order_code': 'varchar(255) NOT NULL',                  # Order code
    'address': 'text NOT NULL',                             # Address
    'remark': 'text NOT NULL',                              # Remarks/description
    'acknowledgement': 'int(11) DEFAULT 0',                 # 1=Approve, 2=Reject
    'gru_ack': 'int(11) DEFAULT 0',                         # GRU acknowledgement
    'gru_ack_remark': 'varchar(150)',                       # GRU remark
    'currency_id': 'int(11)',                               # Currency ID
    'category': 'int(11) NOT NULL',                         # Category
    'amend_no': 'varchar(200) NOT NULL',                    # Amendment number
    'amendment_date': 'datetime',                           # Amendment date
    'order_status': 'int(11) DEFAULT 1',                    # 1=Awaiting, 2=Approve, 3=Reject, 4=Req Approve, 5=Req Reject
    'finance_status': 'int(11) DEFAULT 0',                  # Finance status
    'reason_id': 'int(11)',                                 # Reason ID
    'reason': 'varchar(255) NOT NULL',                      # Reason text
    'clone_id': 'int(11) DEFAULT 0',                        # Clone ID
    'is_delete': 'int(11) DEFAULT 0',                       # Deletion flag
    'status': 'varchar(50) NOT NULL',                       # Status
    'dispatch_status': 'varchar(100)',                      # Dispatch status
    'transportation_mode': 'varchar(100) NOT NULL',         # Transport mode
    'vehicle_no': 'varchar(100) NOT NULL',                  # Vehicle number
    'challan_number': 'varchar(100) NOT NULL',              # Challan number
    'challan_date': 'datetime',                             # Challan date
    'awb_number': 'varchar(250)',                           # AWB number
    'weight': 'varchar(150)',                               # Weight
    'weight_rate': 'varchar(150)',                          # Weight rate
    'freight_rate': 'varchar(150) NOT NULL',                # Freight rate
    'freight_cost': 'varchar(150) NOT NULL',                # Freight cost
    'total_wt': 'float',                                    # Total weight
    'adv_shipping_detatils': 'varchar(250)',                # Shipping details
    'import_files': 'varchar(255)',                         # Import files
    'user_file_name': 'varchar(255)',                       # User file name
    'approved_at': 'datetime',                              # Approval date
    'approved_by': 'int(11)',                               # Approved by user
    'requisition_at': 'datetime NOT NULL',                  # Requisition date
    'requisition_by': 'int(11) NOT NULL',                   # Requisition by user
    'rejected_at': 'datetime',                              # Rejection date
    'rejected_by': 'int(11)',                               # Rejected by user
    'invoice_view': 'varchar(255)',                         # Invoice view
    'invoice_series': 'int(11) NOT NULL',                   # Invoice series
    'invoice_number': 'varchar(255)',                       # Invoice number
    'invoice_generated': 'int(11) DEFAULT 0',               # Invoice generated flag
    'invoice_generated_at': 'datetime',                     # Invoice generation date
    'is_visible_header': 'tinyint(1) NOT NULL',             # Visible header flag
    'created_at': 'datetime',                               # Creation date
    'created_by': 'int(11) NOT NULL',                       # Created by user
    'vendor_created': 'int(11) DEFAULT 0',                  # Vendor created flag
    'updated_at': 'datetime',                               # Update date
    'updated_by': 'int(11) NOT NULL',                       # Updated by user
    'gst_percentage': 'varchar(2) DEFAULT "5"',             # GST percentage
    'is_new_invoice': 'tinyint(4) DEFAULT 0',               # New invoice flag
    'is_invoice_cancel': 'tinyint(4) DEFAULT 0',            # Invoice cancel flag
    'invoice_cancel_date': 'datetime',                      # Invoice cancel date
    'credit_note_number': 'varchar(100) NOT NULL',         # Credit note number
}

# purchase_order_items table (1702 records) - Invoice line items
PURCHASE_ORDER_ITEMS_SCHEMA = {
    'id': 'int(11) AUTO_INCREMENT PRIMARY KEY',
    'purchase_order_id': 'int(11) NOT NULL',                # Links to purchase_requisitions.id
    'category_id': 'int(11)',                               # Category ID
    'subcategory_id': 'int(11)',                            # Subcategory ID
    'product_id': 'int(11)',                                # Product ID
    'vendor_id': 'int(11)',                                 # Vendor ID
    'brand_id': 'int(11) NOT NULL',                         # Brand ID
    'image': 'text NOT NULL',                               # Product image
    'quantity': 'bigint(20)',                               # Quantity
    'unit_rate': 'varchar(100)',                            # Unit rate/price
    'uom': 'varchar(100)',                                  # Unit of measure
    'unit': 'varchar(200)',                                 # Unit description
    'unit_type': 'varchar(200)',                            # Unit type
    'product_type': 'int(11)',                              # Product type
    'gst_id': 'int(11)',                                    # GST ID
    'total_amt': 'float',                                   # Total amount (with GST)
    'gst_amt': 'float',                                     # GST amount
    'cost': 'float',                                        # Cost (without GST)
    'status': 'varchar(50) NOT NULL',                       # Status
    'vendor_approve': 'int(11) DEFAULT 1',                  # Vendor approval
    'created_at': 'datetime',                               # Creation date
    'created_by': 'int(11) NOT NULL',                       # Created by user
    'updated_at': 'datetime',                               # Update date
    'updated_by': 'int(11) NOT NULL',                       # Updated by user
}

# vendors table (3 records) - Supplier information
VENDORS_SCHEMA = {
    'id': 'int(11) AUTO_INCREMENT PRIMARY KEY',
    'name': 'varchar(255) NOT NULL',                        # Vendor name
    'code': 'varchar(150) NOT NULL',                        # Vendor code
    'website': 'varchar(255) NOT NULL',                     # Website
    'contact_number': 'bigint(20) NOT NULL',                # Contact number
    'country_id': 'int(11) NOT NULL',                       # Country ID
    'state_id': 'int(11) NOT NULL',                         # State ID
    'city_id': 'int(11) NOT NULL',                          # City ID
    'pincode': 'varchar(100) NOT NULL',                     # PIN code
    'address': 'varchar(255) NOT NULL',                     # Address
    'email': 'varchar(255) NOT NULL',                       # Email
    'encrypted_password': 'varchar(255) NOT NULL',          # Encrypted password
    'confirm_password': 'varchar(255) NOT NULL',            # Confirm password
    'password': 'varchar(255) NOT NULL',                    # Password
    'vendor_logo': 'varchar(255) NOT NULL',                 # Vendor logo
    'last_sign_in_at': 'datetime NOT NULL',                 # Last sign in
    'last_sign_in_ip': 'varchar(255) NOT NULL',             # Last sign in IP
    'gstn': 'varchar(100)',                                 # GSTN number
    'user_id': 'int(11) NOT NULL',                          # User ID
    'status': 'varchar(50) NOT NULL',                       # Status
    'created_at': 'datetime',                               # Creation date
    'created_by': 'int(11) NOT NULL',                       # Created by user
    'updated_at': 'datetime',                               # Update date
    'updated_by': 'int(11) NOT NULL',                       # Updated by user
}

# =============================================================================
# FIELD MAPPINGS FOR SYNC
# =============================================================================

# ERPNext Purchase Invoice -> ProcureUAT purchase_requisitions
ERPNEXT_TO_PROCUREUAT_REQUISITIONS = {
    'name': 'order_name',                                   # Invoice ID -> Order name
    'posting_date': 'created_at',                           # Posting date -> Created at
    'due_date': 'delivery_date',                            # Due date -> Delivery date
    'supplier': None,                                       # Handle via entity mapping
    'supplier_name': None,                                  # Handle via vendor lookup
    'bill_no': 'invoice_number',                            # Bill number -> Invoice number
    'bill_date': 'invoice_generated_at',                    # Bill date -> Invoice generated at
    'remarks': 'remark',                                    # Remarks -> Remark
    'status': 'order_status',                               # Status -> Order status (needs conversion)
    'docstatus': 'acknowledgement',                         # Document status -> Acknowledgement
    'grand_total': None,                                    # Calculate from items
    'net_total': None,                                      # Calculate from items
    'total_taxes_and_charges': None,                        # Calculate from items
    'custom_gst_percentage': 'gst_percentage',              # GST percentage
    'custom_external_order_id': 'id',                       # External order ID
    'custom_order_code': 'order_code',                      # Order code
    'custom_entity_id': 'entity',                           # Entity ID
}

# ERPNext Purchase Invoice Items -> ProcureUAT purchase_order_items
ERPNEXT_TO_PROCUREUAT_ITEMS = {
    'item_code': 'product_id',                              # Item code -> Product ID (via lookup)
    'item_name': None,                                      # Handle via product lookup
    'qty': 'quantity',                                      # Quantity
    'rate': 'unit_rate',                                    # Rate -> Unit rate
    'amount': 'cost',                                       # Amount -> Cost (before GST)
    'base_amount': 'total_amt',                             # Base amount -> Total amount (with GST)
    'uom': 'uom',                                           # Unit of measure
    'custom_gst_amount': 'gst_amt',                         # GST amount
    'custom_vendor_id': 'vendor_id',                        # Vendor ID
    'custom_category_id': 'category_id',                    # Category ID
    'custom_subcategory_id': 'subcategory_id',              # Subcategory ID
}

# ProcureUAT purchase_requisitions -> ERPNext Purchase Invoice
PROCUREUAT_TO_ERPNEXT_REQUISITIONS = {
    'id': 'custom_external_order_id',                       # Order ID -> External order ID
    'order_name': 'name',                                   # Order name -> Invoice name (prefix with PINV-)
    'created_at': 'posting_date',                           # Created at -> Posting date
    'delivery_date': 'due_date',                            # Delivery date -> Due date
    'entity': None,                                         # Handle via supplier lookup
    'invoice_number': 'bill_no',                            # Invoice number -> Bill number
    'invoice_generated_at': 'bill_date',                    # Invoice generated at -> Bill date
    'remark': 'remarks',                                    # Remark -> Remarks
    'order_status': 'status',                               # Order status -> Status (needs conversion)
    'acknowledgement': 'docstatus',                         # Acknowledgement -> Document status
    'gst_percentage': 'custom_gst_percentage',              # GST percentage
    'order_code': 'custom_order_code',                      # Order code
    'approved_at': None,                                    # Info only
    'approved_by': None,                                    # Info only
}

# ProcureUAT purchase_order_items -> ERPNext Purchase Invoice Items
PROCUREUAT_TO_ERPNEXT_ITEMS = {
    'id': 'custom_external_item_id',                        # Item ID -> External item ID
    'product_id': 'item_code',                              # Product ID -> Item code (via lookup)
    'quantity': 'qty',                                      # Quantity
    'unit_rate': 'rate',                                    # Unit rate -> Rate
    'cost': 'amount',                                       # Cost -> Amount (before GST)
    'total_amt': 'base_amount',                             # Total amount -> Base amount (with GST)
    'gst_amt': 'custom_gst_amount',                         # GST amount
    'uom': 'uom',                                           # Unit of measure
    'vendor_id': 'custom_vendor_id',                        # Vendor ID
    'category_id': 'custom_category_id',                    # Category ID
    'subcategory_id': 'custom_subcategory_id',              # Subcategory ID
}

# =============================================================================
# STATUS MAPPINGS
# =============================================================================

# ERPNext Status -> ProcureUAT order_status
STATUS_MAPPING_ERPNEXT_TO_PROCUREUAT = {
    'Draft': 1,                                             # Awaiting Approval
    'Submitted': 2,                                         # Approved
    'Paid': 2,                                              # Approved
    'Cancelled': 3,                                         # Rejected
    'Return': 5,                                            # Requisition Rejected
}

# ProcureUAT order_status -> ERPNext Status
STATUS_MAPPING_PROCUREUAT_TO_ERPNEXT = {
    1: 'Draft',                                             # Awaiting Approval -> Draft
    2: 'Submitted',                                         # Approved -> Submitted
    3: 'Cancelled',                                         # Rejected -> Cancelled
    4: 'Submitted',                                         # Requisition Approved -> Submitted
    5: 'Cancelled',                                         # Requisition Rejected -> Cancelled
}

# ERPNext docstatus -> ProcureUAT acknowledgement
DOCSTATUS_MAPPING_ERPNEXT_TO_PROCUREUAT = {
    0: 0,                                                   # Draft -> Not acknowledged
    1: 1,                                                   # Submitted -> Approved
    2: 2,                                                   # Cancelled -> Rejected
}

# ProcureUAT acknowledgement -> ERPNext docstatus
DOCSTATUS_MAPPING_PROCUREUAT_TO_ERPNEXT = {
    0: 0,                                                   # Not acknowledged -> Draft
    1: 1,                                                   # Approved -> Submitted
    2: 2,                                                   # Rejected -> Cancelled
}

# =============================================================================
# VENDOR DATA (from actual SQL dump)
# =============================================================================

VENDOR_DATA = {
    1: {
        'name': 'AGO2O STORES LLP',
        'code': 'O2O001',
        'email': 'vendor@gmail.com',
        'gstn': '27ABSFA3175F1Z8',
        'address': '218, Goldcrest Business Park opposite Shreya\'s cinema Ghatkopar west 400086',
        'website': 'https://o2o.ind.in',
        'contact_number': 1234567896,
        'status': 'active'
    },
    2: {
        'name': 'MiceBugs Private Limited', 
        'code': 'CRE001',
        'email': 'Info@micebugs.com',
        'gstn': '27AAQCM6888DIZS',
        'address': '218, Goldcrest Buiness Park opposite shreyas cinema ghatkopar west 400086',
        'website': 'www.micebugs.com',
        'contact_number': 9885687452,
        'status': 'active'
    }
}

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_vendor_id_from_supplier(supplier_name):
    """
    Get ProcureUAT vendor ID from ERPNext supplier name
    Uses custom field or database lookup
    """
    if not supplier_name:
        return None
        
    try:
        # First check if supplier has external vendor ID
        if frappe.db.exists("Supplier", supplier_name):
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
                    if frappe.db.exists("Supplier", supplier_name):
                        supplier_doc = frappe.get_doc("Supplier", supplier_name)
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
        
        # If not found, use vendor data from our mapping or database lookup
        if vendor_id in VENDOR_DATA:
            vendor = VENDOR_DATA[vendor_id]
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

def get_entity_from_supplier(supplier_name):
    """
    Get ProcureUAT entity ID from ERPNext supplier
    """
    # For now, map to default entities (can be enhanced with actual entity mapping)
    vendor_id = get_vendor_id_from_supplier(supplier_name)
    if vendor_id == 1:  # AGO2O STORES LLP
        return "2"  # Entity 2 based on sample data
    elif vendor_id == 2:  # MiceBugs Private Limited
        return "1"  # Entity 1 based on sample data
    else:
        return "1"  # Default entity

def convert_erpnext_status_to_procureuat(erpnext_status):
    """Convert ERPNext status to ProcureUAT order_status"""
    return STATUS_MAPPING_ERPNEXT_TO_PROCUREUAT.get(erpnext_status, 1)

def convert_procureuat_status_to_erpnext(procureuat_status):
    """Convert ProcureUAT order_status to ERPNext status"""
    return STATUS_MAPPING_PROCUREUAT_TO_ERPNEXT.get(procureuat_status, 'Draft')

def convert_erpnext_docstatus_to_procureuat(docstatus):
    """Convert ERPNext docstatus to ProcureUAT acknowledgement"""
    return DOCSTATUS_MAPPING_ERPNEXT_TO_PROCUREUAT.get(docstatus, 0)

def convert_procureuat_acknowledgement_to_erpnext(acknowledgement):
    """Convert ProcureUAT acknowledgement to ERPNext docstatus"""
    return DOCSTATUS_MAPPING_PROCUREUAT_TO_ERPNEXT.get(acknowledgement, 0)

def calculate_totals_from_items(items_data):
    """
    Calculate grand total, net total, and tax total from items
    """
    net_total = sum(flt(item.get('cost', 0)) for item in items_data)
    tax_total = sum(flt(item.get('gst_amt', 0)) for item in items_data)
    grand_total = net_total + tax_total
    
    return {
        'net_total': net_total,
        'total_taxes_and_charges': tax_total,
        'grand_total': grand_total
    }

def generate_erpnext_invoice_name(order_name):
    """
    Generate ERPNext Purchase Invoice name from ProcureUAT order name
    """
    return f"PINV-{order_name}"

def generate_procureuat_order_name(invoice_name):
    """
    Generate ProcureUAT order name from ERPNext invoice name
    """
    if invoice_name.startswith("PINV-"):
        return invoice_name[5:]  # Remove PINV- prefix
    return invoice_name