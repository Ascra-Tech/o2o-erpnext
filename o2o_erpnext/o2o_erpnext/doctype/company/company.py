import frappe
from frappe import _
from frappe.utils import now_datetime
from erpnext.setup.doctype.company.company import Company as ERPNextCompany

class Company(ERPNextCompany):
    def validate(self):
        super(Company, self).validate()
        self.validate_vendor_link()

    def validate_vendor_link(self):
        """Validate and maintain the bidirectional link with Vendor"""
        # Check if custom_vendor field was changed
        if hasattr(self, '_doc_before_save') and self._doc_before_save and self.custom_vendor != getattr(self._doc_before_save, 'custom_vendor', None):
            # If there was a previous vendor, unlink it
            if getattr(self._doc_before_save, 'custom_vendor', None):
                frappe.db.set_value('Vendor',
                    self._doc_before_save.custom_vendor,
                    {
                        'linked_company': None,
                        'modified': now_datetime()
                    }
                )
               
            # If there's a new vendor, link it
            if self.custom_vendor:
                # Verify vendor exists
                if not frappe.db.exists("Vendor", self.custom_vendor):
                    frappe.throw(_("Selected Vendor {0} does not exist").format(self.custom_vendor))
               
                # Check if vendor is already linked to another company
                linked_company = frappe.db.get_value("Vendor", self.custom_vendor, "linked_company")
                if linked_company and linked_company != self.name:
                    frappe.throw(_("Vendor {0} is already linked to Company {1}").format(
                        self.custom_vendor, linked_company))
                   
                # Update vendor with company reference (bidirectional link)
                frappe.db.set_value('Vendor',
                    self.custom_vendor,
                    {
                        'linked_company': self.name,
                        'modified': now_datetime()
                    }
                )
               
                frappe.msgprint(_("Vendor {0} has been linked to this company").format(
                    self.custom_vendor), alert=True, indicator='green')

    def on_trash(self):
        self.unlink_from_vendor()
        super(Company, self).on_trash()
       
    def unlink_from_vendor(self):
        """Remove company reference from associated vendor"""
        if self.custom_vendor:
            try:
                frappe.db.set_value('Vendor',
                    self.custom_vendor,
                    {
                        'linked_company': None,  # Remove company reference
                        'modified': now_datetime()
                    }
                )
               
                frappe.msgprint(_('Company unlinked from vendor {0}').format(self.custom_vendor),
                              alert=True,
                              indicator='blue')
               
            except Exception as e:
                frappe.log_error(
                    message=f"Failed to unlink company from vendor: {str(e)}",
                    title="Company Unlink Error"
                )


@frappe.whitelist()
def handle_vendor_link(company, vendor=None, previous_vendor=None):
    """Handle bidirectional linking between Company and Vendor
    
    Args:
        company (str): Company name
        vendor (str, optional): New vendor to link
        previous_vendor (str, optional): Previous vendor to unlink
        
    Returns:
        dict: Result of the operation
    """
    try:
        # Validate inputs
        if not company:
            return {"success": False, "message": "Company name is required"}
            
        # If previous vendor exists and is different from new vendor, unlink it
        if previous_vendor and previous_vendor != vendor:
            frappe.db.set_value('Vendor', 
                previous_vendor,
                {
                    'linked_company': None,
                    'modified': now_datetime()
                }
            )
            
        # If new vendor is provided, link it
        if vendor:
            # Verify vendor exists
            if not frappe.db.exists("Vendor", vendor):
                return {"success": False, "message": f"Selected Vendor {vendor} does not exist"}
                
            # Check if vendor is already linked to another company
            linked_company = frappe.db.get_value("Vendor", vendor, "linked_company")
            if linked_company and linked_company != company:
                return {"success": False, "message": f"Vendor {vendor} is already linked to Company {linked_company}"}
                
            # Update vendor with company reference
            frappe.db.set_value('Vendor', 
                vendor,
                {
                    'linked_company': company,
                    'modified': now_datetime()
                }
            )
            
            # Verify the link was created
            updated_link = frappe.db.get_value("Vendor", vendor, "linked_company")
            if updated_link == company:
                return {"success": True, "message": f"Vendor {vendor} has been linked to this company"}
            else:
                return {"success": False, "message": "Failed to update vendor link"}
                
        return {"success": True, "message": "Vendor links updated successfully"}
            
    except Exception as e:
        frappe.log_error(message=f"Error in handle_vendor_link: {str(e)}")
        return {"success": False, "message": f"Error: {str(e)}"}


@frappe.whitelist()
def verify_vendor_link(company, vendor):
    """Verify and fix if needed the link between Company and Vendor
    
    Args:
        company (str): Company name
        vendor (str): Vendor name
        
    Returns:
        dict: Result of verification/fix
    """
    try:
        if not company or not vendor:
            return {"success": False, "message": "Both company and vendor are required"}
            
        # Check if the vendor has the correct linked_company
        linked_company = frappe.db.get_value("Vendor", vendor, "linked_company")
        
        if linked_company != company:
            # Fix the link
            frappe.db.set_value('Vendor', 
                vendor,
                {
                    'linked_company': company,
                    'modified': now_datetime()
                }
            )
            return {"success": True, "message": "Fixed vendor link", "fixed": True}
            
        return {"success": True, "message": "Link verified", "fixed": False}
        
    except Exception as e:
        frappe.log_error(message=f"Error in verify_vendor_link: {str(e)}")
        return {"success": False, "message": f"Error: {str(e)}"}