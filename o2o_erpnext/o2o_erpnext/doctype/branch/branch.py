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
    def create_address(self, address_type, address_data):
        """
        Create a new address and link it to the current Branch and its Supplier
        
        Args:
            address_type (str): Either 'Billing' or 'Shipping'
            address_data (dict): Address details containing mandatory fields
                
        Returns:
            dict: Newly created address details
        """
        if not address_type in ["Billing", "Shipping"]:
            frappe.throw(_("Invalid address type. Must be either 'Billing' or 'Shipping'"))
        
        # Convert address_data from string to dict if needed
        if isinstance(address_data, str):
            import json
            address_data = json.loads(address_data)
        
        # Prepare address document
        address_doc = frappe.new_doc("Address")
        
        # Set basic fields
        address_doc.address_type = address_type
        address_doc.address_title = f"{self.name} - {address_type}"
        
        # Copy fields from address_data to the address document
        fields_to_copy = [
            "address_line1", "address_line2", "city", "county", "state", 
            "country", "pincode", "gstin", 
            "gst_category", "tax_category"
        ]
        
        for field in fields_to_copy:
            if field in address_data and address_data[field]:
                address_doc.set(field, address_data[field])
        
        # Set checkbox fields
        if address_data.get("is_primary_address"):
            address_doc.is_primary_address = 1
        
        if address_data.get("is_shipping_address"):
            address_doc.is_shipping_address = 1
        
        if address_data.get("disabled"):
            address_doc.disabled = 1
        
        # Add link to Branch
        address_doc.append("links", {
            "link_doctype": "Branch",
            "link_name": self.name
        })
        
        # Also link to supplier if available
        if self.custom_supplier:
            address_doc.append("links", {
                "link_doctype": "Supplier",
                "link_name": self.custom_supplier
            })
        
        # Save the address
        address_doc.insert(ignore_permissions=True)
        
        # Create a summary of the address
        address_summary = []
        if address_doc.address_line1:
            address_summary.append(address_doc.address_line1)
        if address_doc.address_line2:
            address_summary.append(address_doc.address_line2)
        if address_doc.city:
            address_summary.append(address_doc.city)
        if address_doc.state:
            address_summary.append(address_doc.state)
        if address_doc.country:
            address_summary.append(address_doc.country)
        if address_doc.pincode:
            address_summary.append("PIN: " + address_doc.pincode)
        
        # Format the address summary
        address_summary_text = ", ".join(address_summary)
        
        # Update the appropriate fields in Branch
        if address_type == "Billing":
            self.address = address_doc.name
            self.custom_billing_address_details = address_summary_text
        else:  # Shipping
            self.custom_shipping_address = address_doc.name
            self.custom_shipping_address_details = address_summary_text
        
        self.save(ignore_permissions=True)
        
        return {
            "status": "success",
            "message": f"{address_type} address created successfully",
            "address": address_doc.name
        }


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