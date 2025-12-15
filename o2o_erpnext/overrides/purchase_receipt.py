import frappe
from erpnext.stock.doctype.purchase_receipt.purchase_receipt import PurchaseReceipt
from frappe.model.naming import getseries

class CustomPurchaseReceipt(PurchaseReceipt):
    def autoname(self):
        """
        Custom naming method for Purchase Receipt with format: {vendor_code}/{supplier_code}/{counter}
        Uses first 3 letters of vendor and supplier names in uppercase
        Counter increments globally (1, 2, 3...) regardless of vendor/supplier combination
        
        Examples:
        - XYZ/ABC/0001 (Vendor: XYZ Company, Supplier: ABC Suppliers)
        - VEN/SUP/0002 (Vendor: Vendor2, Supplier: Supplier2)
        - TES/SAM/0003 (Vendor: Test Vendor, Supplier: Sample Supplier)
        """
        try:
            # Debug logging to verify controller is being used
            frappe.logger().info("🔥 CustomPurchaseReceipt.autoname() called - Controller is ACTIVE!")
            print("🔥 DEBUG: CustomPurchaseReceipt.autoname() called - Controller is ACTIVE!")
            
            # Get vendor name from custom_vendor field and extract first 3 letters
            vendor_code = "VEN"  # Default 3-letter code
            if self.custom_vendor:
                try:
                    vendor_doc = frappe.get_doc("Vendor", self.custom_vendor)
                    vendor_full_name = vendor_doc.name or "VENDOR"
                    # Extract first 3 characters and convert to uppercase
                    vendor_code = vendor_full_name[:3].upper()
                except Exception as e:
                    frappe.logger().warning(f"Could not fetch vendor: {str(e)}")
                    vendor_code = str(self.custom_vendor)[:3].upper()
            
            # Get supplier name from supplier field and extract first 3 letters
            supplier_code = "SUP"  # Default 3-letter code
            if self.supplier:
                try:
                    supplier_doc = frappe.get_doc("Supplier", self.supplier)
                    supplier_full_name = supplier_doc.name or "SUPPLIER"
                    # Extract first 3 characters and convert to uppercase
                    supplier_code = supplier_full_name[:3].upper()
                except Exception as e:
                    frappe.logger().warning(f"Could not fetch supplier: {str(e)}")
                    supplier_code = str(self.supplier)[:3].upper()
            
            # Generate global sequential counter using getseries
            # Using a fixed prefix to ensure global counter across all vendor/supplier combinations
            counter_prefix = "PR-GLOBAL-"
            counter = getseries(counter_prefix, 4)  # 4 digits: 0001, 0002, 0003...
            
            # Extract just the number from the counter (remove prefix)
            # counter format will be like "PR-GLOBAL-0001", we want just "0001"
            counter_number = counter.split('-')[-1]
            
            # Construct the final name: vendor_code/supplier_code/counter
            self.name = f"{vendor_code}/{supplier_code}/{counter_number}"
            
            frappe.logger().info(f"✅ Generated Purchase Receipt name: {self.name}")
            print(f"🔥 DEBUG: Generated Purchase Receipt name: {self.name}")
            print(f"🔥 DEBUG: Vendor Code: {vendor_code}, Supplier Code: {supplier_code}, Counter: {counter_number}")
            
        except Exception as e:
            # Fallback to default naming if custom naming fails
            error_msg = str(e)
            frappe.logger().error(f"❌ Custom naming failed: {error_msg}")
            print(f"🔥 DEBUG ERROR: Custom naming failed: {error_msg}")
            
            # Use fallback naming with standard series
            prefix = "PR-.YY.-"
            self.name = getseries(prefix, 5)
            
            frappe.msgprint(
                f"⚠️ <strong>Warning:</strong> Could not generate custom Purchase Receipt name.<br><br>"
                f"<strong>Error:</strong> {error_msg}<br><br>"
                f"<em>Using fallback naming: {self.name}</em>",
                title="⚠️ Custom Naming Warning",
                indicator="orange"
            )
