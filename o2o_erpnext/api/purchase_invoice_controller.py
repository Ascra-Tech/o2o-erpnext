# apps/o2o_erpnext/o2o_erpnext/api/purchase_invoice_controller.py

import frappe
import json
from frappe import _
from frappe.model.document import Document

class CustomPurchaseInvoiceController:
    """
    Custom controller to handle Vendor User restrictions for Purchase Invoice
    """
    
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