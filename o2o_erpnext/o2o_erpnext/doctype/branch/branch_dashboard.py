# branch_dashboard.py
from frappe import _

def get_data():
    return {
        'fieldname': 'name',
        'transactions': [
            {
                'label': _('Related Documents'),
                'items': ['Sub Branch', 'Employee']
            }
        ],
        'non_standard_fieldnames': {
            'Sub Branch': 'branch',
            'Employee': 'branch'
        }
    }