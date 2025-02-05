import frappe
from frappe import _

def get_permission_query_conditions(user):
    if not user:
        user = frappe.session.user
        
    user_roles = frappe.get_roles(user)
    approver_roles = ["PO Approver", "Requisition Approver"]
    
    # Get the employee document linked to the user
    employee = frappe.db.get_value(
        "Employee",
        {"user_id": user},
        ["custom_supplier", "custom_sub_branch", "name"],
        as_dict=1
    )
    
    if not employee:
        return "1=0"  # No access if no employee record found

    # Handle Person Raising Request role
    if "Person Raising Request" in user_roles:
        if not employee.custom_supplier or not employee.custom_sub_branch:
            return "1=0"
        return f"""`tabPurchase Order`.supplier = '{employee.custom_supplier}' 
                AND `tabPurchase Order`.custom_sub_branch = '{employee.custom_sub_branch}'"""
    
    # Handle PO Approver and Requisition Approver roles
    elif any(role in approver_roles for role in user_roles):
        # Get additional sub branches from child table
        additional_branches = frappe.get_all(
            "Employee Sub Branch",  # Replace with your actual child table doctype name
            filters={"parent": employee.name},
            pluck="custom_sub_branch"
        )
        
        conditions = []
        
        # Add supplier condition
        if employee.custom_supplier:
            conditions.append(f"`tabPurchase Order`.supplier = '{employee.custom_supplier}'")
            
        # Create sub-branch conditions
        sub_branch_conditions = []
        
        # Add main sub branch if exists
        if employee.custom_sub_branch:
            sub_branch_conditions.append(
                f"`tabPurchase Order`.custom_sub_branch = '{employee.custom_sub_branch}'"
            )
            
        # Add conditions for additional sub branches
        for branch in additional_branches:
            sub_branch_conditions.append(
                f"`tabPurchase Order`.custom_sub_branch = '{branch}'"
            )
            
        # Combine sub branch conditions with OR
        if sub_branch_conditions:
            conditions.append(f"({' OR '.join(sub_branch_conditions)})")
            
        # If we have no conditions, restrict access
        if not conditions:
            return "1=0"
            
        # Combine all conditions with AND
        return " AND ".join(conditions)
    
    # For other roles, return empty string to fall back to standard permissions
    return ""