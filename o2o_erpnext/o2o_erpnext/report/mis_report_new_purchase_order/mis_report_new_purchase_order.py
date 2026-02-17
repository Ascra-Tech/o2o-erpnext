# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, today, add_months

def execute(filters=None):
    if not filters:
        filters = {}
    
    # Set default filters
    if not filters.get("company"):
        filters["company"] = frappe.defaults.get_user_default("Company")
    
    if not filters.get("from_date"):
        filters["from_date"] = add_months(today(), -1)
    
    if not filters.get("to_date"):
        filters["to_date"] = today()
    
    columns = get_columns()
    data = get_data(filters)
    
    return columns, data

def get_columns():
    return [
        {
            "fieldname": "entity",
            "label": _("Entity"),
            "fieldtype": "Link",
            "options": "Supplier",
            "width": 200
        },
        {
            "fieldname": "purchase_order",
            "label": _("Purchase Order"),
            "fieldtype": "Link",
            "options": "Purchase Order",
            "width": 200
        },
        {
            "fieldname": "purchase_receipt",
            "label": _("Purchase Receipt"),
            "fieldtype": "Link",
            "options": "Purchase Receipt",
            "width": 200
        },
        {
            "fieldname": "product_name",
            "label": _("Product Name"),
            "fieldtype": "Data",
            "width": 200
        },
        {
            "fieldname": "order_code",
            "label": _("Order Code"),
            "fieldtype": "Data",
            "width": 120
        },
        {
            "fieldname": "category",
            "label": _("Category"),
            "fieldtype": "Link",
            "options": "Item Group",
            "width": 200
        },
        {
            "fieldname": "hsn_code",
            "label": _("HSN Code"),
            "fieldtype": "Int",
            "width": 100
        },
        {
            "fieldname": "po_date",
            "label": _("PO Date"),
            "fieldtype": "Date",
            "width": 120
        },
        {
            "fieldname": "required_by",
            "label": _("Required By"),
            "fieldtype": "Date",
            "width": 120
        },
        {
            "fieldname": "branch_name",
            "label": _("Branch Name"),
            "fieldtype": "Link",
            "options": "Branch",
            "width": 200
        },
        {
            "fieldname": "sub_branch",
            "label": _("Sub Branch"),
            "fieldtype": "Link",
            "options": "Sub Branch",
            "width": 150
        },
        {
            "fieldname": "vendor",
            "label": _("Vendor"),
            "fieldtype": "Link",
            "options": "Vendor",
            "width": 150
        },
        {
            "fieldname": "gross_amount",
            "label": _("Gross Amount"),
            "fieldtype": "Currency",
            "width": 170
        },
        {
            "fieldname": "cgst",
            "label": _("CGST"),
            "fieldtype": "Currency",
            "width": 170
        },
        {
            "fieldname": "sgst",
            "label": _("SGST"),
            "fieldtype": "Currency",
            "width": 170
        },
        {
            "fieldname": "igst",
            "label": _("IGST"),
            "fieldtype": "Currency",
            "width": 170
        },
        {
            "fieldname": "total",
            "label": _("Total"),
            "fieldtype": "Currency",
            "width": 170
        },
        {
            "fieldname": "status",
            "label": _("Status"),
            "fieldtype": "Data",
            "width": 120
        },
        {
            "fieldname": "awaiting_for",
            "label": _("Awaiting For"),
            "fieldtype": "Link",
            "options": "User",
            "width": 150
        },
        {
            "fieldname": "created_by",
            "label": _("Created By"),
            "fieldtype": "Data",
            "width": 200
        },
        {
            "fieldname": "created_at",
            "label": _("Created At"),
            "fieldtype": "Datetime",
            "width": 150
        },
        {
            "fieldname": "approved_at",
            "label": _("Approved At"),
            "fieldtype": "Datetime",
            "width": 150
        }
    ]

def get_data(filters):
    conditions = get_conditions(filters)
    
    query = """
        SELECT 
            po.supplier as entity,
            po.name as purchase_order,
            po.custom_purchase_receipt as purchase_receipt,
            poi.item_name as product_name,
            po.custom_order_code as order_code,
            poi.item_group as category,
            poi.gst_hsn_code as hsn_code,
            po.transaction_date as po_date,
            po.schedule_date as required_by,
            po.custom_branch as branch_name,
            po.custom_sub_branch as sub_branch,
            po.custom_vendor as vendor,
            poi.amount as gross_amount,
            poi.cgst_amount as cgst,
            poi.sgst_amount as sgst,
            poi.igst_amount as igst,
            (poi.amount + IFNULL(poi.cgst_amount, 0) + IFNULL(poi.sgst_amount, 0) + IFNULL(poi.igst_amount, 0)) as total,
            po.workflow_state as status,
            po.custom_awaiting_for as awaiting_for,
            po.custom_created_by as created_by,
            po.custom_created_at as created_at,
            po.custom__approved_at as approved_at
        FROM `tabPurchase Order` po
        INNER JOIN `tabPurchase Order Item` poi ON po.name = poi.parent
        WHERE po.docstatus = 1 {conditions}
        ORDER BY po.transaction_date DESC, po.name
    """.format(conditions=conditions)
    
    return frappe.db.sql(query, filters, as_dict=1)

def get_conditions(filters):
    conditions = []
    
    if filters.get("company"):
        conditions.append("AND po.company = %(company)s")
    
    if filters.get("from_date"):
        conditions.append("AND po.transaction_date >= %(from_date)s")
    
    if filters.get("to_date"):
        conditions.append("AND po.transaction_date <= %(to_date)s")
    
    if filters.get("supplier"):
        conditions.append("AND po.supplier = %(supplier)s")
    
    if filters.get("branch"):
        conditions.append("AND po.custom_branch = %(branch)s")
    
    if filters.get("status"):
        conditions.append("AND po.workflow_state = %(status)s")
    
    return " ".join(conditions)
