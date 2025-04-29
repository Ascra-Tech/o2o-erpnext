# Copyright (c) 2025, Ascratech LLP and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_data(filters):
    user_roles = frappe.get_roles(frappe.session.user)
    is_supplier = "Supplier" in user_roles
    is_person_raising_request = "Person Raising Request" in user_roles
    is_requisition_approver = "Requisition Approver" in user_roles
    is_po_approver = "PO Approver" in user_roles
    
    # Base query with sub_branch added
    base_query = '''
        SELECT supplier,
               custom_branch,
               custom_sub_branch,
               shipping_address_display,
               custom_order_code,
               name,
               custom_created_user,
               grand_total,
               workflow_state,
               transaction_date,
               custom_updated_at,
               custom__approved_at
        FROM `tabPurchase Order`
    '''
    
    if frappe.session.user == "Administrator":
        # Full access for admin
        data = frappe.db.sql(base_query, as_dict=True)
    elif is_supplier:
        # Find the supplier record linked to this user
        supplier_name = frappe.db.get_value("Supplier", {"custom_user": frappe.session.user}, "name")
        
        if supplier_name:
            # Suppliers only see POs where they are the supplier
            query = base_query + ' WHERE supplier = %s'
            data = frappe.db.sql(query, (supplier_name,), as_dict=True)
        else:
            # If we can't find a supplier linked to this user, return empty data
            data = []
    elif is_person_raising_request or is_requisition_approver or is_po_approver:
        # For Person Raising Request, Requisition Approver, and PO Approver roles
        # use the same logic - find employee and their associated entities
        employee_name = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
        
        if employee_name:
            # Get the employee record with their primary attributes
            employee = frappe.db.get_value("Employee", 
                                         employee_name, 
                                         ["custom_supplier", "branch", "custom_sub_branch"],
                                         as_dict=True)
            
            # Get additional sub branches from the sub branch access list
            additional_sub_branches = []
            sub_branch_list = frappe.db.sql("""
                SELECT sub_branch 
                FROM `tabSub Branch Table` 
                WHERE parent = %s
            """, (employee_name,), as_dict=True)
            
            additional_sub_branches = [sb.sub_branch for sb in sub_branch_list if sb.sub_branch]
            
            # Build the query conditions
            conditions = []
            values = []
            
            if employee.custom_supplier:
                conditions.append("supplier = %s")
                values.append(employee.custom_supplier)
            
            if employee.branch:
                conditions.append("custom_branch = %s")
                values.append(employee.branch)
            
            # Handle both primary sub branch and additional sub branches from the list
            if employee.custom_sub_branch or additional_sub_branches:
                # Start with an empty sub branch list
                sub_branch_list = []
                
                # Add primary sub branch if it exists
                if employee.custom_sub_branch:
                    sub_branch_list.append(employee.custom_sub_branch)
                
                # Add additional sub branches from the list
                sub_branch_list.extend(additional_sub_branches)
                
                # If we have any sub branches, add them to the condition
                if sub_branch_list:
                    placeholders = ", ".join(["%s"] * len(sub_branch_list))
                    conditions.append(f"custom_sub_branch IN ({placeholders})")
                    values.extend(sub_branch_list)
            
            if conditions:
                condition_string = " AND ".join(conditions)
                query = base_query + f' WHERE {condition_string}'
                data = frappe.db.sql(query, values, as_dict=True)
            else:
                # If no conditions (unlikely but possible if employee record is incomplete)
                data = []
        else:
            # If no employee record is found for this user
            data = []
    else:
        # For all other roles, don't show any data
        data = []
    
    return data

def get_columns():
    columns = [
        {
            "label": _("Entity"),
            "fieldname": "supplier",
            "fieldtype": "data",
            "width": 150,
        },
        {
            "label": _("Branch"),
            "fieldname": "custom_branch",
            "fieldtype": "data",
            "width": 150,
        },
        {
            "label": _("Sub Branch"),  # Added Sub Branch column
            "fieldname": "custom_sub_branch",
            "fieldtype": "data",
            "width": 150,
        },
        {
            "label": _("Shipping Address"),
            "fieldname": "shipping_address_display",
            "fieldtype": "data",
            "width": 150,
        },
        {
            "label": _("Created By"),
            "fieldname": "custom_created_user",
            "fieldtype": "data",
            "width": 150,
        },
        {
            "label": _("Order Number"),
            "fieldname": "name",
            "fieldtype": "data",
            "width": 150,
        },
        {
            "label": _("Order Code"),
            "fieldname": "custom_order_code",
            "fieldtype": "data",
            "width": 150,
        },
        {
            "label": _("Gross Total"),
            "fieldname": "grand_total",
            "fieldtype": "Currency",
            "width": 150,
        },
        {
            "label": _("Order Status"),
            "fieldname": "workflow_state",
            "fieldtype": "data",
            "width": 150,
        },
        {
            "label": _("Created At"),
            "fieldname": "transaction_date",
            "fieldtype": "Datetime",
            "width": 200,
        },
        {
            "label": _("Update At"),
            "fieldname": "custom_updated_at",
            "fieldtype": "datetime",  # Corrected from "datatime"
            "width": 200,
        },
        {
            "label": _("Approved At"),
            "fieldname": "custom__approved_at",
            "fieldtype": "date",
            "width": 150,
        }
    ]
    return columns