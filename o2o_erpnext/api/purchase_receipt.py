import frappe
from frappe import _
from frappe.utils import flt, get_datetime
from frappe.exceptions import DoesNotExistError

@frappe.whitelist()
def validate_and_set_purchase_receipt_defaults(doc_name=None):
    """
    Validates and sets default values for a Purchase Receipt based on the logged-in user's Employee record.
    """
    try:
        user_email = frappe.session.user
        employee = frappe.get_value("Employee", 
                                  {"user_id": user_email}, 
                                  ["name", "custom_supplier", "branch", "custom_sub_branch"],
                                  as_dict=1)
        
        if not employee:
            frappe.throw(_("No Employee record found linked to your User ID"), title=_("Employee Not Found"))
            
        if doc_name:
            pr_doc = frappe.get_doc("Purchase Receipt", doc_name)
        else:
            pr_doc = frappe.new_doc("Purchase Receipt")
            
        if employee.custom_supplier:
            pr_doc.supplier = employee.custom_supplier
            
        if employee.branch:
            pr_doc.custom_branch = employee.branch
            
        if employee.custom_sub_branch:
            pr_doc.custom_sub_branch = employee.custom_sub_branch
            
        if not doc_name:
            return {
                "status": "success",
                "message": _("Default values set successfully"),
                "data": {
                    "supplier": employee.custom_supplier,
                    "custom_branch": employee.branch,
                    "custom_sub_branch": employee.custom_sub_branch
                }
            }
        
        pr_doc.save()
        frappe.db.commit()
        
        return {
            "status": "success",
            "message": _("Purchase Receipt updated successfully")
        }
            
    except Exception as e:
        frappe.log_error(f"Error in Purchase Receipt auto-fill: {str(e)}", 
                        "Purchase Receipt API Error")
        raise e

@frappe.whitelist()
def get_supplier_vendors(supplier):
    """
    Fetches the list of vendors associated with a specific supplier.
    """
    try:
        supplier_doc = frappe.get_doc("Supplier", supplier)
        vendors = []
        
        if supplier_doc.custom_vendor_access_list:
            vendors = [v.vendor for v in supplier_doc.custom_vendor_access_list]
            
        return vendors
        
    except Exception as e:
        frappe.log_error(f"Error fetching supplier vendors: {str(e)}", 
                        "Get Supplier Vendors Error")
        return []

@frappe.whitelist()
def check_linked_purchase_invoices(purchase_receipt):
    """Check if a Purchase Receipt has linked Purchase Invoices in Draft or Submitted status"""
    if not purchase_receipt:
        return {"success": False, "message": "Purchase Receipt name is required"}
   
    try:
        # Log start of check (concise)
        frappe.log_error(f"Checking PR: {purchase_receipt}", "PI Check")
        
        # First, get all linked invoices
        linked_invoices = frappe.db.sql("""
            SELECT pi.name, pi.status, pi.docstatus, pi.is_return, pi.return_against
            FROM `tabPurchase Invoice` pi
            JOIN `tabPurchase Invoice Item` pii ON pii.parent = pi.name
            WHERE pii.purchase_receipt = %s
            AND pi.docstatus IN (0, 1)
        """, purchase_receipt, as_dict=1)
        
        # Log count only to avoid truncation
        frappe.log_error(f"Found {len(linked_invoices)} invoices", "PI Check")
        
        if not linked_invoices:
            return {
                "success": True,
                "message": "No linked Purchase Invoices found",
                "has_active_invoices": False,
                "invoices": []
            }
        
        # Build a dictionary of return invoices keyed by the original invoice they're returning
        return_invoices = {}
        for inv in linked_invoices:
            if inv.get("is_return") and inv.get("return_against"):
                if inv.get("return_against") not in return_invoices:
                    return_invoices[inv.get("return_against")] = []
                return_invoices[inv.get("return_against")].append(inv.get("name"))
        
        # Now filter to find active, non-fully-returned invoices
        active_invoices = []
        for inv in linked_invoices:
            # Skip return invoices themselves
            if inv.get("is_return"):
                continue
                
            # Check if this invoice has been fully returned
            fully_returned = False
            if inv.get("name") in return_invoices:
                # For simplicity, we'll consider an invoice with any return against it as "fully returned"
                # In a real system, you might want to check the amounts to determine if it's fully or partially returned
                fully_returned = True
                
            if not fully_returned and inv.get("docstatus") in [0, 1]:  # Draft or Submitted
                active_invoices.append(inv)
                # Log each active invoice separately
                frappe.log_error(f"Active: {inv.name} status={inv.status} docstatus={inv.docstatus}", "PI Check")
        
        if active_invoices:
            return {
                "success": True,
                "message": f"Found {len(active_invoices)} active linked Purchase Invoices",
                "has_active_invoices": True,
                "invoices": active_invoices
            }
        else:
            return {
                "success": True,
                "message": "No active linked Purchase Invoices found",
                "has_active_invoices": False,
                "invoices": linked_invoices
            }
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        frappe.log_error(error_msg, "PI Check Error")
        return {
            "success": False,
            "message": error_msg,
            "has_active_invoices": False,
            "invoices": []
        }

@frappe.whitelist()
def block_invoice_creation_if_linked(purchase_receipt):
    """
    Checks if any linked purchase invoices exist for a purchase receipt and blocks
    creation of new invoices if active ones are found.
    
    This function considers an invoice as "inactive" if it has been fully returned.
    
    Returns:
        dict: {
            "allow_creation": True/False,
            "message": str,
            "invoices": list of invoices (if any)
        }
    """
    try:
        result = check_linked_purchase_invoices(purchase_receipt)
        
        if not result["success"]:
            return {
                "allow_creation": False,
                "message": result["message"],
                "invoices": []
            }
        
        if result["has_active_invoices"]:
            invoice_details = [f"{inv['name']} ({inv['status']})" for inv in result["invoices"]]
            return {
                "allow_creation": False,
                "message": f"Cannot create Purchase Invoice. This Purchase Receipt is already linked to active invoices: {', '.join(invoice_details)}",
                "invoices": result["invoices"]
            }
        
        return {
            "allow_creation": True,
            "message": "No active Purchase Invoices found. You can create a new one.",
            "invoices": []
        }
    except Exception as e:
        frappe.log_error(f"Error in block_invoice_creation: {str(e)}", 
                        "Purchase Receipt API Error")
        return {
            "allow_creation": False,
            "message": f"Error checking linked invoices: {str(e)}",
            "invoices": []
        }

def get_permission_query_conditions(user, doctype):
    """
    Returns SQL conditions to filter Purchase Receipt based on user roles and related employee/supplier data.
    """
    roles = frappe.get_roles(user)

    if "Administrator" in roles:
        return None  # Administrator can see all
    
    # Check for Approver roles (Requisition Approver and PO Approver)
    if "Requisition Approver" in roles or "PO Approver" in roles:
        # Get employee linked to the user
        employee = frappe.db.get_value("Employee",
            {"user_id": user},
            ["name", "custom_supplier", "branch", "custom_sub_branch"],
            as_dict=1
        )

        if not employee:
            return "1=0"  # No employee found, return false condition

        conditions = []

        # Build conditions based on employee details (supplier and branch)
        if employee.custom_supplier:
            conditions.append(f"`tabPurchase Receipt`.supplier = '{employee.custom_supplier}'")
        if employee.branch:
            conditions.append(f"`tabPurchase Receipt`.custom_branch = '{employee.branch}'")

        # --- Sub-Branch Filtering (Primary OR any secondary sub-branch) ---
        sub_branch_conditions = []

        # 1. Primary Sub-Branch (custom_sub_branch)
        if employee.custom_sub_branch:
            sub_branch_conditions.append(f"`tabPurchase Receipt`.custom_sub_branch = '{employee.custom_sub_branch}'")

        # 2. Secondary Sub-Branches from custom_sub_branch_list table field in Employee
        if employee.name:
            try:
                # Use the correct table name: tabSub Branch Table
                additional_sub_branches = frappe.get_all(
                    "Sub Branch Table",  # The correct table DocType name
                    filters={"parent": employee.name},
                    fields=["sub_branch"],  # The correct field name for sub-branch
                    pluck="sub_branch"
                )
                
                for sub_branch in additional_sub_branches:
                    if sub_branch:  # Check for null values
                        sub_branch_conditions.append(f"`tabPurchase Receipt`.custom_sub_branch = '{sub_branch}'")
            except Exception as e:
                # Log error but continue execution
                frappe.log_error(f"Error fetching sub branches: {str(e)}", "Permission Query Error")

        # Combine sub-branch conditions with OR
        if sub_branch_conditions:
            conditions.append(f"({' OR '.join(sub_branch_conditions)})")
        
        # Combine all conditions with AND
        if conditions:
            return " AND ".join(conditions)
        else:
            return "1=0"
    
    # Then check if user has Person Raising Request role
    elif "Person Raising Request" in roles:
        # Get employee linked to the user
        employee = frappe.db.get_value("Employee", 
            {"user_id": user}, 
            ["custom_supplier", "branch", "custom_sub_branch"], 
            as_dict=1
        )
        
        if not employee:
            return "1=0"  # Return false condition if no employee found
            
        conditions = []
        
        # Build conditions based on employee details
        if employee.custom_supplier:
            conditions.append(f"`tabPurchase Receipt`.supplier = '{employee.custom_supplier}'")
        if employee.branch:
            conditions.append(f"`tabPurchase Receipt`.custom_branch = '{employee.branch}'")
        if employee.custom_sub_branch:
            conditions.append(f"`tabPurchase Receipt`.custom_sub_branch = '{employee.custom_sub_branch}'")
            
        # If any conditions exist, join them with AND
        if conditions:
            return " AND ".join(conditions)
        else:
            return "1=0"  # Return false condition if no matching criteria
    
    # Check if user has Supplier role
    elif "Supplier" in roles:
        # Get supplier linked to the user using custom_user field
        supplier = frappe.db.get_value("Supplier", {"custom_user": user}, "name")
        
        if not supplier:
            return "1=0"  # Return false condition if no supplier found
            
        # Return condition to match PO supplier with user's supplier
        return f"`tabPurchase Receipt`.supplier = '{supplier}'"

    # Check if user has Vendor User role
    elif "Vendor User" in roles:
        # Get vendor linked to the user
        vendor = frappe.db.get_value("Vendor", {"user_id": user}, "name")
        
        if not vendor:
            return "1=0"  # Return false condition if no vendor found
            
        # Return condition to match PO custom_vendor with user's vendor
        return f"`tabPurchase Receipt`.custom_vendor = '{vendor}'"
    
    # If user has none of the allowed roles
    else:
        frappe.throw(_("Not Allowed to see PO"))
        return "1=0"


def has_permission(doc, user=None, permission_type=None):
    """
    Additional permission check at document level
    """
    if not user:
        user = frappe.session.user
    
    roles = frappe.get_roles(user)
    
    # Administrator can see all documents
    if "Administrator" in roles:
        return True
    
    # Check for Approver roles
    elif "Requisition Approver" in roles or "PO Approver" in roles:
        # Get employee details
        employee = frappe.db.get_value("Employee", 
            {"user_id": user}, 
            ["name", "custom_supplier", "branch", "custom_sub_branch"], 
            as_dict=1
        )
        
        if not employee:
            return False
        
        try:    
            # Get additional sub-branches from the custom_sub_branch_list table field
            additional_sub_branches = frappe.get_all(
                "Sub Branch Table",  # The correct DocType name
                filters={"parent": employee.name},
                fields=["sub_branch"],  # The correct field name
                pluck="sub_branch"
            )
        except Exception as e:
            frappe.log_error(f"Error in has_permission: {str(e)}", "Permission Error")
            additional_sub_branches = []
        
        # Check if document matches required employee criteria
        matches_supplier = (doc.supplier == employee.custom_supplier)
        matches_branch = (doc.custom_branch == employee.branch)
        
        # Check if document's sub-branch matches either primary or any additional sub-branch
        matches_sub_branch = (doc.custom_sub_branch == employee.custom_sub_branch or 
                             doc.custom_sub_branch in additional_sub_branches)
        
        # For approver roles, must match supplier and branch, AND match at least one sub-branch
        return matches_supplier and matches_branch and matches_sub_branch
    
    # Check Person Raising Request role
    elif "Person Raising Request" in roles:
        # Get employee details
        employee = frappe.db.get_value("Employee", 
            {"user_id": user}, 
            ["custom_supplier", "branch", "custom_sub_branch"], 
            as_dict=1
        )
        
        if not employee:
            return False
            
        # Check if document matches employee criteria
        matches_supplier = (doc.supplier == employee.custom_supplier)
        matches_branch = (doc.custom_branch == employee.branch)
        matches_sub_branch = (doc.custom_sub_branch == employee.custom_sub_branch)
        
        return matches_supplier and matches_branch and matches_sub_branch
    
    # Check Supplier role
    elif "Supplier" in roles:
        # Get supplier linked to the user using custom_user field
        supplier = frappe.db.get_value("Supplier", {"custom_user": user}, "name")
        
        if not supplier:
            return False
            
        # Check if document matches supplier
        return doc.supplier == supplier

    # Check Vendor User role
    elif "Vendor User" in roles:
        # Get vendor linked to the user
        vendor = frappe.db.get_value("Vendor", {"user_id": user}, "name")
        
        if not vendor:
            return False
            
        # Check if document matches vendor
        return doc.custom_vendor == vendor
    
    return False