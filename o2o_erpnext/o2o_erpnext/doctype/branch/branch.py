import frappe
from frappe import _
from frappe.utils import now_datetime
from frappe.model.document import Document

class Branch(Document):
    def validate(self):
        self.validate_supplier()
    
    def validate_supplier(self):
        if not self.custom_supplier:
            frappe.throw(_('Please select a Supplier'))
            
        # Verify supplier belongs to current user
        supplier_user = frappe.db.get_value('Supplier', 
            self.custom_supplier, 'custom_user')
            
        if not supplier_user or supplier_user != frappe.session.user:
            frappe.throw(_('Please select a Supplier associated with your account'))

        # Check for existing branches
        if self.is_new():
            existing_branch = frappe.db.exists('Branch', {
                'custom_supplier': self.custom_supplier,
                'name': ['!=', self.name or '']
            })
            
            if existing_branch:
                creation_date = frappe.db.get_value('Branch', 
                    existing_branch, 'creation')
                frappe.throw(
                    _('This supplier already has a branch (created on {0}). '
                      'Only one branch is allowed per supplier.').format(
                        frappe.format_datetime(creation_date)
                    )
                )

    def on_update(self):
        self.update_supplier_reference()
    
    def on_trash(self):
        """Before deletion, remove branch reference from supplier"""
        self.unlink_from_supplier()
    
    def unlink_from_supplier(self):
        """Remove branch reference from associated supplier"""
        if self.custom_supplier:
            try:
                frappe.db.set_value('Supplier', 
                    self.custom_supplier,
                    {
                        'custom_branch': None,  # Remove branch reference
                        'custom_updated_at': now_datetime()
                    }
                )
                
                frappe.msgprint(_('Branch unlinked from supplier {0}').format(self.custom_supplier),
                              alert=True,
                              indicator='blue')
                
            except Exception as e:
                frappe.log_error(
                    message=f"Failed to unlink branch from supplier: {str(e)}",
                    title="Branch Unlink Error"
                )
                frappe.throw(_('Failed to unlink branch from supplier. Please try again.'))
    
    def update_supplier_reference(self):
        """Update supplier with branch reference"""
        try:
            frappe.db.set_value('Supplier', 
                self.custom_supplier,
                {
                    'custom_branch': self.name,
                    'custom_updated_at': now_datetime()
                }
            )
            
        except Exception as e:
            frappe.log_error(
                message=f"Failed to update supplier reference: {str(e)}",
                title="Branch Reference Update Error"
            )
            frappe.throw(_('Failed to update Supplier with branch reference'))

@frappe.whitelist()
def get_supplier_branch_info(supplier):
    """Get branch information for a supplier
    
    Args:
        supplier (str): Supplier ID
        
    Returns:
        dict: Branch details if exists
    """
    if not supplier:
        return {}
        
    # Verify user permission
    supplier_user = frappe.db.get_value('Supplier', 
        supplier, ['custom_user'])
        
    if not supplier_user or supplier_user != frappe.session.user:
        frappe.throw(_('Invalid supplier selected'))
        
    # Get existing branch
    branch = frappe.db.get_value('Branch',
        {'custom_supplier': supplier},
        ['name', 'creation'],
        as_dict=True
    )
    
    return branch if branch else {}