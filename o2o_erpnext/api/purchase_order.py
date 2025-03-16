import frappe
from frappe import _
from frappe.utils import flt, get_datetime
from frappe.exceptions import DoesNotExistError

@frappe.whitelist()
def validate_and_set_purchase_order_defaults(doc_name=None):
    try:
        user_email = frappe.session.user
        employee = frappe.get_value("Employee", 
                                  {"user_id": user_email}, 
                                  ["name", "custom_supplier", "branch", "custom_sub_branch"],
                                  as_dict=1)
        
        if not employee:
            frappe.throw(_("No Employee record found linked to your User ID"), title=_("Employee Not Found"))
            
        if doc_name:
            po_doc = frappe.get_doc("Purchase Order", doc_name)
        else:
            po_doc = frappe.new_doc("Purchase Order")
            
        if employee.custom_supplier:
            po_doc.supplier = employee.custom_supplier
            
        approver_info = None
        if employee.branch:
            po_doc.custom_branch = employee.branch
            
            # Find branch approver once we set the branch
            approver_info = get_branch_approver_info(employee.branch)
            if approver_info:
                po_doc.custom__approver_name_and_email = approver_info
            
        if employee.custom_sub_branch:
            po_doc.custom_sub_branch = employee.custom_sub_branch
            
        if not doc_name:
            response_data = {
                "supplier": employee.custom_supplier,
                "custom_branch": employee.branch,
                "custom_sub_branch": employee.custom_sub_branch
            }
            
            if approver_info:
                response_data["custom__approver_name_and_email"] = approver_info
                
            return {
                "status": "success",
                "message": _("Default values set successfully"),
                "data": response_data
            }
        
        po_doc.save()
        frappe.db.commit()
        
        return {
            "status": "success",
            "message": _("Purchase Order updated successfully")
        }
            
    except Exception as e:
        frappe.log_error(f"Error in Purchase Order auto-fill: {str(e)}", 
                        "Purchase Order API Error")
        raise e


def get_branch_approver_info(branch):
    """Helper function to find branch approver information"""
    try:
        if not branch:
            return None
            
        # Search for Employee with PO Approver role in custom_roles
        # and matching branch
        employees = frappe.get_all(
            "Employee",
            filters={
                "branch": branch,
                "custom_roles": ["like", "%PO Approver%"]
            },
            fields=["name", "employee_name", "custom_user_email"]
        )
        
        if not employees:
            return None
            
        # Take the first matching employee
        approver = employees[0]
        
        # Format approver information
        return f"{approver.employee_name}:{approver.custom_user_email}"
            
    except Exception as e:
        frappe.log_error(f"Error finding branch approver: {str(e)}", 
                        "Get Branch Approver Error")
        return None

@frappe.whitelist()
def get_supplier_vendors(supplier):
    try:
        supplier_doc = frappe.get_doc("Supplier", supplier)
        vendors = []
        
        if supplier_doc.custom_vendor_access_list:
            vendors = [v.vendor for v in supplier_doc.custom_vendor_access_list]
            
        return vendors
        
    except Exception as e:
        frappe.log_error(f"Error fetching supplier vendors: {str(e)}", 
                        "Get Supplier Vendors Error")
        return []

@frappe.whitelist()
def set_branch_approver_for_purchase_order(purchase_order_name):
    try:
        # Get the Purchase Order document
        po_doc = frappe.get_doc("Purchase Order", purchase_order_name)
        
        # Get the branch from Purchase Order
        branch = po_doc.custom_branch
        
        if not branch:
            frappe.throw(_("Purchase Order does not have a branch assigned"), 
                        title=_("Missing Branch"))
        
        # Search for Employee with PO Approver role in custom_roles
        # and matching branch
        employees = frappe.get_all(
            "Employee",
            filters={
                "branch": branch,  # Using the branch from PO
                "custom_roles": ["like", "%PO Approver%"]
            },
            fields=["name", "employee_name", "custom_user_email"]
        )
        
        if not employees:
            frappe.msgprint(
                _("No Branch Approver found for branch {0}").format(branch),
                title=_("Approver Not Found")
            )
            return {
                "status": "warning",
                "message": _("No Branch Approver found")
            }
        
        # Take the first matching employee
        approver = employees[0]
        
        # Format and set the approver information
        approver_info = f"{approver.employee_name}:{approver.custom_user_email}"
        
        # Update the Purchase Order
        po_doc.custom__approver_name_and_email = approver_info
        po_doc.save()
        frappe.db.commit()
        
        return {
            "status": "success",
            "message": _("Branch Approver set successfully"),
            "approver": approver_info
        }
            
    except Exception as e:
        frappe.log_error(f"Error setting branch approver: {str(e)}", 
                        "Set Branch Approver Error")
        return {
            "status": "error",
            "message": str(e)
        }

class PurchaseOrderValidation:
    def validate_vendor_access(self):
        if not self.doc.custom_vendor:
            return True

        if not self.doc.supplier:
            frappe.throw(_("Supplier must be selected before selecting a vendor"), title=_("Missing Supplier"))

        supplier_doc = frappe.get_doc("Supplier", self.doc.supplier)
        allowed_vendors = [v.vendor for v in supplier_doc.custom_vendor_access_list]

        if not allowed_vendors:
            frappe.throw(_("No vendors configured for supplier {0}").format(self.doc.supplier), 
                        title=_("No Vendors Available"))

        if self.doc.custom_vendor not in allowed_vendors:
            frappe.throw(
                _("Selected vendor {0} is not in the allowed vendor list for supplier {1}").format(
                    self.doc.custom_vendor, self.doc.supplier
                ),
                title=_("Invalid Vendor")
            )
        return True

def get_permission_query_conditions(user, doctype):
    """
    Returns SQL conditions to filter Purchase Orders based on user roles and related employee/supplier data.
    """
    roles = frappe.get_roles(user)

    if "Administrator" in roles:
        return None  # Administrator can see all
    
        # Then check if user has Person Raising Request Branch role
    if "Person Raising Request Branch" in roles:
        # Get employee linked to the user
        employee = frappe.db.get_value("Employee", 
            {"user_id": user}, 
            ["custom_supplier", "branch"], 
            as_dict=1
        )
        
        if not employee:
            return "1=0"  # Return false condition if no employee found
            
        conditions = []
        
        # Build conditions based on employee details
        if employee.custom_supplier:
            conditions.append(f"`tabPurchase Order`.supplier = '{employee.custom_supplier}'")
        if employee.branch:
            conditions.append(f"`tabPurchase Order`.custom_branch = '{employee.branch}'")
            conditions.append("(`tabPurchase Order`.custom_sub_branch IS NULL OR TRIM(`tabPurchase Order`.custom_sub_branch) = '')")
            
        # If any conditions exist, join them with AND
        if conditions:
            return " AND ".join(conditions)
        else:
            return "1=0"  # Return false condition if no matching criteria
    
    # Check for Approver roles (Requisition Approver and PO Approver)
    if "Requisition Approver" in roles or "PO Approver" in roles:
        # Get employee linked to the user
        employee = frappe.db.get_value("Employee",
            {"user_id": user},
            ["name", "custom_supplier", "branch", "custom_sub_branch"],
            as_dict=1
        )

        if not employee:
            return "1=0"  # No employee found, return false condition

        conditions = []

        # Build conditions based on employee details (supplier and branch)
        if employee.custom_supplier:
            conditions.append(f"`tabPurchase Order`.supplier = '{employee.custom_supplier}'")
        if employee.branch:
            conditions.append(f"`tabPurchase Order`.custom_branch = '{employee.branch}'")

        # --- Sub-Branch Filtering (Primary OR any secondary sub-branch) ---
        sub_branch_conditions = []

        # 1. Primary Sub-Branch (custom_sub_branch)
        if employee.custom_sub_branch:
            sub_branch_conditions.append(f"`tabPurchase Order`.custom_sub_branch = '{employee.custom_sub_branch}'")

        # 2. Secondary Sub-Branches from custom_sub_branch_list table field in Employee
        if employee.name:
            try:
                # Use the correct table name: tabSub Branch Table
                additional_sub_branches = frappe.get_all(
                    "Sub Branch Table",  # The correct table DocType name
                    filters={"parent": employee.name},
                    fields=["sub_branch"],  # The correct field name for sub-branch
                    pluck="sub_branch"
                )
                
                for sub_branch in additional_sub_branches:
                    if sub_branch:  # Check for null values
                        sub_branch_conditions.append(f"`tabPurchase Order`.custom_sub_branch = '{sub_branch}'")
            except Exception as e:
                # Log error but continue execution
                frappe.log_error(f"Error fetching sub branches: {str(e)}", "Permission Query Error")

        # Combine sub-branch conditions with OR
        if sub_branch_conditions:
            conditions.append(f"({' OR '.join(sub_branch_conditions)})")
        
        # Combine all conditions with AND
        if conditions:
            return " AND ".join(conditions)
        else:
            return "1=0"
    
    # Then check if user has Person Raising Request role
    elif "Person Raising Request" in roles:
        # Get employee linked to the user
        employee = frappe.db.get_value("Employee", 
            {"user_id": user}, 
            ["custom_supplier", "branch", "custom_sub_branch"], 
            as_dict=1
        )
        
        if not employee:
            return "1=0"  # Return false condition if no employee found
            
        conditions = []
        
        # Build conditions based on employee details
        if employee.custom_supplier:
            conditions.append(f"`tabPurchase Order`.supplier = '{employee.custom_supplier}'")
        if employee.branch:
            conditions.append(f"`tabPurchase Order`.custom_branch = '{employee.branch}'")
        if employee.custom_sub_branch:
            conditions.append(f"`tabPurchase Order`.custom_sub_branch = '{employee.custom_sub_branch}'")
            
        # If any conditions exist, join them with AND
        if conditions:
            return " AND ".join(conditions)
        else:
            return "1=0"  # Return false condition if no matching criteria
    
    # Check if user has Supplier role
    elif "Supplier" in roles:
        # Get supplier linked to the user using custom_user field
        supplier = frappe.db.get_value("Supplier", {"custom_user": user}, "name")
        
        if not supplier:
            return "1=0"  # Return false condition if no supplier found
            
        # Return condition to match PO supplier with user's supplier
        return f"`tabPurchase Order`.supplier = '{supplier}'"

    # Check if user has Vendor User role
    elif "Vendor User" in roles:
        # Get vendor linked to the user
        vendor = frappe.db.get_value("Vendor", {"user_id": user}, "name")
        
        if not vendor:
            return "1=0"  # Return false condition if no vendor found
            
        # Return condition to match PO custom_vendor with user's vendor
        return f"`tabPurchase Order`.custom_vendor = '{vendor}'"
    
    # If user has none of the allowed roles
    else:
        frappe.throw(_("Not Allowed to see PO"))
        return "1=0"


def has_permission(doc, user=None, permission_type=None):
    """
    Additional permission check at document level
    """
    if not user:
        user = frappe.session.user
    
    roles = frappe.get_roles(user)
    
    # Administrator can see all documents
    if "Administrator" in roles:
        return True
    
    # Check for Person Raising Request Branch roles
    elif "Person Raising Request Branch" in roles:
        # Get employee details
        employee = frappe.db.get_value("Employee", 
            {"user_id": user}, 
            ["custom_supplier", "branch"], 
            as_dict=1
        )
        
        if not employee:
            return False
            
        # Check if document matches employee criteria
        matches_supplier = (doc.supplier == employee.custom_supplier)
        matches_branch = (doc.custom_branch == employee.branch)
        
        return matches_supplier and matches_branch
    
    # Check for Approver roles
    elif "Requisition Approver" in roles or "PO Approver" in roles:
        # Get employee details
        employee = frappe.db.get_value("Employee", 
            {"user_id": user}, 
            ["name", "custom_supplier", "branch", "custom_sub_branch"], 
            as_dict=1
        )
        
        if not employee:
            return False
        
        try:    
            # Get additional sub-branches from the custom_sub_branch_list table field
            additional_sub_branches = frappe.get_all(
                "Sub Branch Table",  # The correct DocType name
                filters={"parent": employee.name},
                fields=["sub_branch"],  # The correct field name
                pluck="sub_branch"
            )
        except Exception as e:
            frappe.log_error(f"Error in has_permission: {str(e)}", "Permission Error")
            additional_sub_branches = []
        
        # Check if document matches required employee criteria
        matches_supplier = (doc.supplier == employee.custom_supplier)
        matches_branch = (doc.custom_branch == employee.branch)
        
        # Check if document's sub-branch matches either primary or any additional sub-branch
        matches_sub_branch = (doc.custom_sub_branch == employee.custom_sub_branch or 
                             doc.custom_sub_branch in additional_sub_branches)
        
        # For approver roles, must match supplier and branch, AND match at least one sub-branch
        return matches_supplier and matches_branch and matches_sub_branch
    
    # Check Person Raising Request role
    elif "Person Raising Request" in roles:
        # Get employee details
        employee = frappe.db.get_value("Employee", 
            {"user_id": user}, 
            ["custom_supplier", "branch", "custom_sub_branch"], 
            as_dict=1
        )
        
        if not employee:
            return False
            
        # Check if document matches employee criteria
        matches_supplier = (doc.supplier == employee.custom_supplier)
        matches_branch = (doc.custom_branch == employee.branch)
        matches_sub_branch = (doc.custom_sub_branch == employee.custom_sub_branch)
        
        return matches_supplier and matches_branch and matches_sub_branch
    
    # Check Supplier role
    elif "Supplier" in roles:
        # Get supplier linked to the user using custom_user field
        supplier = frappe.db.get_value("Supplier", {"custom_user": user}, "name")
        
        if not supplier:
            return False
            
        # Check if document matches supplier
        return doc.supplier == supplier

    # Check Vendor User role
    elif "Vendor User" in roles:
        # Get vendor linked to the user
        vendor = frappe.db.get_value("Vendor", {"user_id": user}, "name")
        
        if not vendor:
            return False
            
        # Check if document matches vendor
        return doc.custom_vendor == vendor
    
    return False

@frappe.whitelist()
def calculate_gst_values(doc_name):
    """
    Calculate GST values for Purchase Order and save the document.
    Can be called from client-side.
    """
    try:
        # Get the Purchase Order document
        po_doc = frappe.get_doc("Purchase Order", doc_name)
        
        # Document level totals
        doc_total_sgst = 0
        doc_total_cgst = 0
        doc_total_igst = 0
        doc_total_tax = 0
        doc_grand_total = 0
        doc_net_total = 0
        
        # Process each item in the items table
        for item in po_doc.get('items', []):
            # Convert tax values to float, defaulting to 0 if None
            sgst_amount = float(item.get('sgst_amount') or 0)
            cgst_amount = float(item.get('cgst_amount') or 0)
            igst_amount = float(item.get('igst_amount') or 0)
            net_amount = float(item.get('net_amount') or 0)
            
            # Calculate item totals
            item_total_tax = sgst_amount + cgst_amount + igst_amount
            item_grand_total = net_amount + item_total_tax
            
            # Set custom fields for the item
            item.custom_gstn_value = item_total_tax
            item.custom_grand_total = item_grand_total
            
            # Add to document totals
            doc_total_sgst += sgst_amount
            doc_total_cgst += cgst_amount
            doc_total_igst += igst_amount
            doc_total_tax += item_total_tax
            doc_grand_total += item_grand_total
            doc_net_total += net_amount
        
        # Update document-level custom fields if they exist
        if hasattr(po_doc, 'custom_total_sgst'):
            po_doc.custom_total_sgst = doc_total_sgst
        
        if hasattr(po_doc, 'custom_total_cgst'):
            po_doc.custom_total_cgst = doc_total_cgst
        
        if hasattr(po_doc, 'custom_total_igst'):
            po_doc.custom_total_igst = doc_total_igst
        
        if hasattr(po_doc, 'custom_total_tax'):
            po_doc.custom_total_tax = doc_total_tax
        
        if hasattr(po_doc, 'custom_net_total'):
            po_doc.custom_net_total = doc_net_total
        
        if hasattr(po_doc, 'custom_grand_total'):
            po_doc.custom_grand_total = doc_grand_total
        
        # Save the document with ignore_permissions to ensure it saves
        po_doc.save(ignore_permissions=True)
        frappe.db.commit()
        
        return {
            "status": "success",
            "message": _("GST values calculated successfully")
        }
    
    except Exception as e:
        frappe.log_error(f"Error calculating GST values: {str(e)}", 
                        "GST Calculation Error")
        return {
            "status": "error",
            "message": str(e)
        }


