import frappe
from frappe import _
from frappe.utils import flt, get_datetime

@frappe.whitelist()
def get_permission_query_conditions(user):
    """
    Returns query conditions for Purchase Invoice list view based on user role
    """
    if not user:
        user = frappe.session.user
    
    roles = frappe.get_roles(user)
    
    # First check if user is Administrator - show all PIs
    if "Administrator" in roles:
        return ""  # Empty string means no conditions - show all records
    
    # Check for Approver roles (Requisition Approver and PO Approver)
    elif "Requisition Approver" in roles or "PO Approver" in roles:
        # Get employee linked to the user and their sub-branches
        employee = frappe.db.get_value("Employee", 
            {"user_id": user}, 
            ["name", "custom_supplier", "branch", "custom_sub_branch"], 
            as_dict=1
        )
        
        if not employee:
            return "1=0"  # Return false condition if no employee found
            
        # Get additional sub-branches from custom_sub_branch_list
        additional_sub_branches = frappe.get_all("Employee Sub Branch List",
            filters={"parent": employee.name},
            pluck="custom_sub_branch"
        )
        
        conditions = []
        
        # Build conditions based on employee details
        if employee.custom_supplier:
            conditions.append(f"`tabPurchase Invoice`.supplier = '{employee.custom_supplier}'")
        if employee.branch:
            conditions.append(f"`tabPurchase Invoice`.custom_branch = '{employee.branch}'")
        
        # Build sub-branch condition to include both primary and additional sub-branches
        sub_branch_conditions = []
        if employee.custom_sub_branch:
            sub_branch_conditions.append(f"`tabPurchase Invoice`.custom_sub_branch = '{employee.custom_sub_branch}'")
        
        # Add conditions for additional sub-branches
        for sub_branch in additional_sub_branches:
            sub_branch_conditions.append(f"`tabPurchase Invoice`.custom_sub_branch = '{sub_branch}'")
        
        # Combine sub-branch conditions with OR
        if sub_branch_conditions:
            conditions.append(f"({' OR '.join(sub_branch_conditions)})")
            
        # If any conditions exist, join them with AND
        if conditions:
            return " AND ".join(conditions)
        else:
            return "1=0"  # Return false condition if no matching criteria
    
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
            conditions.append(f"`tabPurchase Invoice`.supplier = '{employee.custom_supplier}'")
        if employee.branch:
            conditions.append(f"`tabPurchase Invoice`.custom_branch = '{employee.branch}'")
        if employee.custom_sub_branch:
            conditions.append(f"`tabPurchase Invoice`.custom_sub_branch = '{employee.custom_sub_branch}'")
            
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
            
        # Return condition to match PI supplier with user's supplier
        return f"`tabPurchase Invoice`.supplier = '{supplier}'"

    # Check if user has Vendor User role
    elif "Vendor User" in roles:
        # Get vendor linked to the user
        vendor = frappe.db.get_value("Vendor", {"user_id": user}, "name")
        
        if not vendor:
            return "1=0"  # Return false condition if no vendor found
            
        # Return condition to match PI custom_vendor with user's vendor
        return f"`tabPurchase Invoice`.custom_vendor = '{vendor}'"
    
    # If user has none of the allowed roles
    else:
        frappe.throw(_("Not Allowed to see PI"))
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
            
        # Get additional sub-branches
        additional_sub_branches = frappe.get_all("Employee Sub Branch List",
            filters={"parent": employee.name},
            pluck="custom_sub_branch"
        )
        
        # Check if document matches employee criteria
        matches_supplier = (doc.supplier == employee.custom_supplier)
        matches_branch = (doc.custom_branch == employee.branch)
        
        # Check if document's sub-branch matches either primary or any additional sub-branch
        matches_sub_branch = (doc.custom_sub_branch == employee.custom_sub_branch or 
                            doc.custom_sub_branch in additional_sub_branches)
        
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