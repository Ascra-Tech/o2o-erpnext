import frappe
from frappe import _

@frappe.whitelist()
def check_supplier_permission():
    user = frappe.session.user
    response = {'allowed': True, 'message': ''}
    
    # Check if user has Supplier role
    user_roles = frappe.get_roles(user)
    if 'Supplier' not in user_roles:
        response['allowed'] = False
        response['message'] = _('You are not authorized to Create Suppliers')
        return response
    
    # Check if user already has a supplier
    existing_supplier = frappe.get_all('Supplier', 
        filters={
            'custom_user': user
        }, 
        fields=['name'])
    
    if existing_supplier:
        response['allowed'] = False
        response['message'] = _('You can create only one supplier is Allowed')
        return response
        
    return response