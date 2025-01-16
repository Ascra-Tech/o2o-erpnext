# In /home/frappe/frappe-bench-1/apps/o2o_erpnext/o2o_erpnext/o2o_erpnext/custom/purchase_order.py

import frappe
from frappe import _

def get_permission_query_conditions(user):
    """
    Filter Purchase Orders based on logged-in user's linked supplier
    """
    if not user:
        user = frappe.session.user  # Get logged-in user
    
    # Check if user has Vendor User role
    if "Vendor User" in frappe.get_roles(user):
        try:
            # Find employee record linked to user
            employee = frappe.db.sql("""
                SELECT name, supplier 
                FROM `tabEmployee` 
                WHERE user_id = %s
            """, user, as_dict=1)
            
            if employee and employee[0].supplier:
                # Return condition to filter Purchase Orders
                return f"`tabPurchase Order`.supplier = '{employee[0].supplier}'"
            else:
                # If no supplier linked, don't show any records
                return "1=0"
                
        except Exception as e:
            frappe.log_error(f"Error in Purchase Order permission: {str(e)}")
            return "1=0"
            
    return ""

def has_permission(doc, user=None, permission_type=None):
    """
    Check if user has permission to access specific Purchase Order
    """
    if not user:
        user = frappe.session.user
    
    if "Vendor User" in frappe.get_roles(user):
        try:
            # Get supplier linked to employee
            supplier = frappe.db.get_value("Employee", 
                {"user_id": user}, "supplier")
            
            if supplier:
                # Allow access if document supplier matches employee's supplier
                return doc.supplier == supplier
                
            return False
            
        except Exception as e:
            frappe.log_error(f"Error in Purchase Order permission check: {str(e)}")
            return False
            
    return True