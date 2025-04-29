# Copyright (c) 2025, Ascratech LLP and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_data(filters):
	if frappe.session.user == "Administrator":
		data = frappe.db.sql('''
            SELECT supplier,
                   custom_branch,
                   shipping_address_display,
                   custom_order_code,
                   name,
                   custom_created_user,
                   grand_total,
                   workflow_state,
                   transaction_date,
                   custom_updated_at
            FROM `tabPurchase Order`
        ''', as_dict=True)
	else:
		data = frappe.db.sql('''
			SELECT supplier,
					custom_branch,
					shipping_address_display,
					custom_order_code,
					name,
					custom_created_user,
					grand_total,
					workflow_state,
					transaction_date,
					custom_updated_at
			FROM `tabPurchase Order`
			WHERE custom_created_user = %s
		''', (frappe.session.user,), as_dict=True)
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
			"fieldtype": "datatime",
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