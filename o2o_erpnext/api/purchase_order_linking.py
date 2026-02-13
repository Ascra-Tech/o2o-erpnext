import frappe
from frappe import _

@frappe.whitelist()
def get_linked_purchase_receipt(purchase_order_name):
    """
    Get the first Purchase Receipt linked to a Purchase Order
    Uses elevated permissions to query Purchase Receipt Items
    """
    try:
        if not purchase_order_name:
            return {
                "success": False,
                "message": "Purchase Order name is required",
                "purchase_receipt": None
            }
        
        # Query Purchase Receipt Items with elevated permissions using direct SQL
        linked_receipts = frappe.db.sql("""
            SELECT pri.parent as purchase_receipt_name
            FROM `tabPurchase Receipt Item` pri
            INNER JOIN `tabPurchase Receipt` pr ON pri.parent = pr.name
            WHERE pri.purchase_order = %s
            AND pr.docstatus IN (0, 1)
            ORDER BY pr.creation DESC
            LIMIT 1
        """, purchase_order_name, as_dict=1)
        
        if linked_receipts and len(linked_receipts) > 0:
            receipt_name = linked_receipts[0].purchase_receipt_name
            return {
                "success": True,
                "message": f"Found linked Purchase Receipt: {receipt_name}",
                "purchase_receipt": receipt_name
            }
        else:
            return {
                "success": True,
                "message": "No linked Purchase Receipts found",
                "purchase_receipt": None
            }
            
    except Exception as e:
        frappe.log_error(f"Error getting linked Purchase Receipt for PO {purchase_order_name}: {str(e)}", 
                        "Get Linked Purchase Receipt Error")
        return {
            "success": False,
            "message": f"Error querying linked Purchase Receipts: {str(e)}",
            "purchase_receipt": None
        }

@frappe.whitelist()
def get_linked_purchase_invoices(purchase_order_name):
    """
    Get linked Purchase Invoices for a Purchase Order with elevated permissions
    """
    try:
        if not purchase_order_name:
            return {"success": False, "message": "Purchase Order name is required"}
        
        # Use direct SQL query to bypass permission restrictions
        query = """
            SELECT DISTINCT pi.name as purchase_invoice
            FROM `tabPurchase Invoice Item` pii
            INNER JOIN `tabPurchase Invoice` pi ON pii.parent = pi.name
            WHERE pii.purchase_order = %s
            AND pi.docstatus = 1
            ORDER BY pi.creation DESC
            LIMIT 1
        """
        
        result = frappe.db.sql(query, (purchase_order_name,), as_dict=True)
        
        if result:
            return {
                "success": True, 
                "purchase_invoice": result[0].purchase_invoice
            }
        else:
            return {
                "success": True, 
                "purchase_invoice": None,
                "message": "No linked Purchase Invoices found"
            }
            
    except Exception as e:
        frappe.log_error(f"Error in get_linked_purchase_invoices: {str(e)}")
        return {
            "success": False, 
            "message": f"Error querying linked Purchase Invoices: {str(e)}"
        }

@frappe.whitelist()
def debug_purchase_receipt_links(purchase_order_name):
    """
    Debug function to check Purchase Receipt Item links
    """
    try:
        # Check Purchase Receipt Items
        pri_query = """
            SELECT pri.name, pri.parent, pri.purchase_order, pr.docstatus, pr.name as pr_name
            FROM `tabPurchase Receipt Item` pri
            LEFT JOIN `tabPurchase Receipt` pr ON pri.parent = pr.name
            WHERE pri.purchase_order = %s
        """
        
        pri_result = frappe.db.sql(pri_query, (purchase_order_name,), as_dict=True)
        
        return {
            "success": True,
            "purchase_receipt_items": pri_result,
            "count": len(pri_result)
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@frappe.whitelist()
def update_purchase_receipt_field_for_submitted_po(purchase_order_name):
    """
    Update custom_purchase_receipt field for submitted Purchase Orders only
    Finds the first linked Purchase Receipt and saves it to the field
    """
    try:
        if not purchase_order_name:
            return {"success": False, "message": "Purchase Order name is required"}
        
        # Get the Purchase Order document
        po_doc = frappe.get_doc("Purchase Order", purchase_order_name)
        
        # Only process submitted Purchase Orders
        if po_doc.docstatus != 1:
            return {
                "success": False, 
                "message": f"Purchase Order {purchase_order_name} is not submitted (docstatus: {po_doc.docstatus})"
            }
        
        # Use direct SQL query to find linked Purchase Receipts (both draft and submitted)
        query = """
            SELECT DISTINCT pr.name as purchase_receipt, pr.docstatus
            FROM `tabPurchase Receipt Item` pri
            INNER JOIN `tabPurchase Receipt` pr ON pri.parent = pr.name
            WHERE pri.purchase_order = %s
            AND pr.docstatus IN (0, 1)
            ORDER BY pr.docstatus DESC, pr.creation ASC
            LIMIT 1
        """
        
        result = frappe.db.sql(query, (purchase_order_name,), as_dict=True)
        
        if result:
            purchase_receipt_name = result[0].purchase_receipt
            
            # Check if field already has the correct value
            if po_doc.custom_purchase_receipt == purchase_receipt_name:
                return {
                    "success": True,
                    "message": f"Field already has correct value: {purchase_receipt_name}",
                    "purchase_receipt": purchase_receipt_name,
                    "updated": False
                }
            
            # Update the field directly in database (bypass validation for submitted docs)
            frappe.db.set_value("Purchase Order", purchase_order_name, "custom_purchase_receipt", purchase_receipt_name)
            frappe.db.commit()
            
            return {
                "success": True,
                "message": f"Updated custom_purchase_receipt field with: {purchase_receipt_name}",
                "purchase_receipt": purchase_receipt_name,
                "updated": True
            }
        else:
            return {
                "success": True,
                "message": "No linked Purchase Receipts found",
                "purchase_receipt": None,
                "updated": False
            }
            
    except Exception as e:
        frappe.log_error(f"Error in update_purchase_receipt_field_for_submitted_po: {str(e)}")
        return {
            "success": False, 
            "message": f"Error updating Purchase Receipt field: {str(e)}"
        }

# ===== AUTOMATIC HOOKS FOR PURCHASE RECEIPT EVENTS =====

def update_linked_purchase_orders_on_receipt_create(doc, method):
    """
    Hook: Called when a Purchase Receipt is created (after_insert)
    Updates custom_purchase_receipt field in linked Purchase Orders
    """
    try:
        _update_linked_purchase_orders_from_receipt(doc, "created")
    except Exception as e:
        frappe.log_error(f"Error in update_linked_purchase_orders_on_receipt_create: {str(e)}")

def update_linked_purchase_orders_on_receipt_submit(doc, method):
    """
    Hook: Called when a Purchase Receipt is submitted (on_submit)
    Updates custom_purchase_receipt field in linked Purchase Orders
    """
    try:
        _update_linked_purchase_orders_from_receipt(doc, "submitted")
    except Exception as e:
        frappe.log_error(f"Error in update_linked_purchase_orders_on_receipt_submit: {str(e)}")

def update_linked_purchase_orders_on_receipt_cancel(doc, method):
    """
    Hook: Called when a Purchase Receipt is cancelled (on_cancel)
    Clears custom_purchase_receipt field in linked Purchase Orders if this was the linked receipt
    """
    try:
        _update_linked_purchase_orders_from_receipt(doc, "cancelled")
    except Exception as e:
        frappe.log_error(f"Error in update_linked_purchase_orders_on_receipt_cancel: {str(e)}")

def _update_linked_purchase_orders_from_receipt(receipt_doc, action):
    """
    Helper function to update linked Purchase Orders when Purchase Receipt changes
    """
    if not receipt_doc or not receipt_doc.items:
        return
    
    # Get unique Purchase Orders linked to this Purchase Receipt
    linked_pos = set()
    for item in receipt_doc.items:
        if item.purchase_order:
            linked_pos.add(item.purchase_order)
    
    if not linked_pos:
        return
    
    # Update each linked Purchase Order
    for po_name in linked_pos:
        try:
            # Get the Purchase Order
            po_doc = frappe.get_doc("Purchase Order", po_name)
            
            # Only update submitted Purchase Orders
            if po_doc.docstatus != 1:
                continue
            
            if action == "cancelled":
                # If this receipt was cancelled, check if it was the linked one and clear if needed
                if po_doc.custom_purchase_receipt == receipt_doc.name:
                    # Find another linked receipt to replace it
                    replacement_receipt = _find_replacement_receipt(po_name, receipt_doc.name)
                    new_value = replacement_receipt if replacement_receipt else ""
                    
                    if po_doc.custom_purchase_receipt != new_value:
                        frappe.db.set_value("Purchase Order", po_name, "custom_purchase_receipt", new_value)
                        frappe.db.commit()
            else:
                # For create/submit actions, update with the first available receipt
                result = update_purchase_receipt_field_for_submitted_po(po_name)
                # Log success/failure if needed
                
        except Exception as e:
            frappe.log_error(f"Error updating Purchase Order {po_name} from receipt {receipt_doc.name}: {str(e)}")

def _find_replacement_receipt(purchase_order_name, excluded_receipt_name):
    """
    Find a replacement Purchase Receipt for a Purchase Order (excluding the specified one)
    """
    try:
        query = """
            SELECT DISTINCT pr.name as purchase_receipt
            FROM `tabPurchase Receipt Item` pri
            INNER JOIN `tabPurchase Receipt` pr ON pri.parent = pr.name
            WHERE pri.purchase_order = %s
            AND pr.name != %s
            AND pr.docstatus IN (0, 1)
            ORDER BY pr.docstatus DESC, pr.creation ASC
            LIMIT 1
        """
        
        result = frappe.db.sql(query, (purchase_order_name, excluded_receipt_name), as_dict=True)
        
        if result:
            return result[0].purchase_receipt
        return None
        
    except Exception as e:
        frappe.log_error(f"Error finding replacement receipt: {str(e)}")
        return None
