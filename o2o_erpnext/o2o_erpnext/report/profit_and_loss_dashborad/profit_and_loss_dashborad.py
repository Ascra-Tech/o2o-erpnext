# Copyright (c) 2025, Ascratech LLP and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
	columns = get_columns()
	data = get_data(filter)
	return columns, data

def get_data(fillter):
	data=frappe.db.sql('''select name,supplier,custom_sub_branch,transaction_date,custom__approved_at,custom_branch,custom_total_pl,custom_total_purchase_cost,total from `tabPurchase Order` ''', as_dict=True)
	return data

def get_columns():
	columns = [
		{
            "label": _("Supplier"),
            "fieldname": "supplier",
            "fieldtype": "data",
            "width": 150,
        },
		{
            "label": _("Sub Branch"),
            "fieldname": "custom_sub_branch",
            "fieldtype": "data",
            "width": 150,
        },
        {
            "label": _("Purchase Order"),
            "fieldname": "name",
            "fieldtype": "data",
            "width": 150,
        },
		{
            "label": _("Created At"),
            "fieldname": "transaction_date",
            "fieldtype": "data",
            "width": 150,
        },
		{
            "label": _("Approved At"),
            "fieldname": "custom__approved_at",
            "fieldtype": "data",
            "width": 150,
        },
		{
            "label": _("Total"),
            "fieldname": "total",
            "fieldtype": "data",
            "width": 100,
        },
		{
            "label": _("Total Purchase cost"),
            "fieldname": "custom_total_purchase_cost",
            "fieldtype": "data",
            "width": 100,
        },
		{
            "label": _("Total P&L"),
            "fieldname": "custom_total_pl",
            "fieldtype": "data",
            "width": 100,
        },
		{
            "label": _("Branch"),
            "fieldname": "custom_branch",
            "fieldtype": "data",
            "width": 100,
        },
		
	]
	return columns

