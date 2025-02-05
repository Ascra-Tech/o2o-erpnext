from frappe import _

def get_data():
    return {
        "fieldname": "vendor",
        "transactions": [
            {
                "label": _("Connections"),
                "items": ["Supplier"]
            }
        ]
    }
