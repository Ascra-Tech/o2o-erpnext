# Copyright (c) 2025, Ascratech LLP and contributors
# For license information, please see license.txt
from frappe.model.document import Document
import frappe
from frappe import _
from frappe.utils import cint
from frappe.model.document import Document
from frappe.permissions import has_permission

class SubBranch(Document):
    @frappe.whitelist()
    def get_employees(self):
        """Get all employees linked to this sub branch"""
        if not has_permission("Employee", "read"):
            frappe.throw(_("Not permitted to view Employee records"), frappe.PermissionError)
        
        return frappe.get_all(
            "Employee",
            filters={"custom_sub_branch": self.name},
            fields=["name", "employee_name", "department", "designation"]
        )

    def on_trash(self):
        """Clear sub branch reference from all linked employees when sub branch is deleted"""
        employees = frappe.get_all(
            "Employee",
            filters={"custom_sub_branch": self.name},
            fields=["name"]
        )
        
        for emp in employees:
            employee_doc = frappe.get_doc("Employee", emp.name)
            employee_doc.custom_sub_branch = None
            employee_doc.save(ignore_permissions=True)

def get_list(doctype, txt, filters, limit_start, limit_page_length=20, order_by=None):
    """
    Custom function to get filtered list of Sub Branch
    """
    user = frappe.session.user
    roles = frappe.get_roles(user)
    
    if "System Manager" in roles:
        return frappe.get_all(doctype, filters=filters, start=limit_start, 
                            page_length=limit_page_length, order_by=order_by)
    
    elif "Person Raising Request" in roles:
        employee = frappe.db.get_value("Employee", 
            {"user_id": user}, 
            ["custom_supplier", "branch", "custom_sub_branch"], 
            as_dict=1
        )
        
        if not employee or not all([employee.custom_supplier, employee.branch, employee.custom_sub_branch]):
            return []
            
        custom_filters = {
            "custom_supplier": employee.custom_supplier,
            "branch": employee.branch,
            "name": employee.custom_sub_branch
        }
        
        return frappe.get_all(doctype, filters=custom_filters, start=limit_start, 
                            page_length=limit_page_length, order_by=order_by)
    
    return []

def get_permission_query_conditions(user=None):
    """
    Returns query conditions for Sub Branch list view based on user role
    """
    conditions = []
    if not user:
        user = frappe.session.user
    
    roles = frappe.get_roles(user)
    
    if "System Manager" in roles:
        return ""
    
    elif "Person Raising Request" in roles:
        # Get employee linked to logged in user
        employee = frappe.db.get_value("Employee", 
            {"user_id": user}, 
            ["custom_supplier", "branch", "custom_sub_branch"], 
            as_dict=1
        )
        
        if not employee:
            frappe.msgprint("No Employee record found for user")
            return "1=0"
        
        conditions = []
        
        # Build strict conditions based on employee details
        if employee.custom_supplier:
            conditions.append(f"`tabSub Branch`.custom_supplier = '{employee.custom_supplier}'")
        else:
            return "1=0"
            
        if employee.branch:
            conditions.append(f"`tabSub Branch`.branch = '{employee.branch}'")
        else:
            return "1=0"
            
        if employee.custom_sub_branch:
            conditions.append(f"`tabSub Branch`.name = '{employee.custom_sub_branch}'")
        else:
            return "1=0"
            
        # Return combined conditions with AND
        if conditions:
            final_condition = " AND ".join(conditions)
            frappe.msgprint(f"Debug: Applied filter: {final_condition}")  # Debug message
            return final_condition
            
        return "1=0"
        
    return "1=0"  # Default to showing nothing

def has_permission(doc, ptype="read", user=None):
    """
    Returns True if user has permission on Sub Branch document
    """
    if not user:
        user = frappe.session.user

    roles = frappe.get_roles(user)
    
    if "System Manager" in roles:
        return True
        
    elif "Person Raising Request" in roles:
        # Get employee linked to logged in user
        employee = frappe.db.get_value("Employee", 
            {"user_id": user}, 
            ["custom_supplier", "branch", "custom_sub_branch"], 
            as_dict=1
        )
        
        if not employee:
            return False
            
        # All conditions must match
        matches_supplier = (doc.custom_supplier == employee.custom_supplier)
        matches_branch = (doc.branch == employee.branch)
        matches_sub_branch = (doc.name == employee.custom_sub_branch)
        
        # For debugging
        if not (matches_supplier and matches_branch and matches_sub_branch):
            frappe.msgprint(f"Debug: Permission denied - Supplier match: {matches_supplier}, Branch match: {matches_branch}, Sub Branch match: {matches_sub_branch}")
            
        return matches_supplier and matches_branch and matches_sub_branch
    
    return False  # Default to no access