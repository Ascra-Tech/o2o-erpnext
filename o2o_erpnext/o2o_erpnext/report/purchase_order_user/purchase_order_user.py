# Copyright (c) 2025, Ascratech LLP and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_data(filters):
    try:
        frappe.logger().info("Purchase Order User Report: Starting data fetch")
        user_roles = frappe.get_roles(frappe.session.user)
        current_user = frappe.session.user
        
        frappe.logger().info(f"Current user: {current_user}, Roles: {user_roles}")
        
        is_supplier = "Supplier" in user_roles
        is_person_raising_request = "Person Raising Request" in user_roles
        is_requisition_approver = "Requisition Approver" in user_roles
        is_po_approver = "PO Approver" in user_roles
        
        # Base query with sub_branch added
        base_query = '''
            SELECT 
                po.supplier,
                po.custom_branch,
                po.custom_sub_branch,
                po.shipping_address_display,
                po.custom_order_code,
                po.name,
                po.custom_created_user,
                po.workflow_state,
                po.transaction_date,
                po.custom_updated_at,
                po.custom__approved_at,
                poi.item_group,
                poi.item_name,
                poi.qty,
                poi.amount
            FROM `tabPurchase Order` po
            LEFT JOIN `tabPurchase Order Item` poi ON poi.parent = po.name 
        '''
        
        if current_user == "Administrator":
            frappe.logger().info("User is Administrator - showing all Purchase Orders")
            # Full access for admin
            data = frappe.db.sql(base_query, as_dict=True)
            frappe.logger().info(f"Found {len(data)} Purchase Orders for Administrator")
        elif is_supplier:
            frappe.logger().info(f"User has Supplier role - finding associated supplier for {current_user}")
            # Find the supplier record linked to this user
            supplier_name = frappe.db.get_value("Supplier", {"custom_user": current_user}, "name")
            
            frappe.logger().info(f"Supplier lookup result: {supplier_name}")
            
            if supplier_name:
                # Suppliers only see POs where they are the supplier
                query = base_query + ' WHERE supplier = %s'
                frappe.logger().info(f"Executing query with supplier={supplier_name}")
                data = frappe.db.sql(query, (supplier_name,), as_dict=True)
                frappe.logger().info(f"Found {len(data)} Purchase Orders for supplier: {supplier_name}")
            else:
                frappe.logger().warning(f"No supplier record found for user {current_user}")
                # If we can't find a supplier linked to this user, return empty data
                data = []
        elif is_person_raising_request or is_requisition_approver or is_po_approver:
            role_type = []
            if is_person_raising_request:
                role_type.append("Person Raising Request")
            if is_requisition_approver:
                role_type.append("Requisition Approver")
            if is_po_approver:
                role_type.append("PO Approver")
                
            frappe.logger().info(f"User has roles: {', '.join(role_type)} - finding associated employee for {current_user}")
            
            # For Person Raising Request, Requisition Approver, and PO Approver roles
            # use the same logic - find employee and their associated entities
            employee_name = frappe.db.get_value("Employee", {"user_id": current_user}, "name")
            
            frappe.logger().info(f"Employee lookup result: {employee_name}")
            
            if employee_name:
                # Get the employee record with their primary attributes
                employee = frappe.db.get_value("Employee", 
                                             employee_name, 
                                             ["custom_supplier", "branch", "custom_sub_branch"],
                                             as_dict=True)
                
                frappe.logger().info(f"Employee details - Supplier: {employee.custom_supplier}, Branch: {employee.branch}, Sub Branch: {employee.custom_sub_branch}")
                
                # Get additional sub branches from the sub branch access list
                frappe.logger().info(f"Fetching additional sub branches for employee: {employee_name}")
                additional_sub_branches = []
                sub_branch_list = frappe.db.sql("""
                    SELECT sub_branch 
                    FROM `tabSub Branch Table` 
                    WHERE parent = %s
                """, (employee_name,), as_dict=True)
                
                additional_sub_branches = [sb.sub_branch for sb in sub_branch_list if sb.sub_branch]
                
                frappe.logger().info(f"Additional sub branches: {additional_sub_branches}")
                
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
                
                frappe.logger().info(f"Query conditions: {conditions}")
                frappe.logger().info(f"Query values: {values}")
                
                if conditions:
                    condition_string = " AND ".join(conditions)
                    query = base_query + f' WHERE {condition_string}'
                    frappe.logger().info(f"Executing query: {query} with values: {values}")
                    data = frappe.db.sql(query, values, as_dict=True)
                    frappe.logger().info(f"Found {len(data)} Purchase Orders for employee: {employee_name}")
                else:
                    frappe.logger().warning(f"No conditions to filter on for employee: {employee_name}")
                    # If no conditions (unlikely but possible if employee record is incomplete)
                    data = []
            else:
                frappe.logger().warning(f"No employee record found for user: {current_user}")
                # If no employee record is found for this user
                data = []
        else:
            frappe.logger().info(f"User {current_user} has none of the required roles - showing no data")
            # For all other roles, don't show any data
            data = []
        
        frappe.logger().info("Purchase Order User Report: Data fetch completed successfully")
        return data
        
    except Exception as e:
        frappe.logger().error(f"Error in Purchase Order User Report: {str(e)}")
        frappe.logger().error(f"Traceback: {frappe.get_traceback()}")
        # Return empty data in case of error to prevent report failure
        return []

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
            "label": _("Categories"),
            "fieldname": "item_group",
            "fieldtype": "data",
            "width": 150,
        },
        {
            "label": _("Product Name"),
            "fieldname": "item_name",
            "fieldtype": "data",
            "width": 150,
        },
        {
            "label": _("Quantity"),
            "fieldname": "qty",
            "fieldtype": "data",
            "width": 150,
        },
        {
            "label": _("Total Coest"),
            "fieldname": "amount",
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


