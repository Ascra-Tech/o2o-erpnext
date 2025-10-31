# apps/o2o_erpnext/o2o_erpnext/api/purchase_invoice_controller.py

import frappe
import json
from frappe import _
from frappe.model.document import Document

def validate_remote_duplicate_on_submit(doc, method=None):
    """
    Validate Purchase Invoice against remote database duplicates before submission

    This function checks the remote ProcureUAT database for existing purchase_requisitions
    with matching invoice_number or order_code to prevent duplicate submissions.

    Args:
        doc: Purchase Invoice document being submitted
        method: Hook method (on_submit)
    """
    # Only validate on submission (docstatus = 1)
    if doc.docstatus != 1:
        return
        
    try:
        # Import here to avoid circular imports
        from o2o_erpnext.config.external_db_updated import get_external_db_connection
        
        # Get Purchase Invoice details for checking
        invoice_name = doc.name  # ERPNext invoice number (e.g., CINV-24-00001)
        supplier_invoice = doc.bill_no  # Supplier invoice number
        
        frappe.logger().info(f"🔍 Checking remote duplicates for Invoice: {invoice_name}, Supplier Invoice: {supplier_invoice}")
        
        with get_external_db_connection() as conn:
            with conn.cursor() as cursor:
                # Check for duplicates by order_code (ERPNext invoice number)
                cursor.execute("""
                    SELECT id, order_code, invoice_number, order_name, created_at 
                    FROM purchase_requisitions 
                    WHERE order_code = %s AND is_delete = 0
                    LIMIT 1
                """, (invoice_name,))
                
                order_code_duplicate = cursor.fetchone()
                
                # Check for duplicates by invoice_number (supplier invoice number)
                invoice_number_duplicate = None
                if supplier_invoice:
                    cursor.execute("""
                        SELECT id, order_code, invoice_number, order_name, created_at 
                        FROM purchase_requisitions 
                        WHERE invoice_number = %s AND is_delete = 0
                        LIMIT 1
                    """, (supplier_invoice,))
                    
                    invoice_number_duplicate = cursor.fetchone()
                
                # If any duplicates found, block submission
                if order_code_duplicate or invoice_number_duplicate:
                    error_messages = []
                    
                    if order_code_duplicate:
                        dup = order_code_duplicate
                        created_date = dup['created_at'].strftime('%Y-%m-%d %H:%M') if dup['created_at'] else 'Unknown'
                        error_messages.append(
                            f"📋 <strong>ERPNext Invoice Number</strong> '{invoice_name}' already exists in portal<br>"
                            f"&nbsp;&nbsp;&nbsp;&nbsp;Portal ID: {dup['id']}<br>"
                            f"&nbsp;&nbsp;&nbsp;&nbsp;Order Name: {dup['order_name'] or 'N/A'}<br>"
                            f"&nbsp;&nbsp;&nbsp;&nbsp;Created: {created_date}"
                        )
                    
                    if invoice_number_duplicate:
                        dup = invoice_number_duplicate
                        created_date = dup['created_at'].strftime('%Y-%m-%d %H:%M') if dup['created_at'] else 'Unknown'
                        error_messages.append(
                            f"🧾 <strong>Supplier Invoice Number</strong> '{supplier_invoice}' already exists in portal<br>"
                            f"&nbsp;&nbsp;&nbsp;&nbsp;Portal ID: {dup['id']}<br>"
                            f"&nbsp;&nbsp;&nbsp;&nbsp;Order Code: {dup['order_code'] or 'N/A'}<br>"
                            f"&nbsp;&nbsp;&nbsp;&nbsp;Created: {created_date}"
                        )
                    
                    # Create user-friendly error message
                    main_message = (
                        f"🚫 <strong>Duplicate Invoice Detected!</strong><br><br>"
                        f"Cannot submit Purchase Invoice because duplicate record(s) found in portal:<br><br>"
                        f"{'<br><br>'.join(error_messages)}<br><br>"
                        f"<strong>🔧 How to Fix:</strong><br>"
                        f"1. Change the Invoice ID (currently: <code>{invoice_name}</code>)<br>"
                        f"2. Or update the Supplier Invoice Number (currently: <code>{supplier_invoice or 'Not Set'}</code>)<br>"
                        f"3. Then try submitting again<br><br>"
                        f"<em>This validation ensures no duplicate invoices are created in the portal system.</em>"
                    )
                    
                    frappe.throw(
                        _(main_message),
                        title=_("🔍 Duplicate Check Failed"),
                        exc=frappe.DuplicateEntryError
                    )
                
                else:
                    # No duplicates found - log success
                    frappe.logger().info(f"✅ No duplicates found for {invoice_name} - submission allowed")
    
    except Exception as e:
        # Log the error but don't block submission for database connectivity issues
        error_msg = str(e)
        frappe.logger().error(f"❌ Remote duplicate check failed for {doc.name}: {error_msg}")
        
        # Only block if it's a duplicate error we threw intentionally
        if isinstance(e, frappe.DuplicateEntryError):
            raise e
        
        # For other errors (connectivity, etc.), show warning but allow submission
        frappe.msgprint(
            _(f"⚠️ <strong>Warning:</strong> Could not verify duplicates in portal database.<br><br>"
              f"<strong>Error:</strong> {error_msg}<br><br>"
              f"<em>Invoice submission will proceed, but please manually verify no duplicates exist in the portal.</em>"),
            title=_("🔗 Portal Connection Warning"),
            indicator="orange"
        )

def create_remote_invoice_on_submit(doc, method=None):
    """
    Create invoice in remote ProcureUAT database on Purchase Invoice submit
    
    Args:
        doc: Purchase Invoice document
        method: Hook method (on_submit)
    """
    # Only process on submit
    if doc.docstatus != 1:
        return
    
    # Skip if external sync is disabled
    if doc.get('custom_skip_external_sync'):
        frappe.msgprint(
            _("⚠️ External sync skipped as requested. Invoice will not be created in portal."),
            title=_("🔗 Portal Sync Skipped"),
            indicator="yellow"
        )
        return
    
    try:
        frappe.logger().info(f"🚀 Creating remote invoice for {doc.name}")
        
        # Import here to avoid circular imports
        from o2o_erpnext.api.remote_invoice_creator import create_remote_invoice
        
        # Create remote invoice
        success, remote_invoice_code, message = create_remote_invoice(doc)
        
        if success:
            # Update ERPNext document with remote details
            doc.custom_portal_sync_id = remote_invoice_code
            doc.custom_sync_status = "Synced"
            doc.save(ignore_permissions=True)
            
            frappe.msgprint(
                _(f"✅ <strong>Invoice Created Successfully!</strong><br><br>"
                  f"<strong>Remote Invoice Code:</strong> {remote_invoice_code}<br>"
                  f"<strong>Message:</strong> {message}<br><br>"
                  f"<em>Invoice has been created in the portal database.</em>"),
                title=_("🎉 Portal Sync Success"),
                indicator="green"
            )
            
        else:
            # Log error but don't block submission
            doc.custom_sync_status = "Failed"
            doc.save(ignore_permissions=True)
            
            frappe.msgprint(
                _(f"⚠️ <strong>Warning:</strong> Invoice submitted successfully but portal sync failed.<br><br>"
                  f"<strong>Error:</strong> {message}<br><br>"
                  f"<em>Please contact administrator to manually sync this invoice.</em>"),
                title=_("🔗 Portal Sync Warning"),
                indicator="orange"
            )
            
    except Exception as e:
        error_msg = str(e)
        frappe.logger().error(f"❌ Remote invoice creation failed for {doc.name}: {error_msg}")
        
        # Don't block submission for sync errors
        frappe.msgprint(
            _(f"⚠️ <strong>Warning:</strong> Invoice submitted but portal creation failed.<br><br>"
              f"<strong>Error:</strong> {error_msg}<br><br>"
              f"<em>Invoice submission completed. Please retry sync manually.</em>"),
            title=_("🔗 Portal Creation Failed"),
            indicator="red"
        )
    
    @staticmethod
    def validate_vendor_user_permissions(doc, method=None):
        """
        Validate that Vendor Users cannot modify items in Draft Purchase Invoices
        """
        # Only check for Draft documents
        if doc.docstatus != 0:
            return
        
        # Check if current user has Vendor User role
        if "Vendor User" not in frappe.get_roles():
            return
        
        # For new documents, allow creation
        if doc.is_new():
            return
        
        # Get the original document from database
        try:
            original_doc = frappe.get_doc("Purchase Invoice", doc.name)
            
            # Check if items have been modified
            if len(doc.items) != len(original_doc.items):
                frappe.throw(
                    _("Vendor Users cannot add or remove items when Purchase Invoice is in Draft status."),
                    title=_("Access Restricted")
                )
            
            # Check for modifications in existing items
            for idx, item in enumerate(doc.items):
                if idx < len(original_doc.items):
                    original_item = original_doc.items[idx]
                    
                    # Check critical fields
                    if item.item_code != original_item.item_code:
                        frappe.throw(
                            _("Vendor Users cannot modify item codes when Purchase Invoice is in Draft status."),
                            title=_("Access Restricted")
                        )
                    
                    if float(item.qty or 0) != float(original_item.qty or 0):
                        frappe.throw(
                            _("Vendor Users cannot modify quantities when Purchase Invoice is in Draft status."),
                            title=_("Access Restricted")
                        )
                    
                    if float(item.rate or 0) != float(original_item.rate or 0):
                        frappe.throw(
                            _("Vendor Users cannot modify rates when Purchase Invoice is in Draft status."),
                            title=_("Access Restricted")
                        )
                    
                    if float(item.amount or 0) != float(original_item.amount or 0):
                        frappe.throw(
                            _("Vendor Users cannot modify amounts when Purchase Invoice is in Draft status."),
                            title=_("Access Restricted")
                        )
                        
        except frappe.DoesNotExistError:
            # Document doesn't exist in DB, it's new
            pass
        except Exception as e:
            if "does not exist" not in str(e):
                frappe.log_error(
                    title="Vendor User Validation Error",
                    message=f"Error validating Purchase Invoice: {str(e)}"
                )


# Class definition moved here
class CustomPurchaseInvoiceController:
    """
    Custom controller to handle Purchase Invoice validations and restrictions
    """
    
    @staticmethod
    def validate_vendor_user_permissions(doc, method=None):
        """
        Validate that Vendor Users cannot modify items in Draft Purchase Invoices
        """
        try:
            if not frappe.session.user:
                return
                
            # Check if current user is a Vendor User
            if "Vendor User" not in frappe.get_roles():
                return
                
            # Get original items for comparison
            original_doc = frappe.get_doc("Purchase Invoice", doc.name)
            
            # Check if items have been modified
            for idx, item in enumerate(doc.items):
                if idx < len(original_doc.items):
                    original_item = original_doc.items[idx]
                    
                    # Check critical fields
                    if item.item_code != original_item.item_code:
                        frappe.throw(
                            _("Vendor Users cannot modify item codes when Purchase Invoice is in Draft status."),
                            title=_("Access Restricted")
                        )
                    
                    if float(item.qty or 0) != float(original_item.qty or 0):
                        frappe.throw(
                            _("Vendor Users cannot modify quantities when Purchase Invoice is in Draft status."),
                            title=_("Access Restricted")
                        )
                    
                    if float(item.rate or 0) != float(original_item.rate or 0):
                        frappe.throw(
                            _("Vendor Users cannot modify rates when Purchase Invoice is in Draft status."),
                            title=_("Access Restricted")
                        )
                        
        except Exception as e:
            frappe.log_error(
                message=f"Vendor validation error: {str(e)}",
                title="Vendor Validation Error"
            )
            frappe.throw(
                _("Error validating vendor permissions. Please contact your system administrator."),
                title=_("Validation Error")
            )

# Hook function to be called from hooks.py
def validate_purchase_invoice_for_vendor(doc, method):
    """
    Hook function for Purchase Invoice validate event
    """
    CustomPurchaseInvoiceController.validate_vendor_user_permissions(doc, method)


# Whitelisted methods for client-side calls
@frappe.whitelist()
def check_vendor_user_permissions(docname=None):
    """
    Check if current user is a Vendor User and return permission status
    """
    try:
        roles = frappe.get_roles()
        has_vendor_role = "Vendor User" in roles
        
        return {
            "has_vendor_role": has_vendor_role,
            "user": frappe.session.user,
            "roles": roles,
            "can_modify_items": not has_vendor_role
        }
        
    except Exception as e:
        frappe.log_error(
            title="Check Vendor Permissions Error",
            message=str(e)
        )
        return {"error": str(e)}


@frappe.whitelist()
def get_original_items(docname):
    """
    Get original items from the database for comparison
    """
    try:
        if not docname:
            return {"items": []}
            
        doc = frappe.get_doc("Purchase Invoice", docname)
        items = []
        
        for item in doc.items:
            items.append({
                "idx": item.idx,
                "item_code": item.item_code,
                "item_name": item.item_name,
                "qty": item.qty,
                "rate": item.rate,
                "amount": item.amount
            })
        
        return {"items": items}
        
    except Exception as e:
        frappe.log_error(
            title="Get Original Items Error",
            message=str(e)
        )
        return {"error": str(e), "items": []}