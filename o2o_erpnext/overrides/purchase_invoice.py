import frappe
from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import PurchaseInvoice
from frappe.model.naming import getseries

class CustomPurchaseInvoice(PurchaseInvoice):
    def autoname(self):
        """
        Custom naming method that fetches next invoice number from remote database counter
        """
        try:
            # Debug logging to verify controller is being used
            frappe.logger().info("🔥 CustomPurchaseInvoice.autoname() called - Controller is ACTIVE!")
            print("🔥 DEBUG: CustomPurchaseInvoice.autoname() called - Controller is ACTIVE!")
            # Import here to avoid circular imports
            from o2o_erpnext.api.remote_invoice_creator import RemoteInvoiceCreator
            
            # Create instance of remote invoice creator
            creator = RemoteInvoiceCreator()
            
            # Get current financial year from posting date
            posting_date = self.posting_date
            if posting_date:
                # Convert string to date if needed
                if isinstance(posting_date, str):
                    from frappe.utils import getdate
                    posting_date = getdate(posting_date)
                
                current_year = posting_date.year
                # Calculate financial year (April to March)
                if posting_date.month >= 4:
                    fy_start = current_year % 100
                    fy_end = (current_year + 1) % 100
                else:
                    fy_start = (current_year - 1) % 100
                    fy_end = current_year % 100
                
                financial_year = f"{fy_start:02d}-{fy_end:02d}"
            else:
                # Use current date if posting_date is not set
                from datetime import datetime
                current_year = datetime.now().year
                if datetime.now().month >= 4:
                    fy_start = current_year % 100
                    fy_end = (current_year + 1) % 100
                else:
                    fy_start = (current_year - 1) % 100
                    fy_end = current_year % 100
                
                financial_year = f"{fy_start:02d}-{fy_end:02d}"
            
            # Get next invoice code from remote database counter
            next_invoice_code = creator.get_next_invoice_code('AGO2O', financial_year)
            
            # Set the document name
            self.name = next_invoice_code
            
            frappe.logger().info(f"✅ Generated invoice name from remote counter: {next_invoice_code}")
            print(f"🔥 DEBUG: Generated invoice name from remote counter: {next_invoice_code}")
            
        except Exception as e:
            # Fallback to default naming if remote counter fails
            error_msg = str(e)
            frappe.logger().error(f"❌ Remote counter naming failed: {error_msg}")
            
            # Use fallback naming with getseries
            prefix = "PINV-.YY.-"
            self.name = getseries(prefix, 5)
            
            frappe.msgprint(
                f"⚠️ <strong>Warning:</strong> Could not fetch next number from remote database.<br><br>"
                f"<strong>Error:</strong> {error_msg}<br><br>"
                f"<em>Using fallback naming: {self.name}</em>",
                title="🔗 Remote Counter Warning",
                indicator="orange"
            )