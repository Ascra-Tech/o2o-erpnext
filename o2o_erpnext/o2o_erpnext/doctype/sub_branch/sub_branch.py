# Copyright (c) 2025, Ascratech LLP and contributors
# For license information, please see license.txt
from frappe.model.document import Document
import frappe
from frappe import _
from frappe.utils import cint
from frappe.model.document import Document
from frappe.permissions import has_permission

class SubBranch(Document):
    def validate(self):
        """Validate document before saving"""
        self.update_gst_state_number()
        
    def update_gst_state_number(self):
        """Update GST State Number based on GST State"""
        if self.gst_state:
            state_code_map = {
                "Andaman and Nicobar Islands": "35",
                "Andhra Pradesh": "37",
                "Arunachal Pradesh": "12",
                "Assam": "18",
                "Bihar": "10",
                "Chandigarh": "04",
                "Chhattisgarh": "22",
                "Dadra and Nagar Haveli and Daman and Diu": "26",
                "Delhi": "07",
                "Goa": "30",
                "Gujarat": "24",
                "Haryana": "06",
                "Himachal Pradesh": "02",
                "Jammu and Kashmir": "01",
                "Jharkhand": "20",
                "Karnataka": "29",
                "Kerala": "32",
                "Ladakh": "38",
                "Lakshadweep Islands": "31",
                "Madhya Pradesh": "23",
                "Maharashtra": "27",
                "Manipur": "14",
                "Meghalaya": "17",
                "Mizoram": "15",
                "Nagaland": "13",
                "Odisha": "21",
                "Other Countries": "96",
                "Other Territory": "97",
                "Puducherry": "34",
                "Punjab": "03",
                "Rajasthan": "08",
                "Sikkim": "11",
                "Tamil Nadu": "33",
                "Telangana": "36",
                "Tripura": "16",
                "Uttar Pradesh": "09",
                "Uttarakhand": "05",
                "West Bengal": "19"
            }
            self.gst_state_number = state_code_map.get(self.gst_state, "")
    
    @frappe.whitelist()
    def copy_tax_details_from_address(self):
        """Copy tax details from linked address to Sub Branch"""
        if self.address:
            address_doc = frappe.get_doc("Address", self.address)
            if address_doc:
                # Copy GST details from address
                self.gstin = address_doc.gstin
                self.gst_state = address_doc.gst_state
                self.gst_category = address_doc.gst_category
                self.gst_state_number = address_doc.gst_state_number
                self.tax_category = address_doc.tax_category
                self.save(ignore_permissions=True)
                return {
                    "status": "success",
                    "message": "Tax details copied from address successfully"
                }
        return {
            "status": "error",
            "message": "No address found to copy details from"
        }

    @frappe.whitelist()
    def sync_tax_details_with_address(self):
        """Sync tax details between Sub Branch and Address"""
        if not self.address:
            frappe.throw(_("No primary address linked to this Sub Branch"))
            
        address_doc = frappe.get_doc("Address", self.address)
        
        # Update address with Sub Branch tax details
        address_doc.gstin = self.gstin
        address_doc.gst_state = self.gst_state
        address_doc.gst_category = self.gst_category
        address_doc.gst_state_number = self.gst_state_number
        address_doc.tax_category = self.tax_category
        
        address_doc.save(ignore_permissions=True)
        
        frappe.msgprint(_("Tax details synced with primary address"))
        return {
            "status": "success",
            "message": "Tax details synced successfully"
        }
    
    @frappe.whitelist()
    def get_employees(self):
        """Get all employees linked to this sub branch"""
        if not has_permission("Employee", "read"):
            frappe.throw(_("Not permitted to view Employee records"), frappe.PermissionError)
        
        return frappe.get_all(
            "Employee",
            filters={"custom_sub_branch": self.name},
            fields=["name", "employee_name", "department", "designation"]
        )

    def on_trash(self):
        """Clear sub branch reference from all linked employees when sub branch is deleted"""
        employees = frappe.get_all(
            "Employee",
            filters={"custom_sub_branch": self.name},
            fields=["name"]
        )
        
        for emp in employees:
            employee_doc = frappe.get_doc("Employee", emp.name)
            employee_doc.custom_sub_branch = None
            employee_doc.save(ignore_permissions=True)
    
    @frappe.whitelist()
    def create_address(self, address_type, address_data):
        """
        Create a new address and link it to the current Sub Branch and its Supplier
        
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
            "country", "pincode", "gstin", "gst_category", "tax_category"
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
        
        # Add link to Sub Branch
        address_doc.append("links", {
            "link_doctype": "Sub Branch",
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
        
        # Update the appropriate fields in Sub Branch
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


def get_list(doctype, txt, filters, limit_start, limit_page_length=20, order_by=None):
    """
    Custom function to get filtered list of Sub Branch
    """
    user = frappe.session.user
    roles = frappe.get_roles(user)
    
    if "System Manager" in roles:
        return frappe.get_all(doctype, filters=filters, start=limit_start, 
                            page_length=limit_page_length, order_by=order_by)
    
    elif "Person Raising Request" in roles:
        employee = frappe.db.get_value("Employee", 
            {"user_id": user}, 
            ["custom_supplier", "branch", "custom_sub_branch"], 
            as_dict=1
        )
        
        if not employee or not all([employee.custom_supplier, employee.branch, employee.custom_sub_branch]):
            return []
            
        custom_filters = {
            "custom_supplier": employee.custom_supplier,
            "branch": employee.branch,
            "name": employee.custom_sub_branch
        }
        
        return frappe.get_all(doctype, filters=custom_filters, start=limit_start, 
                            page_length=limit_page_length, order_by=order_by)
    
    return []

def get_permission_query_conditions(user=None):
    """
    Returns query conditions for Sub Branch list view based on user role
    """
    conditions = []
    if not user:
        user = frappe.session.user
    
    roles = frappe.get_roles(user)
    
    if "System Manager" in roles:
        return ""
    
    elif "Person Raising Request" in roles:
        # Get employee linked to logged in user
        employee = frappe.db.get_value("Employee", 
            {"user_id": user}, 
            ["custom_supplier", "branch", "custom_sub_branch"], 
            as_dict=1
        )
        
        if not employee:
            frappe.msgprint("No Employee record found for user")
            return "1=0"
        
        conditions = []
        
        # Build strict conditions based on employee details
        if employee.custom_supplier:
            conditions.append(f"`tabSub Branch`.custom_supplier = '{employee.custom_supplier}'")
        else:
            return "1=0"
            
        if employee.branch:
            conditions.append(f"`tabSub Branch`.branch = '{employee.branch}'")
        else:
            return "1=0"
            
        if employee.custom_sub_branch:
            conditions.append(f"`tabSub Branch`.name = '{employee.custom_sub_branch}'")
        else:
            return "1=0"
            
        # Return combined conditions with AND
        if conditions:
            final_condition = " AND ".join(conditions)
            frappe.msgprint(f"Debug: Applied filter: {final_condition}")  # Debug message
            return final_condition
            
        return "1=0"
        
    return "1=0"  # Default to showing nothing

def has_permission(doc, ptype="read", user=None):
    """
    Returns True if user has permission on Sub Branch document
    """
    if not user:
        user = frappe.session.user

    roles = frappe.get_roles(user)
    
    if "System Manager" in roles:
        return True
        
    elif "Person Raising Request" in roles:
        # Get employee linked to logged in user
        employee = frappe.db.get_value("Employee", 
            {"user_id": user}, 
            ["custom_supplier", "branch", "custom_sub_branch"], 
            as_dict=1
        )
        
        if not employee:
            return False
            
        # All conditions must match
        matches_supplier = (doc.custom_supplier == employee.custom_supplier)
        matches_branch = (doc.branch == employee.branch)
        matches_sub_branch = (doc.name == employee.custom_sub_branch)
        
        # For debugging
        if not (matches_supplier and matches_branch and matches_sub_branch):
            frappe.msgprint(f"Debug: Permission denied - Supplier match: {matches_supplier}, Branch match: {matches_branch}, Sub Branch match: {matches_sub_branch}")
            
        return matches_supplier and matches_branch and matches_sub_branch
    
    return False  # Default to no access