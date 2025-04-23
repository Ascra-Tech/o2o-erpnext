# In your vendor.py file at /home/erpnext/frappe-bench/apps/o2o_erpnext/o2o_erpnext/o2o_erpnext/doctype/vendor/vendor.py

import frappe
from frappe import _
from frappe.utils import now_datetime
from frappe.model.document import Document

class Vendor(Document):
    def validate(self):
        self.validate_company_link()
    
    def validate_company_link(self):
        """Validate and maintain the bidirectional link with Company"""
        # Check if linked_company field was changed
        if hasattr(self, '_doc_before_save') and self._doc_before_save and self.linked_company != getattr(self._doc_before_save, 'linked_company', None):
            # If there was a previous company, unlink it
            if getattr(self._doc_before_save, 'linked_company', None):
                frappe.db.set_value('Company', 
                    self._doc_before_save.linked_company,
                    {
                        'custom_vendor': None,
                        'modified': now_datetime()
                    }
                )
                
            # If there's a new company, link it
            if self.linked_company:
                # Verify company exists
                if not frappe.db.exists("Company", self.linked_company):
                    frappe.throw(_("Selected Company {0} does not exist").format(self.linked_company))
                
                # Check if company is already linked to another vendor
                other_vendor = frappe.db.get_value("Company", self.linked_company, "custom_vendor")
                if other_vendor and other_vendor != self.name:
                    frappe.throw(_("Company {0} is already linked to Vendor {1}").format(
                        self.linked_company, other_vendor))
                    
                # Update company with vendor reference
                frappe.db.set_value('Company', 
                    self.linked_company,
                    {
                        'custom_vendor': self.name,
                        'modified': now_datetime()
                    }
                )
                
                frappe.msgprint(_("Company {0} has been linked to this vendor").format(
                    self.linked_company), alert=True, indicator='green')
    
    def on_trash(self):
        self.unlink_from_company()
    
    def unlink_from_company(self):
        """Remove vendor reference from associated company"""
        if self.linked_company:
            try:
                frappe.db.set_value('Company', 
                    self.linked_company,
                    {
                        'custom_vendor': None,  # Remove vendor reference
                        'modified': now_datetime()
                    }
                )
                
                frappe.msgprint(_('Vendor unlinked from company {0}').format(self.linked_company),
                              alert=True,
                              indicator='blue')
                
            except Exception as e:
                frappe.log_error(
                    message=f"Failed to unlink vendor from company: {str(e)}",
                    title="Vendor Unlink Error"
                )