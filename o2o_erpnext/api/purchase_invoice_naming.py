# Custom Purchase Invoice naming using remote database counter

import frappe
from frappe import _
from frappe.model.document import Document

class PurchaseInvoiceNaming:
    """Custom naming class for Purchase Invoice using remote counter"""
    
    @staticmethod
    def autoname(doc, method=None):
        """
        Custom autoname method for Purchase Invoice
        This method will be called during document creation to set the name
        """
        # Only apply custom naming for new documents
        if not doc.is_new():
            return
            
        # Skip if name is already set
        if doc.name and doc.name != 'new-purchase-invoice-1':
            return
            
        try:
            from o2o_erpnext.api.remote_naming_series import get_next_invoice_number_from_remote, get_current_financial_year
            
            # Get current financial year
            financial_year = get_current_financial_year()
            
            # Get vendor code for prefix
            vendor_code = 'AGO2O'  # Default
            if hasattr(doc, 'custom_vendor') and doc.custom_vendor:
                vendor_code = doc.custom_vendor[:5].upper()
            elif hasattr(doc, 'custom_vendor_code') and doc.custom_vendor_code:
                vendor_code = doc.custom_vendor_code
                
            # Generate remote invoice number
            invoice_number = get_next_invoice_number_from_remote(vendor_code, financial_year)
            
            # Set the document name
            doc.name = invoice_number
            
            # Also set custom fields for tracking
            if hasattr(doc, 'custom_portal_sync_id'):
                doc.custom_portal_sync_id = invoice_number
            if hasattr(doc, 'custom_fiscal_year'):
                doc.custom_fiscal_year = financial_year
            if hasattr(doc, 'custom_vendor_code'):
                doc.custom_vendor_code = vendor_code
                
            frappe.logger().info(f"Set Purchase Invoice name to: {invoice_number}")
            
        except Exception as e:
            frappe.logger().error(f"Custom naming failed for Purchase Invoice: {str(e)}")
            
            # Fallback to standard ERPNext naming
            frappe.msgprint(
                _(f"⚠️ Remote naming unavailable: {str(e)}<br>Using standard ERPNext naming."),
                title=_("Remote Naming Warning"),
                indicator="orange"
            )
            
            # Let ERPNext handle naming with standard series
            if hasattr(doc, 'naming_series') and doc.naming_series:
                from frappe.model.naming import make_autoname
                doc.name = make_autoname(doc.naming_series)
            else:
                # Set default naming series
                doc.naming_series = "PINV-.YY.-"
                doc.name = make_autoname(doc.naming_series)

def setup_purchase_invoice_naming():
    """
    Setup custom naming for Purchase Invoice doctype
    This function adds the custom naming method to Purchase Invoice hooks
    """
    try:
        # Check if already set up
        from frappe.core.doctype.doctype.doctype import validate_series
        
        frappe.logger().info("Setting up custom Purchase Invoice naming...")
        
        # This will be called via hooks
        return True
        
    except Exception as e:
        frappe.logger().error(f"Failed to setup Purchase Invoice naming: {str(e)}")
        return False