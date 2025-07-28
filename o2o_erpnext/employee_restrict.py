import frappe
from frappe import _

def get_permission_query_conditions(user):
    """
    Apply role-based filtering for Employee doctype based on user's employee record
    """
    if not user:
        user = frappe.session.user
    
    # Skip restrictions for Administrator and System Manager
    if user == "Administrator" or "System Manager" in frappe.get_roles(user):
        return ""
    
    # Get current user's employee record
    employee = frappe.db.get_value(
        "Employee", 
        {"user_id": user}, 
        ["custom_supplier", "branch", "custom_sub_branch"], 
        as_dict=True
    )
    
    if not employee:
        # If user has no employee record, show nothing
        return "1=0"
    
    user_roles = frappe.get_roles(user)
    
    # PO Approver: Show employees from same supplier + branch
    if "PO Approver" in user_roles:
        if employee.custom_supplier and employee.branch:
            return f"""(`tabEmployee`.`custom_supplier` = '{employee.custom_supplier}' 
                       AND `tabEmployee`.`branch` = '{employee.branch}')"""
        else:
            return "1=0"
    
    # Requisition Approver: Show employees from same supplier + branch + sub-branch
    elif "Requisition Approver" in user_roles:
        if employee.custom_supplier and employee.branch and employee.custom_sub_branch:
            return f"""(`tabEmployee`.`custom_supplier` = '{employee.custom_supplier}' 
                       AND `tabEmployee`.`branch` = '{employee.branch}' 
                       AND `tabEmployee`.`custom_sub_branch` = '{employee.custom_sub_branch}')"""
        else:
            return "1=0"
    
    # For other roles, no restrictions
    return ""

def has_permission(doc, user):
    """
    Check if user has permission to access specific employee record
    """
    if not user:
        user = frappe.session.user
    
    # Skip restrictions for Administrator and System Manager
    if user == "Administrator" or "System Manager" in frappe.get_roles(user):
        return True
    
    # Get current user's employee record
    employee = frappe.db.get_value(
        "Employee", 
        {"user_id": user}, 
        ["custom_supplier", "branch", "custom_sub_branch"], 
        as_dict=True
    )
    
    if not employee:
        return False
    
    user_roles = frappe.get_roles(user)
    
    # PO Approver: Can access employees from same supplier + branch
    if "PO Approver" in user_roles:
        if employee.custom_supplier and employee.branch:
            return (doc.custom_supplier == employee.custom_supplier and 
                   doc.branch == employee.branch)
        return False
    
    # Requisition Approver: Can access employees from same supplier + branch + sub-branch
    elif "Requisition Approver" in user_roles:
        if employee.custom_supplier and employee.branch and employee.custom_sub_branch:
            return (doc.custom_supplier == employee.custom_supplier and 
                   doc.branch == employee.branch and 
                   doc.custom_sub_branch == employee.custom_sub_branch)
        return False
    
    # For other roles, allow access
    return True