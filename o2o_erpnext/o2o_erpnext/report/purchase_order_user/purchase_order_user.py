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
    
    # Base query with sub_branch added
    base_query = '''
        SELECT supplier,
               custom_branch,
               custom_sub_branch,  # Added sub_branch column
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
    elif is_person_raising_request:
        # Find the employee linked to this user
        employee = frappe.db.get_value("Employee", 
                                      {"user_id": frappe.session.user}, 
                                      ["custom_supplier", "branch", "custom_sub_branch"],
                                      as_dict=True)
        
        if employee:
            # Build the query conditions based on what we have
            conditions = []
            values = []
            
            if employee.custom_supplier:
                conditions.append("supplier = %s")
                values.append(employee.custom_supplier)
            
            if employee.branch:
                conditions.append("custom_branch = %s")
                values.append(employee.branch)
            
            if employee.custom_sub_branch:
                conditions.append("custom_sub_branch = %s")
                values.append(employee.custom_sub_branch)
            
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