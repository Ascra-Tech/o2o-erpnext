# In your custom_app/custom_app/doctype/sub_branch/sub_branch_dashboard.py

from frappe import _

def get_data():
    return {
        'fieldname': 'name',
        'transactions': [
            {
                'label': _('Branch Details'),
                'items': ['Branch']
            },
            {
                'label': _('Employee Records'),
                'items': ['Employee']
            }
        ],
        'internal_links': {
            'Branch': 'branch'
        },
        'non_standard_fieldnames': {
            'Employee': 'custom_sub_branch',
            'Branch': 'branch'
        }
    }