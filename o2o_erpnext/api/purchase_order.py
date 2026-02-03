import frappe
from frappe import _
from frappe.utils import flt, get_datetime, today
from frappe.exceptions import DoesNotExistError
import datetime
import json
import uuid
from frappe.utils import now

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
            # Set supplier code based on supplier
            if po_doc.supplier:
                po_doc.custom_supplier_code = po_doc.supplier[:3].upper() if po_doc.supplier else ""
            
        branch_approver_info = None
        if employee.branch:
            po_doc.custom_branch = employee.branch
            
            # Find branch approver once we set the branch
            branch_approver_info = get_branch_approver_info(employee.branch)
            if branch_approver_info:
                po_doc.custom__approver_name_and_email = branch_approver_info
                
                # Extract and set the PO approver email
                approver_parts = branch_approver_info.split(':', 1)
                if len(approver_parts) > 1:
                    po_doc.custom_po_approver_email = approver_parts[1]
            
        requisition_approver_info = None
        if employee.custom_sub_branch:
            po_doc.custom_sub_branch = employee.custom_sub_branch
            
            # Only set requisition approver if approval flow is "3 way"
            if employee.custom_supplier:
                approval_flow = frappe.db.get_value("Supplier", employee.custom_supplier, "custom_approval_flow")
                if approval_flow == "3 way":
                    # Find requisition approver once we set the sub-branch
                    requisition_approver_info = get_sub_branch_requisition_approver(employee.custom_sub_branch)
                    if requisition_approver_info:
                        po_doc.custom_requisition_approver_name_and_email = requisition_approver_info
                        
                        # Extract and set the requisition approver email
                        approver_parts = requisition_approver_info.split(':', 1)
                        if len(approver_parts) > 1:
                            po_doc.custom_requisition_approver_email = approver_parts[1]
        
        # Set order code
        update_order_code(po_doc)
            
        if not doc_name:
            response_data = {
                "supplier": employee.custom_supplier,
                "custom_branch": employee.branch,
                "custom_sub_branch": employee.custom_sub_branch,
                "custom_supplier_code": po_doc.custom_supplier_code if hasattr(po_doc, 'custom_supplier_code') else "",
                "custom_order_code": po_doc.custom_order_code if hasattr(po_doc, 'custom_order_code') else ""
            }
            
            if branch_approver_info:
                response_data["custom__approver_name_and_email"] = branch_approver_info
                # Also include the PO approver email in the response
                approver_parts = branch_approver_info.split(':', 1)
                if len(approver_parts) > 1:
                    response_data["custom_po_approver_email"] = approver_parts[1]
                
            if requisition_approver_info:
                response_data["custom_requisition_approver_name_and_email"] = requisition_approver_info
                # Also include the requisition approver email in the response
                approver_parts = requisition_approver_info.split(':', 1)
                if len(approver_parts) > 1:
                    response_data["custom_requisition_approver_email"] = approver_parts[1]
                
            return {
                "status": "success",
                "message": _("Default values set successfully"),
                "data": response_data
            }
        
        po_doc.save(ignore_version=True)
        frappe.db.commit()
        
        return {
            "status": "success",
            "message": _("Purchase Order updated successfully")
        }
            
    except Exception as e:
        frappe.log_error(f"Error in Purchase Order auto-fill: {str(e)}", 
                        "Purchase Order API Error")
        raise e


def update_order_code(po_doc):
    """Update Order Code based on transaction date"""
    if po_doc.docstatus == 0:  # Only for draft documents
        if not po_doc.transaction_date:
            po_doc.transaction_date = today()
            
        try:
            date_obj = get_datetime(po_doc.transaction_date).date()
            weekday = date_obj.strftime("%a").upper()
            year_yy = date_obj.strftime("%y")
            
            po_doc.custom_order_code = f"POA{weekday}{year_yy}"
        except Exception as e:
            frappe.log_error(f"Error updating order code: {str(e)}", "Order Code Error")


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
        
        # Update the Purchase Order with approver name and email
        frappe.db.set_value("Purchase Order", purchase_order_name, "custom__approver_name_and_email", approver_info)
        
        # Extract and set the email in the dedicated field
        if approver.custom_user_email:
            frappe.db.set_value("Purchase Order", purchase_order_name, "custom_po_approver_email", approver.custom_user_email)
        
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

# get_permission_query_conditions - Updated version
def get_permission_query_conditions(user, doctype):
    """
    Returns SQL conditions to filter Purchase Orders based on user roles and related employee/supplier data.
    """
    roles = frappe.get_roles(user)

    if "Administrator" in roles:
        return None  # Administrator can see all
    
    # Check if user has Person Raising Request Branch role
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

        # --- Sub-Branch Filtering (Primary OR any secondary sub-branch OR no sub-branch at all) ---
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

        # 3. ADDED: Branch-level POs with no sub-branch specified
        sub_branch_conditions.append("(`tabPurchase Order`.custom_sub_branch IS NULL OR TRIM(`tabPurchase Order`.custom_sub_branch) = '')")
        
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

# has_permission - Updated version
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
        
        # Check if document's sub-branch matches either primary or any additional sub-branch OR is empty (branch-level PO)
        matches_sub_branch = (
            doc.custom_sub_branch == employee.custom_sub_branch or 
            doc.custom_sub_branch in additional_sub_branches or
            not doc.custom_sub_branch  # ADDED: Branch-level POs with no sub-branch
        )
        
        # For approver roles, must match supplier and branch, AND match at least one sub-branch or have no sub-branch
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
            item.custom_gstn_value = item_total_tax
            item.custom_grand_total = net_amount + item_total_tax
            
            # Add to document totals
            doc_total_sgst += sgst_amount
            doc_total_cgst += cgst_amount
            doc_total_igst += igst_amount
            doc_total_tax += item_total_tax
            doc_grand_total += item_total_tax + net_amount
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
            
        # Add this line to set the custom_total_gstn field
        if hasattr(po_doc, 'custom_total_gstn'):
            po_doc.custom_total_gstn = doc_total_tax
        
        if hasattr(po_doc, 'custom_net_total'):
            po_doc.custom_net_total = doc_net_total
        
        if hasattr(po_doc, 'custom_grand_total'):
            po_doc.custom_grand_total = doc_grand_total
        
        # Save the document with ignore_permissions to ensure it saves
        # Also use ignore_version to bypass timestamp checks
        po_doc.save(ignore_permissions=True, ignore_version=True)
        frappe.db.commit()
        
        return {
            "status": "success",
            #"message": _("GST values calculated successfully")
        }
    
    except Exception as e:
        frappe.log_error(f"Error calculating GST values: {str(e)}", 
                        "GST Calculation Error")
        return {
            "status": "error",
            "message": str(e)
        }

@frappe.whitelist()
def calculate_item_gst_values(items_json):
    """
    Calculate GST values for items without saving to the database.
    For client-side use to preview GST calculations before saving.
    """
    try:
        items = json.loads(items_json)
        result = []
        
        for item in items:
            # Convert tax values to float, defaulting to 0 if None
            sgst_amount = float(item.get('sgst_amount') or 0)
            cgst_amount = float(item.get('cgst_amount') or 0)
            igst_amount = float(item.get('igst_amount') or 0)
            net_amount = float(item.get('net_amount') or 0)
            
            # Calculate item totals
            item_total_tax = sgst_amount + cgst_amount + igst_amount
            grand_total = net_amount + item_total_tax
            
            result.append({
                'name': item.get('name'),
                'custom_gstn_value': item_total_tax,
                'custom_grand_total': grand_total
            })
            
        return {
            "status": "success",
            "data": result
        }
    
    except Exception as e:
        frappe.log_error(f"Error calculating item GST values: {str(e)}", 
                        "Item GST Calculation Error")
        return {
            "status": "error",
            "message": str(e)
        }
    
@frappe.whitelist()
def create_test_po_for_address_debug():
    """Create a test Purchase Order with Allahabad sub-branch for debugging"""
    try:
        # Create a new Purchase Order
        po = frappe.new_doc("Purchase Order")
        po.supplier = "Bandhan AMC Limited"
        po.custom_branch = "Mumbai (IB)"
        po.custom_sub_branch = "Allahabad"
        po.transaction_date = frappe.utils.today()
        po.schedule_date = frappe.utils.add_days(frappe.utils.today(), 20)
        po.company = "Bandhan AMC Limited"
        
        # Add a test item
        po.append("items", {
            "item_code": "Test Item",
            "item_name": "Test Item for Address Debug",
            "qty": 1,
            "rate": 100,
            "schedule_date": po.schedule_date,
            "custom_product_type": "OPEX"
        })
        
        po.insert(ignore_permissions=True)
        frappe.db.commit()
        
        return {
            "status": "success",
            "po_name": po.name,
            "message": f"Test PO created: {po.name}"
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

@frappe.whitelist()
def study_branch_doctype_structure():
    """Study Branch and Sub Branch doctype structures for address fields"""
    try:
        result = {}
        
        # Study Branch doctype
        print("=== BRANCH DOCTYPE FIELDS ===")
        branch_meta = frappe.get_meta('Branch')
        branch_fields = []
        for field in branch_meta.fields:
            if 'address' in field.fieldname.lower() or field.fieldtype in ['Small Text', 'Text', 'Long Text', 'Data']:
                branch_fields.append({
                    'fieldname': field.fieldname,
                    'fieldtype': field.fieldtype,
                    'label': field.label
                })
                print(f"   {field.fieldname}: {field.fieldtype} - {field.label}")
        
        result['branch_fields'] = branch_fields
        
        # Get sample Branch data
        branch_sample = frappe.db.sql("SELECT name FROM `tabBranch` LIMIT 1", as_dict=True)
        if branch_sample:
            branch_doc = frappe.get_doc('Branch', branch_sample[0].name)
            print(f"\n=== SAMPLE BRANCH: {branch_doc.name} ===")
            branch_data = {}
            for field_info in branch_fields:
                field_name = field_info['fieldname']
                value = getattr(branch_doc, field_name, None)
                if value:
                    branch_data[field_name] = str(value)[:200] + "..." if len(str(value)) > 200 else str(value)
                    print(f"   {field_name}: {branch_data[field_name]}")
            result['sample_branch'] = branch_data
        
        print("\n=== SUB BRANCH DOCTYPE FIELDS ===")
        # Study Sub Branch doctype
        sub_branch_meta = frappe.get_meta('Sub Branch')
        sub_branch_fields = []
        for field in sub_branch_meta.fields:
            if 'address' in field.fieldname.lower() or field.fieldtype in ['Small Text', 'Text', 'Long Text', 'Data']:
                sub_branch_fields.append({
                    'fieldname': field.fieldname,
                    'fieldtype': field.fieldtype,
                    'label': field.label
                })
                print(f"   {field.fieldname}: {field.fieldtype} - {field.label}")
        
        result['sub_branch_fields'] = sub_branch_fields
        
        # Get sample Sub Branch data
        sub_branch_sample = frappe.db.sql("SELECT name FROM `tabSub Branch` WHERE name = 'Allahabad' LIMIT 1", as_dict=True)
        if sub_branch_sample:
            sub_branch_doc = frappe.get_doc('Sub Branch', sub_branch_sample[0].name)
            print(f"\n=== SAMPLE SUB BRANCH: {sub_branch_doc.name} ===")
            sub_branch_data = {}
            for field_info in sub_branch_fields:
                field_name = field_info['fieldname']
                value = getattr(sub_branch_doc, field_name, None)
                if value:
                    sub_branch_data[field_name] = str(value)[:200] + "..." if len(str(value)) > 200 else str(value)
                    print(f"   {field_name}: {sub_branch_data[field_name]}")
            result['sample_sub_branch'] = sub_branch_data
        
        return result
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {"status": "error", "message": str(e)}

@frappe.whitelist()
def debug_address_display_issue():
    """Debug function to check address display issue"""
    try:
        print("=== DEBUGGING ADDRESS DISPLAY ISSUE ===")
        
        # 1. Check Allahabad-Billing address content
        print("\n1. Checking Allahabad-Billing address document:")
        address_doc = frappe.get_doc('Address', 'Allahabad-Billing')
        print(f"   Address Line 1: {address_doc.address_line1}")
        print(f"   City: {address_doc.city}")
        print(f"   State: {address_doc.state}")
        print(f"   Country: {address_doc.country}")
        print(f"   Pincode: {address_doc.pincode}")
        
        formatted_display = address_doc.get_display()
        print(f"   Formatted Display: {formatted_display}")
        print()
        
        # 2. Find any Purchase Order to test with
        print("2. Finding any Purchase Order to test address update:")
        po_list = frappe.db.sql("""
            SELECT name, supplier_address, address_display, custom_sub_branch, custom_branch
            FROM `tabPurchase Order` 
            ORDER BY modified DESC
            LIMIT 1
        """, as_dict=True)
        
        if po_list:
            po_data = po_list[0]
            print(f"   Found PO: {po_data.name}")
            print(f"   Current Sub Branch: {po_data.custom_sub_branch}")
            print(f"   Current Branch: {po_data.custom_branch}")
            print(f"   Current Supplier Address: {po_data.supplier_address}")
            print(f"   Current Address Display: {po_data.address_display}")
            print()
            
            # Test address update with Allahabad sub-branch
            print("3. Testing address update with Allahabad sub-branch:")
            result = fetch_branch_or_sub_branch_addresses(
                purchase_order_name=po_data.name,
                sub_branch='Allahabad',
                branch='Mumbai (IB)'
            )
            print(f"   Update Result: {result}")
            
            # Check after update
            updated_po = frappe.db.get_value('Purchase Order', po_data.name, 
                                           ['supplier_address', 'address_display'], as_dict=True)
            print(f"   After Update - Supplier Address: {updated_po.supplier_address}")
            print(f"   After Update - Address Display: {updated_po.address_display}")
            print()
            
            # Compare addresses
            print("4. Address Comparison:")
            print(f"   Expected (Allahabad-Billing): {formatted_display}")
            print(f"   Actual (PO after update): {updated_po.address_display}")
            print(f"   Match: {formatted_display == updated_po.address_display}")
            
            return {
                "status": "success",
                "po_name": po_data.name,
                "expected_display": formatted_display,
                "actual_display": updated_po.address_display,
                "match": formatted_display == updated_po.address_display,
                "update_result": result
            }
        else:
            return {"status": "error", "message": "No Purchase Orders found"}
            
    except Exception as e:
        return {"status": "error", "message": str(e)}

@frappe.whitelist()
def get_correct_address_display(sub_branch=None, branch=None):
    """Get correct address display content from Branch/Sub Branch to prevent overrides"""
    try:
        billing_display = None
        shipping_display = None
        
        # First try sub-branch
        if sub_branch and sub_branch.strip() != "":
            try:
                sub_branch_doc = frappe.get_doc("Sub Branch", sub_branch)
                billing_display = getattr(sub_branch_doc, 'custom_billing_address_details', None)
                shipping_display = getattr(sub_branch_doc, 'custom_shipping_address_details', None)
            except frappe.exceptions.DoesNotExistError:
                pass
        
        # If no sub-branch data, try branch
        if (not billing_display and not shipping_display) and branch and branch.strip() != "":
            try:
                branch_doc = frappe.get_doc("Branch", branch)
                billing_display = getattr(branch_doc, 'custom_billing_address_details', None)
                shipping_display = getattr(branch_doc, 'custom_shipping_address_details', None)
            except frappe.exceptions.DoesNotExistError:
                pass
        
        return {
            "status": "success",
            "billing_display": billing_display,
            "shipping_display": shipping_display
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@frappe.whitelist()
def fetch_branch_or_sub_branch_addresses(purchase_order_name=None, sub_branch=None, branch=None):
    """
    Fetch billing and shipping addresses from sub-branch or branch and update Purchase Order.
    
    Args:
        purchase_order_name (str, optional): Purchase Order document name
        sub_branch (str, optional): Sub-branch name to fetch addresses from
        branch (str, optional): Branch name to fetch addresses from (used if sub_branch not provided)
        
    Returns:
        dict: Result with status, message and addresses
    """
    try:
        # Handle different input scenarios
        po_doc = None
        if purchase_order_name and not purchase_order_name.startswith('new-'):
            try:
                # Only try to load the PO if it's not a new unsaved document
                po_doc = frappe.get_doc("Purchase Order", purchase_order_name)
                if not sub_branch:
                    sub_branch = po_doc.custom_sub_branch
                if not branch:
                    branch = po_doc.custom_branch
            except frappe.exceptions.DoesNotExistError:
                return {"status": "error", "message": "Purchase Order not found"}
        
        billing_address = None
        shipping_address = None
        source = None
        
        # First try to get addresses from sub-branch
        if sub_branch and sub_branch.strip() != "":
            # Fetch sub-branch document to get address fields
            try:
                sub_branch_doc = frappe.get_doc("Sub Branch", sub_branch)
                
                # Get address values
                billing_address = sub_branch_doc.address if hasattr(sub_branch_doc, 'address') else None
                shipping_address = sub_branch_doc.custom_shipping_address if hasattr(sub_branch_doc, 'custom_shipping_address') else None
                
                if billing_address or shipping_address:
                    source = "sub_branch"
            except frappe.exceptions.DoesNotExistError:
                # If sub-branch doesn't exist or has no addresses, continue to branch
                pass
                
        # If no addresses found, try to get addresses from branch
        if (not billing_address and not shipping_address) and branch and branch.strip() != "":
            try:
                branch_doc = frappe.get_doc("Branch", branch)
                
                # Get address values from branch
                billing_address = branch_doc.address if hasattr(branch_doc, 'address') else None
                shipping_address = branch_doc.custom_shipping_address if hasattr(branch_doc, 'custom_shipping_address') else None
                
                if billing_address or shipping_address:
                    source = "branch"
            except frappe.exceptions.DoesNotExistError:
                # Branch doesn't exist or has no addresses
                pass
        
        # If we found addresses (from either source), prepare result
        if billing_address or shipping_address:
            result = {
                "status": "success",
                "billing_address": billing_address,
                "shipping_address": shipping_address,
                "source": source
            }
            
            # If Purchase Order is provided and it's a valid document, update it
            if po_doc and purchase_order_name:
                # CRITICAL: Only update if document is in draft status (docstatus = 0)
                # Do not update submitted/cancelled documents to avoid "Not Saved" status
                if po_doc.docstatus != 0:
                    return result  # Skip update for submitted/cancelled documents
                
                # Use direct SQL update to avoid concurrent modification issues
                update_fields = {}
                if billing_address:
                    update_fields["supplier_address"] = billing_address
                if shipping_address:
                    update_fields["shipping_address"] = shipping_address
                
                if update_fields:
                    try:
                        # Get address display content first before updating links
                        billing_display_content = None
                        shipping_display_content = None
                        
                        if billing_address:
                            if source == "sub_branch" and sub_branch:
                                billing_display_content = frappe.db.get_value("Sub Branch", sub_branch, "custom_billing_address_details")
                            elif source == "branch" and branch:
                                billing_display_content = frappe.db.get_value("Branch", branch, "custom_billing_address_details")
                        
                        if shipping_address:
                            if source == "sub_branch" and sub_branch:
                                shipping_display_content = frappe.db.get_value("Sub Branch", sub_branch, "custom_shipping_address_details")
                            elif source == "branch" and branch:
                                shipping_display_content = frappe.db.get_value("Branch", branch, "custom_shipping_address_details")
                        
                        # Update address links and display fields together
                        if billing_display_content:
                            update_fields["address_display"] = billing_display_content
                        if shipping_display_content:
                            update_fields["shipping_address_display"] = shipping_display_content
                        
                        # Update all fields at once using SQL to bypass document versioning
                        frappe.db.set_value("Purchase Order", purchase_order_name, update_fields)
                        frappe.db.commit()
                        
                        # Force update again after a brief moment to prevent override
                        if billing_display_content or shipping_display_content:
                            force_update_fields = {}
                            if billing_display_content:
                                force_update_fields["address_display"] = billing_display_content
                            if shipping_display_content:
                                force_update_fields["shipping_address_display"] = shipping_display_content
                            
                            # Second update to ensure our values stick
                            frappe.db.set_value("Purchase Order", purchase_order_name, force_update_fields)
                            frappe.db.commit()
                    except Exception as e:
                        frappe.log_error(
                            message=f"Failed to update addresses: {str(e)}", 
                            title="Address update error"
                        )
            
            return result
        
        # If we get here, neither branch nor sub-branch had valid addresses
        return {
            "status": "warning",
            "message": "No addresses found"
        }
            
    except Exception as e:
        error_type = type(e).__name__
        frappe.log_error(
            message=f"Details: {str(e)}", 
            title=f"Address fetch error: {error_type}"
        )
        return {
            "status": "error",
            "message": f"Error fetching addresses: {error_type}"
        }

@frappe.whitelist()
def is_branch_level_user():
    """Check if current user has the branch-level role"""
    user_roles = frappe.get_roles(frappe.session.user)
    return 'Person Raising Request Branch' in user_roles

@frappe.whitelist()
def get_hierarchy_data(branch=None, sub_branch=None):
    """Get hierarchy data for validations"""
    result = {
        'sub_branch': None,
        'branch': None,
        'supplier': None,
        'is_branch_user': is_branch_level_user()
    }
    
    # Check if this is a branch-level PO (no sub-branch provided)
    is_branch_level_po = branch and not sub_branch
    
    # For branch-level users OR branch-level POs, only get branch and supplier
    if result['is_branch_user'] or is_branch_level_po:
        if branch:
            branch_data = frappe.get_value('Branch', branch,
                ['custom_supplier', 'custom_capex_budget', 'custom_opex_budget', 
                'custom_minimum_order_value', 'custom_maximum_order_value'],
                as_dict=1
            )
            result['branch'] = branch_data
            
            if branch_data and branch_data.get('custom_supplier'):
                supplier_data = frappe.get_value('Supplier', branch_data.get('custom_supplier'),
                    ['custom_capex_budget', 'custom_opex_budget', 'custom_minimum_order_value', 
                    'custom_maximum_order_value', 'custom_budget_start_date', 'custom_budget_end_date'],
                    as_dict=1
                )
                result['supplier'] = supplier_data
        
        # For branch-level POs, mark as branch user to use branch validations
        if is_branch_level_po:
            result['is_branch_user'] = True
    
    # For sub-branch users with sub-branch provided, get the full hierarchy
    else:
        if sub_branch:
            sub_branch_data = frappe.get_value('Sub Branch', sub_branch,
                ['branch', 'custom_supplier', 'capex_budget', 'opex_budget', 
                'minimum_order_value', 'maximum_order_value'],
                as_dict=1
            )
            result['sub_branch'] = sub_branch_data
            
            if sub_branch_data and sub_branch_data.get('branch'):
                branch_data = frappe.get_value('Branch', sub_branch_data.get('branch'),
                    ['custom_supplier', 'custom_capex_budget', 'custom_opex_budget', 
                    'custom_minimum_order_value', 'custom_maximum_order_value'],
                    as_dict=1
                )
                result['branch'] = branch_data
                
                if branch_data and branch_data.get('custom_supplier'):
                    supplier_data = frappe.get_value('Supplier', branch_data.get('custom_supplier'),
                        ['custom_capex_budget', 'custom_opex_budget', 'custom_minimum_order_value', 
                        'custom_maximum_order_value', 'custom_budget_start_date', 'custom_budget_end_date'],
                        as_dict=1
                    )
                    result['supplier'] = supplier_data
    
    return result

def validate_purchase_order_hook(doc, method):
    """Hook wrapper for Frappe's validate event - handles all validation server-side"""
    # Skip during migrations only
    if frappe.flags.in_migrate:
        return
    
    # Skip validation if document is being auto-saved or if it's a field update
    if not doc.get('items') or len(doc.get('items')) == 0:
        return  # No items, no validation needed
        
    # Skip validation for documents that are just being created/updated without explicit save
    if hasattr(doc, 'flags') and (doc.flags.ignore_validate or doc.flags.ignore_permissions):
        return
        
    try:
        # Convert doc to dict for validation
        doc_dict = doc.as_dict()
        
        # Improved document detection logic
        is_new_document = True
        
        # Check if document exists in database
        if doc.name and not doc.name.startswith("new-"):
            if frappe.db.exists("Purchase Order", doc.name):
                is_new_document = False
        
        # Additional check: if document has docstatus > 0, it's definitely existing
        if doc.docstatus > 0:
            is_new_document = False
        
        # Call the main validation function
        result = validate_purchase_order_internal(doc_dict, is_new_document)
        
        # If validation fails, throw error with specific message (no wrapping)
        if result.get("status") == "error":
            error_message = result.get("message", "Validation failed")
            # Only throw validation errors, don't break document creation for system errors
            frappe.throw(error_message)
            
    except frappe.ValidationError:
        # Re-raise validation errors (these are intentional)
        raise
    except Exception as e:
        # Log system errors but don't break the document creation
        frappe.log_error(f"PO Validation System Error: {str(e)}", "PO Validation System Error")
        # Don't re-raise system exceptions to allow document creation

def on_submit_purchase_order(doc, method):
    """Hook for Purchase Order submission - update budgets"""
    try:
        # Calculate CAPEX and OPEX totals
        capex_total, opex_total = calculate_capex_opex_totals(doc.as_dict())
        
        # Update budgets
        update_budgets(doc.name, capex_total, opex_total)
        
        frappe.log_error(f"Budget updated for PO {doc.name}: CAPEX={capex_total}, OPEX={opex_total}", "PO Budget Update")
        
    except Exception as e:
        frappe.log_error(f"Error updating budgets for PO {doc.name}: {str(e)}", "PO Budget Update Error")

@frappe.whitelist()
def validate_purchase_order(doc_name=None, doc_json=None):
    """Client-side validation function"""
    if doc_name:
        doc = frappe.get_doc("Purchase Order", doc_name)
        doc_dict = doc.as_dict()
        is_new_document = False
    elif doc_json:
        doc_dict = json.loads(doc_json)
        # Better detection: check if document exists in database
        doc_name_from_json = doc_dict.get('name')
        if doc_name_from_json:
            try:
                frappe.get_doc("Purchase Order", doc_name_from_json)
                is_new_document = False  # Document exists in database
            except frappe.DoesNotExistError:
                is_new_document = True   # Document doesn't exist yet
        else:
            is_new_document = True       # No name means definitely new
    else:
        return {"status": "error", "message": "Either doc_name or doc_json must be provided"}
    
    return validate_purchase_order_internal(doc_dict, is_new_document)

def validate_purchase_order_internal(doc, is_new_document=True):
    """Validate Purchase Order - comprehensive validation function"""
    try:
        
        validation_results = {
            "status": "success",
            "validations": {},
            "capex_total": 0,
            "opex_total": 0
        }
        
        # Basic validations
        validation_results["validations"]["branch"] = validate_branch_mandatory(doc)
        
        # Sub-branch validation - role-based for new docs, structure-based for existing
        validation_results["validations"]["sub_branch"] = validate_sub_branch_mandatory(doc, is_new_document)
        
        # Hierarchy validation - always validate the relationship
        validation_results["validations"]["hierarchy"] = validate_hierarchy(doc)
            
        validation_results["validations"]["transaction_date"] = validate_transaction_date_mandatory(doc)
        
        # If we have items, do more validations
        if doc.get('items') and len(doc.get('items')) > 0:
            # Calculate CAPEX and OPEX totals
            capex_total, opex_total = calculate_capex_opex_totals(doc)
            validation_results["capex_total"] = capex_total
            validation_results["opex_total"] = opex_total
            
            # Validate order value and budget dates (always)
            validation_results["validations"]["order_value"] = validate_order_value(doc)
            validation_results["validations"]["budget_dates"] = validate_budget_dates(doc)
            
            # Budget validation for both NEW and EXISTING documents
            if is_new_document:  # New document - full budget validation
                validation_results["validations"]["budgets"] = validate_budgets(doc, capex_total, opex_total)
            else:  # Existing document - incremental budget validation
                validation_results["validations"]["budgets"] = validate_incremental_budgets(doc, capex_total, opex_total)
        
        # Check if any validation failed
        for key, result in validation_results["validations"].items():
            if result.get("status") == "error":
                validation_results["status"] = "error"
                validation_results["message"] = result.get("message", f"{key} validation failed")
                break
                
        return validation_results
    
    except Exception as e:
        frappe.log_error(f"Error validating Purchase Order: {str(e)}",
                      "Validation Error")
        return {
            "status": "error", 
            "message": f"Validation error: {str(e)}"
        }

def validate_branch_mandatory(doc):
    """Validate that branch is provided"""
    if not doc.get('custom_branch'):
        return {
            "status": "error",
            "message": "Branch is mandatory for Purchase Order"
        }
    return {"status": "success"}

def validate_sub_branch_mandatory(doc, is_new_document=True):
    """Validate that sub-branch is provided based on user roles and workflow"""
    # Get current user info
    current_user = frappe.session.user
    user_roles = frappe.get_roles(current_user)
    has_branch_role = 'Person Raising Request Branch' in user_roles
    has_request_role = 'Person Raising Request' in user_roles
    has_po_approver_role = 'PO Approver' in user_roles
    has_requisition_approver_role = 'Requisition Approver' in user_roles
    
    # Check PO structure
    has_branch = bool(doc.get('custom_branch'))
    has_sub_branch = bool(doc.get('custom_sub_branch'))
    is_branch_level_po = has_branch and not has_sub_branch
    
    # Validation logic continues below
    
    # CASE 1: For existing documents (editing/submitting), always allow
    # PO Approvers and Requisition Approvers only work with existing POs
    if not is_new_document:
        return {"status": "success"}
    
    # CASE 2: For new documents (creation), only request raisers can create
    if is_new_document:
        # Only Person Raising Request roles can create new POs
        if not (has_branch_role or has_request_role):
            return {
                "status": "error",
                "message": "Only request raisers can create new Purchase Orders"
            }
        
        # Person Raising Request Branch can create branch-level POs (no sub-branch required)
        if has_branch_role and is_branch_level_po:
            return {"status": "success"}
        
        # Person Raising Request must provide sub-branch
        if has_request_role and not has_sub_branch:
            return {
                "status": "error",
                "message": "Sub-branch is mandatory for Purchase Order"
            }
        
        # If sub-branch is provided, always allow
        if has_sub_branch:
            return {"status": "success"}
    return {"status": "success"}

def validate_transaction_date_mandatory(doc):
    """Validate that transaction date is provided"""
    if not doc.get('transaction_date'):
        return {
            "status": "error",
            "message": "Transaction Date is mandatory"
        }
    return {"status": "success"}

def validate_hierarchy(doc):
    """Validate branch and sub-branch hierarchy relationship"""
    try:
        # Get hierarchy data
        hierarchy_data = get_hierarchy_data(
            branch=doc.get('custom_branch'),
            sub_branch=doc.get('custom_sub_branch')
        )
        
        # Determine validation level based on PO structure (not user role)
        has_sub_branch = bool(doc.get('custom_sub_branch'))
        
        if not has_sub_branch:
            # Branch-level PO (no sub-branch) - validate against branch only
            if not hierarchy_data['branch']:
                return {
                    "status": "error",
                    "message": "Could not fetch branch details"
                }
            return {"status": "success"}
        
        # Sub-branch level PO (has sub-branch) - check the full hierarchy
        else:
            if not hierarchy_data['sub_branch']:
                return {
                    "status": "error",
                    "message": f"Could not fetch sub-branch details for '{doc.get('custom_sub_branch')}'. Please check if the sub-branch exists and is properly configured."
                }
            
            if hierarchy_data['sub_branch'].get('branch') != doc.get('custom_branch'):
                return {
                    "status": "error",
                    "message": "Selected sub-branch does not belong to the selected branch"
                }
            return {"status": "success"}
    
    except Exception as e:
        frappe.log_error(f"Error validating hierarchy: {str(e)}", "Hierarchy Validation Error")
        return {
            "status": "error",
            "message": f"Error validating hierarchy: {str(e)}"
        }

def calculate_capex_opex_totals(doc):
    """Calculate total CAPEX and OPEX amounts"""
    capex_total = 0
    opex_total = 0
    
    if not doc.get('items'):
        return capex_total, opex_total
        
    for item in doc.get('items'):
        if not item.get('custom_product_type'):
            continue
            
        item_amount = flt(item.get('amount'))
        if item_amount:
            if item.get('custom_product_type') == 'Capex':
                capex_total += item_amount
            elif item.get('custom_product_type') == 'Opex':
                opex_total += item_amount
    
    return capex_total, opex_total

def validate_order_value(doc):
    """Validate minimum and maximum order values"""
    try:
        if not doc.get('items') or len(doc.get('items')) == 0:
            return {"status": "success"}
            
        total = flt(doc.get('total'))
        
        # Get hierarchy data
        hierarchy_data = get_hierarchy_data(
            branch=doc.get('custom_branch'),
            sub_branch=doc.get('custom_sub_branch')
        )
        
        if not hierarchy_data['supplier']:
            return {
                "status": "error",
                "message": "Could not fetch supplier details"
            }
        
        # Determine validation level based on PO structure (not user role)
        has_sub_branch = bool(doc.get('custom_sub_branch'))
        
        if not has_sub_branch:
            # Branch-level PO (no sub-branch) - validate against branch limits
            if not hierarchy_data['branch']:
                return {
                    "status": "error",
                    "message": "Could not fetch branch details"
                }
            
            # Branch minimum check
            branch_min = flt(hierarchy_data['branch'].get('custom_minimum_order_value'))
            if branch_min > 0 and total < branch_min:
                return {
                    "status": "error",
                    "message": f"Total order value ({total}) must be at least Branch's Minimum Order Value {branch_min}"
                }
            
            # Branch maximum check
            branch_max = flt(hierarchy_data['branch'].get('custom_maximum_order_value'))
            if branch_max > 0 and total > branch_max:
                return {
                    "status": "error",
                    "message": f"Total order value ({total}) must not exceed Branch's Maximum Order Value {branch_max}"
                }
            
            # Supplier minimum check
            supplier_min = flt(hierarchy_data['supplier'].get('custom_minimum_order_value'))
            if supplier_min > 0 and total < supplier_min:
                return {
                    "status": "error",
                    "message": f"Total order value ({total}) must be at least Supplier's Minimum Order Value {supplier_min}"
                }
            
            # Supplier maximum check
            supplier_max = flt(hierarchy_data['supplier'].get('custom_maximum_order_value'))
            if supplier_max > 0 and total > supplier_max:
                return {
                    "status": "error",
                    "message": f"Total order value ({total}) must not exceed Supplier's Maximum Order Value {supplier_max}"
                }
        
        # Sub-branch level PO (has sub-branch) - validate against sub-branch limits
        else:
            if not hierarchy_data['sub_branch']:
                return {
                    "status": "error",
                    "message": f"Could not fetch sub-branch details for '{doc.get('custom_sub_branch')}'. Please check if the sub-branch exists and is properly configured."
                }
            
            # Sub-Branch minimum check
            sub_branch_min = flt(hierarchy_data['sub_branch'].get('minimum_order_value'))
            if sub_branch_min > 0 and total < sub_branch_min:
                return {
                    "status": "error",
                    "message": f"Total order value ({total}) must be at least Sub-Branch's Minimum Order Value {sub_branch_min}"
                }
            
            # Sub-Branch maximum check
            sub_branch_max = flt(hierarchy_data['sub_branch'].get('maximum_order_value'))
            if sub_branch_max > 0 and total > sub_branch_max:
                return {
                    "status": "error",
                    "message": f"Total order value ({total}) must not exceed Sub-Branch's Maximum Order Value {sub_branch_max}"
                }
            
            # Supplier minimum check
            supplier_min = flt(hierarchy_data['supplier'].get('custom_minimum_order_value'))
            if supplier_min > 0 and total < supplier_min:
                return {
                    "status": "error",
                    "message": f"Total order value ({total}) must be at least Supplier's Minimum Order Value {supplier_min}"
                }
            
            # Supplier maximum check
            supplier_max = flt(hierarchy_data['supplier'].get('custom_maximum_order_value'))
            if supplier_max > 0 and total > supplier_max:
                return {
                    "status": "error",
                    "message": f"Total order value ({total}) must not exceed Supplier's Maximum Order Value {supplier_max}"
                }
        
        return {"status": "success"}
    
    except Exception as e:
        frappe.log_error(f"Error validating order value: {str(e)}", "Order Value Validation Error")
        return {
            "status": "error",
            "message": f"Error validating order value: {str(e)}"
        }

def validate_budget_dates(doc):
    """Validate transaction date against budget dates"""
    try:
        transaction_date = get_datetime(doc.get('transaction_date')).date()
        transaction_day = transaction_date.day
        
        # Get hierarchy data
        hierarchy_data = get_hierarchy_data(
            branch=doc.get('custom_branch'),
            sub_branch=doc.get('custom_sub_branch')
        )
        
        if not hierarchy_data['supplier']:
            return {
                "status": "error",
                "message": "Could not fetch supplier details"
            }
        
        # Parse budget days as integers
        try:
            budget_start_day = int(hierarchy_data['supplier'].get('custom_budget_start_date', 1))
            budget_end_day = int(hierarchy_data['supplier'].get('custom_budget_end_date', 31))
        except (ValueError, TypeError):
            budget_start_day = 1
            budget_end_day = 31
        
        if transaction_day < budget_start_day or transaction_day > budget_end_day:
            return {
                "status": "error",
                "message": f"Transaction date day ({transaction_day}) must be within supplier's budget days range: {budget_start_day} to {budget_end_day}"
            }
        
        return {"status": "success"}
    
    except Exception as e:
        frappe.log_error(f"Error validating budget dates: {str(e)}", "Budget Dates Validation Error")
        return {
            "status": "error",
            "message": f"Error validating budget dates: {str(e)}"
        }

def validate_budgets(doc, capex_total, opex_total):
    """Validate CAPEX and OPEX budgets"""
    try:
        if not doc.get('items') or len(doc.get('items')) == 0:
            return {"status": "success"}
        
        # First check if all items have product type
        for item in doc.get('items'):
            if not item.get('custom_product_type'):
                return {
                    "status": "error",
                    "message": f"Product Type must be set for item: {item.get('item_code') or item.get('idx')}"
                }
        
        # Get hierarchy data
        hierarchy_data = get_hierarchy_data(
            branch=doc.get('custom_branch'),
            sub_branch=doc.get('custom_sub_branch')
        )
        
        if not hierarchy_data['supplier']:
            return {
                "status": "error",
                "message": "Could not fetch supplier details"
            }
        
        # Determine validation level based on PO structure (not user role)
        has_sub_branch = bool(doc.get('custom_sub_branch'))
        
        if not has_sub_branch:
            # Branch-level PO (no sub-branch) - validate against branch budgets
            if not hierarchy_data['branch']:
                return {
                    "status": "error",
                    "message": "Could not fetch branch details"
                }
            
            # Validate CAPEX
            if capex_total > 0:
                # Branch - Check for zero/null budget first
                branch_capex = flt(hierarchy_data['branch'].get('custom_capex_budget'))
                if branch_capex <= 0:
                    return {
                        "status": "error",
                        "message": f"Cannot create Purchase Order: Branch CAPEX budget is not allocated or is zero (Current: {branch_capex})"
                    }
                if capex_total > branch_capex:
                    return {
                        "status": "error",
                        "message": f"Total Capex amount ({capex_total}) exceeds Branch Capex budget ({branch_capex})"
                    }
                
                # Supplier - Check for zero/null budget first
                supplier_capex = flt(hierarchy_data['supplier'].get('custom_capex_budget'))
                if supplier_capex <= 0:
                    return {
                        "status": "error",
                        "message": f"Cannot create Purchase Order: Supplier CAPEX budget is not allocated or is zero (Current: {supplier_capex})"
                    }
                if capex_total > supplier_capex:
                    return {
                        "status": "error",
                        "message": f"Total Capex amount ({capex_total}) exceeds Supplier Capex budget ({supplier_capex})"
                    }
            
            # Validate OPEX
            if opex_total > 0:
                # Branch - Check for zero/null budget first
                branch_opex = flt(hierarchy_data['branch'].get('custom_opex_budget'))
                if branch_opex <= 0:
                    return {
                        "status": "error",
                        "message": f"Cannot create Purchase Order: Branch OPEX budget is not allocated or is zero (Current: {branch_opex})"
                    }
                if opex_total > branch_opex:
                    return {
                        "status": "error",
                        "message": f"Total Opex amount ({opex_total}) exceeds Branch Opex budget ({branch_opex})"
                    }
                
                # Supplier - Check for zero/null budget first
                supplier_opex = flt(hierarchy_data['supplier'].get('custom_opex_budget'))
                if supplier_opex <= 0:
                    return {
                        "status": "error",
                        "message": f"Cannot create Purchase Order: Supplier OPEX budget is not allocated or is zero (Current: {supplier_opex})"
                    }
                if opex_total > supplier_opex:
                    return {
                        "status": "error",
                        "message": f"Total Opex amount ({opex_total}) exceeds Supplier Opex budget ({supplier_opex})"
                    }
        
        # Sub-branch level PO (has sub-branch) - validate against sub-branch budgets
        else:
            if not hierarchy_data['sub_branch']:
                return {
                    "status": "error",
                    "message": f"Could not fetch sub-branch details for '{doc.get('custom_sub_branch')}'. Please check if the sub-branch exists and is properly configured."
                }
            
            # Validate CAPEX
            if capex_total > 0:
                # Sub-Branch - Check for zero/null budget first
                sub_branch_capex = flt(hierarchy_data['sub_branch'].get('capex_budget'))
                if sub_branch_capex <= 0:
                    return {
                        "status": "error",
                        "message": f"Cannot create Purchase Order: Sub-branch CAPEX budget is not allocated or is zero (Current: {sub_branch_capex})"
                    }
                if capex_total > sub_branch_capex:
                    return {
                        "status": "error",
                        "message": f"Total Capex amount ({capex_total}) exceeds Sub-branch Capex budget ({sub_branch_capex})"
                    }
                
                # Supplier - Check for zero/null budget first
                supplier_capex = flt(hierarchy_data['supplier'].get('custom_capex_budget'))
                if supplier_capex <= 0:
                    return {
                        "status": "error",
                        "message": f"Cannot create Purchase Order: Supplier CAPEX budget is not allocated or is zero (Current: {supplier_capex})"
                    }
                if capex_total > supplier_capex:
                    return {
                        "status": "error",
                        "message": f"Total Capex amount ({capex_total}) exceeds Supplier Capex budget ({supplier_capex})"
                    }
            
            # Validate OPEX
            if opex_total > 0:
                # Sub-branch - Check for zero/null budget first
                sub_branch_opex = flt(hierarchy_data['sub_branch'].get('opex_budget'))
                if sub_branch_opex <= 0:
                    return {
                        "status": "error",
                        "message": f"Cannot create Purchase Order: Sub-branch OPEX budget is not allocated or is zero (Current: {sub_branch_opex})"
                    }
                if opex_total > sub_branch_opex:
                    return {
                        "status": "error",
                        "message": f"Total Opex amount ({opex_total}) exceeds Sub-branch Opex budget ({sub_branch_opex})"
                    }
                
                # Supplier - Check for zero/null budget first
                supplier_opex = flt(hierarchy_data['supplier'].get('custom_opex_budget'))
                if supplier_opex <= 0:
                    return {
                        "status": "error",
                        "message": f"Cannot create Purchase Order: Supplier OPEX budget is not allocated or is zero (Current: {supplier_opex})"
                    }
                if opex_total > supplier_opex:
                    return {
                        "status": "error",
                        "message": f"Total Opex amount ({opex_total}) exceeds Supplier Opex budget ({supplier_opex})"
                    }
        
        return {"status": "success"}
    
    except Exception as e:
        frappe.log_error(f"Error validating budgets: {str(e)}", "Budget Validation Error")
        return {
            "status": "error", 
            "message": f"Budget validation error: {str(e)}"
        }

def validate_incremental_budgets(doc, capex_total, opex_total):
    """Validate budget changes for existing Purchase Orders - only allow increases if sufficient budget remains"""
    try:
        if not doc.get('items') or len(doc.get('items')) == 0:
            return {"status": "success"}
        
        # Check if document has a valid name (required for incremental validation)
        doc_name = doc.get('name')
        if not doc_name or doc_name.startswith('new-'):
            # This is actually a new document, use full budget validation instead
            return validate_budgets(doc, capex_total, opex_total)
        
        # Get the original PO totals from database using direct DB query (more reliable)
        try:
            # Use database query instead of get_doc to avoid transaction issues
            existing_po = frappe.db.get_value("Purchase Order", doc_name, "name")
            if not existing_po:
                # Document doesn't exist in database yet, treat as new document
                return validate_budgets(doc, capex_total, opex_total)
                
            original_doc = frappe.get_doc("Purchase Order", doc_name)
            original_capex, original_opex = calculate_capex_opex_totals(original_doc.as_dict())
        except Exception as e:
            # Any error fetching original document, treat as new document
            frappe.log_error(f"Could not fetch original PO {doc_name}: {str(e)}", "Incremental Validation Fallback")
            return validate_budgets(doc, capex_total, opex_total)
        
        # Calculate the change (delta)
        capex_change = capex_total - original_capex
        opex_change = opex_total - original_opex
        
        # If both changes are negative or zero, allow (decreasing or same)
        if capex_change <= 0 and opex_change <= 0:
            return {"status": "success", "message": "Budget decrease/same - allowed"}
        
        # If there's an increase, check if sufficient budget remains
        hierarchy_data = get_hierarchy_data(
            branch=doc.get('custom_branch'),
            sub_branch=doc.get('custom_sub_branch')
        )
        
        
        if not hierarchy_data['supplier']:
            return {
                "status": "error",
                "message": "Could not fetch supplier details for budget validation"
            }
        
        # Check CAPEX increase
        if capex_change > 0:
            # Determine validation level based on PO structure (not user role)
            has_sub_branch = bool(doc.get('custom_sub_branch'))
            
            if not has_sub_branch:
                # Branch-level PO (no sub-branch) - validate against branch budgets
                if not hierarchy_data.get('branch'):
                    return {
                        "status": "error",
                        "message": "Could not fetch branch details for budget validation"
                    }
                
                branch_capex = flt(hierarchy_data['branch'].get('custom_capex_budget', 0))
                supplier_capex = flt(hierarchy_data['supplier'].get('custom_capex_budget', 0))
                
                if capex_change > branch_capex:
                    return {
                        "status": "error",
                        "message": f"Cannot increase CAPEX by ₹{capex_change}: Insufficient branch CAPEX budget (Available: ₹{branch_capex})"
                    }
                if capex_change > supplier_capex:
                    return {
                        "status": "error",
                        "message": f"Cannot increase CAPEX by ₹{capex_change}: Insufficient supplier CAPEX budget (Available: ₹{supplier_capex})"
                    }
            else:
                # Sub-branch level PO (has sub-branch) - validate against sub-branch budgets
                if not hierarchy_data.get('sub_branch'):
                    return {
                        "status": "error",
                        "message": f"Could not fetch sub-branch details for '{doc.get('custom_sub_branch')}'. Please check if the sub-branch exists and is properly configured."
                    }
                
                sub_branch_capex = flt(hierarchy_data['sub_branch'].get('capex_budget', 0))
                supplier_capex = flt(hierarchy_data['supplier'].get('custom_capex_budget', 0))
                
                if capex_change > sub_branch_capex:
                    return {
                        "status": "error",
                        "message": f"Cannot increase CAPEX by ₹{capex_change}: Insufficient sub-branch CAPEX budget (Available: ₹{sub_branch_capex})"
                    }
                if capex_change > supplier_capex:
                    return {
                        "status": "error",
                        "message": f"Cannot increase CAPEX by ₹{capex_change}: Insufficient supplier CAPEX budget (Available: ₹{supplier_capex})"
                    }
        
        # Check OPEX increase
        if opex_change > 0:
            # Determine validation level based on PO structure (not user role)
            has_sub_branch = bool(doc.get('custom_sub_branch'))
            
            if not has_sub_branch:
                # Branch-level PO (no sub-branch) - validate against branch budgets
                if not hierarchy_data.get('branch'):
                    return {
                        "status": "error",
                        "message": "Could not fetch branch details for budget validation"
                    }
                
                branch_opex = flt(hierarchy_data['branch'].get('custom_opex_budget', 0))
                supplier_opex = flt(hierarchy_data['supplier'].get('custom_opex_budget', 0))
                
                if opex_change > branch_opex:
                    return {
                        "status": "error",
                        "message": f"Cannot increase OPEX by ₹{opex_change}: Insufficient branch OPEX budget (Available: ₹{branch_opex})"
                    }
                if opex_change > supplier_opex:
                    return {
                        "status": "error",
                        "message": f"Cannot increase OPEX by ₹{opex_change}: Insufficient supplier OPEX budget (Available: ₹{supplier_opex})"
                    }
            else:
                # Sub-branch level PO (has sub-branch) - validate against sub-branch budgets
                if not hierarchy_data.get('sub_branch'):
                    return {
                        "status": "error",
                        "message": f"Could not fetch sub-branch details for '{doc.get('custom_sub_branch')}'. Please check if the sub-branch exists and is properly configured."
                    }
                
                sub_branch_opex = flt(hierarchy_data['sub_branch'].get('opex_budget', 0))
                supplier_opex = flt(hierarchy_data['supplier'].get('custom_opex_budget', 0))
                
                if opex_change > sub_branch_opex:
                    return {
                        "status": "error",
                        "message": f"Cannot increase OPEX by ₹{opex_change}: Insufficient sub-branch OPEX budget (Available: ₹{sub_branch_opex})"
                    }
                if opex_change > supplier_opex:
                    return {
                        "status": "error",
                        "message": f"Cannot increase OPEX by ₹{opex_change}: Insufficient supplier OPEX budget (Available: ₹{supplier_opex})"
                    }
        
        return {"status": "success", "message": "Budget increase allowed - sufficient budget available"}
    
    except Exception as e:
        frappe.log_error(f"Error validating incremental budgets: {str(e)}", "Incremental Budget Validation Error")
        return {
            "status": "error", 
            "message": f"Incremental budget validation error: {str(e)}"
        }

@frappe.whitelist()
def update_budgets(doc_name, capex_total=0, opex_total=0):
    """Update budgets after Purchase Order is submitted"""
    try:
        capex_total = flt(capex_total)
        opex_total = flt(opex_total)
        
        if capex_total == 0 and opex_total == 0:
            return {"status": "success", "message": "No budget updates needed"}
        
        doc = frappe.get_doc("Purchase Order", doc_name)
        
        # Get hierarchy data
        hierarchy_data = get_hierarchy_data(
            branch=doc.custom_branch,
            sub_branch=doc.custom_sub_branch
        )
        
        if not hierarchy_data['supplier']:
            return {
                "status": "error",
                "message": "Could not fetch supplier details"
            }
        
        updates = []
        
        # Determine update level based on PO structure (not user role)
        has_sub_branch = bool(doc.custom_sub_branch)
        
        # For branch-level POs (no sub-branch)
        if not has_sub_branch:
            if not hierarchy_data['branch']:
                return {
                    "status": "error",
                    "message": "Could not fetch branch details"
                }
            
            # Update CAPEX Budget for Branch
            if capex_total > 0 and hierarchy_data['branch'].get('custom_capex_budget'):
                branch_capex = flt(hierarchy_data['branch'].get('custom_capex_budget'))
                if branch_capex > 0:
                    new_branch_capex = branch_capex - capex_total
                    frappe.db.set_value('Branch', doc.custom_branch, 'custom_capex_budget', new_branch_capex)
                    updates.append(f"Branch Capex budget updated to {new_branch_capex}")
            
            # Update CAPEX Budget for Supplier
            if capex_total > 0 and hierarchy_data['branch'].get('custom_supplier'):
                supplier_capex = flt(hierarchy_data['supplier'].get('custom_capex_budget'))
                if supplier_capex > 0:
                    new_supplier_capex = supplier_capex - capex_total
                    frappe.db.set_value('Supplier', hierarchy_data['branch'].get('custom_supplier'), 'custom_capex_budget', new_supplier_capex)
                    updates.append(f"Supplier Capex budget updated to {new_supplier_capex}")
            
            # Update OPEX Budget for Branch
            if opex_total > 0 and hierarchy_data['branch'].get('custom_opex_budget'):
                branch_opex = flt(hierarchy_data['branch'].get('custom_opex_budget'))
                if branch_opex > 0:
                    new_branch_opex = branch_opex - opex_total
                    frappe.db.set_value('Branch', doc.custom_branch, 'custom_opex_budget', new_branch_opex)
                    updates.append(f"Branch Opex budget updated to {new_branch_opex}")
            
            # Update OPEX Budget for Supplier
            if opex_total > 0 and hierarchy_data['branch'].get('custom_supplier'):
                supplier_opex = flt(hierarchy_data['supplier'].get('custom_opex_budget'))
                if supplier_opex > 0:
                    new_supplier_opex = supplier_opex - opex_total
                    frappe.db.set_value('Supplier', hierarchy_data['branch'].get('custom_supplier'), 'custom_opex_budget', new_supplier_opex)
                    updates.append(f"Supplier Opex budget updated to {new_supplier_opex}")
        
        # For sub-branch level POs (has sub-branch)
        else:
            if not hierarchy_data['sub_branch']:
                return {
                    "status": "error",
                    "message": f"Could not fetch sub-branch details for '{doc.custom_sub_branch}'. Please check if the sub-branch exists and is properly configured."
                }
            
            # Update CAPEX Budget for Sub-Branch
            if capex_total > 0 and hierarchy_data['sub_branch'].get('capex_budget'):
                sub_branch_capex = flt(hierarchy_data['sub_branch'].get('capex_budget'))
                if sub_branch_capex > 0:
                    new_sub_branch_capex = sub_branch_capex - capex_total
                    frappe.db.set_value('Sub Branch', doc.custom_sub_branch, 'capex_budget', new_sub_branch_capex)
                    updates.append(f"Sub Branch Capex budget updated to {new_sub_branch_capex}")
            
            # Update CAPEX Budget for Supplier
            if capex_total > 0 and hierarchy_data['branch'] and hierarchy_data['branch'].get('custom_supplier'):
                supplier_capex = flt(hierarchy_data['supplier'].get('custom_capex_budget'))
                if supplier_capex > 0:
                    new_supplier_capex = supplier_capex - capex_total
                    frappe.db.set_value('Supplier', hierarchy_data['branch'].get('custom_supplier'), 'custom_capex_budget', new_supplier_capex)
                    updates.append(f"Supplier Capex budget updated to {new_supplier_capex}")
            
            # Update OPEX Budget for Sub-Branch
            if opex_total > 0 and hierarchy_data['sub_branch'].get('opex_budget'):
                sub_branch_opex = flt(hierarchy_data['sub_branch'].get('opex_budget'))
                if sub_branch_opex > 0:
                    new_sub_branch_opex = sub_branch_opex - opex_total
                    frappe.db.set_value('Sub Branch', doc.custom_sub_branch, 'opex_budget', new_sub_branch_opex)
                    updates.append(f"Sub Branch Opex budget updated to {new_sub_branch_opex}")
            
            # Update OPEX Budget for Supplier
            if opex_total > 0 and hierarchy_data['branch'] and hierarchy_data['branch'].get('custom_supplier'):
                supplier_opex = flt(hierarchy_data['supplier'].get('custom_opex_budget'))
                if supplier_opex > 0:
                    new_supplier_opex = supplier_opex - opex_total
                    frappe.db.set_value('Supplier', hierarchy_data['branch'].get('custom_supplier'), 'custom_opex_budget', new_supplier_opex)
                    updates.append(f"Supplier Opex budget updated to {new_supplier_opex}")
        
        frappe.db.commit()
        
        return {
            "status": "success",
            "message": "Budgets updated successfully",
            "updates": updates
        }
    
    except Exception as e:
        frappe.log_error(f"Error updating budgets: {str(e)}", "Budget Update Error")
        return {
            "status": "error",
            "message": f"Error updating budgets: {str(e)}"
        }
    
@frappe.whitelist()
def update_budgets_for_po(doc_name, is_new=False):
    """
    Update budgets for Purchase Orders (both new and existing).
    
    For new POs: Deduct the full amount and initialize tracking fields
    For existing POs: Calculate the delta from previous values and apply accordingly
    
    Always fetches the current budget values before making changes to account for
    any manual budget adjustments that may have been made outside this process.
    Records all budget transactions.
    """
    try:
        # Get the current Purchase Order
        current_po = frappe.get_doc("Purchase Order", doc_name)
        
        # Calculate current CAPEX/OPEX totals
        current_capex_total, current_opex_total = calculate_capex_opex_totals(current_po)
        
        # Determine delta values based on whether this is new or existing
        if is_new == "true" or is_new is True:
            # For new POs, use the full amounts
            capex_delta = current_capex_total
            opex_delta = current_opex_total
        else:
            # For existing POs, calculate delta from previous values
            prev_capex_total = flt(current_po.get('custom_last_capex_total', 0))
            prev_opex_total = flt(current_po.get('custom_last_opex_total', 0))
            
            capex_delta = current_capex_total - prev_capex_total
            opex_delta = current_opex_total - prev_opex_total
        
        # Update the tracking fields regardless of new or existing
        frappe.db.set_value('Purchase Order', doc_name, {
            'custom_last_capex_total': current_capex_total,
            'custom_last_opex_total': current_opex_total
        })
        
        # Only proceed if there are changes to apply
        if capex_delta == 0 and opex_delta == 0:
            return {
                "status": "success",
                "message": "No budget updates needed - no change in CAPEX/OPEX amounts"
            }
        
        # Get hierarchy data
        hierarchy_data = get_hierarchy_data(
            branch=current_po.custom_branch,
            sub_branch=current_po.custom_sub_branch
        )
        
        if not hierarchy_data['supplier']:
            return {
                "status": "error",
                "message": "Could not fetch supplier details"
            }
        
        updates = []
        transactions = []
        
        # Determine update level based on PO structure (not user role)
        has_sub_branch = bool(current_po.custom_sub_branch)
        
        # For branch-level POs (no sub-branch)
        if not has_sub_branch:
            if not hierarchy_data['branch']:
                return {
                    "status": "error",
                    "message": "Could not fetch branch details"
                }
            
            # Update CAPEX Budget for Branch
            if capex_delta != 0:
                # Record transaction for branch CAPEX
                transaction_id = record_budget_transaction(
                    entity_type="Branch",
                    entity_name=current_po.custom_branch,
                    budget_type="CAPEX",
                    amount=-capex_delta,  # Negative for deduction
                    reference_doctype="Purchase Order",
                    reference_name=doc_name,
                    description=f"CAPEX budget adjustment of {abs(capex_delta)} from Purchase Order {doc_name}"
                )
                
                if transaction_id:
                    transactions.append(transaction_id)
                    
                    # Get the updated value (after transaction)
                    current_branch_capex = frappe.db.get_value('Branch', current_po.custom_branch, 'custom_capex_budget') or 0
                    
                    if capex_delta > 0:
                        action = f"decreased by {abs(capex_delta)}"
                    else:
                        action = f"increased by {abs(capex_delta)}"
                        
                    updates.append(f"Branch Capex budget {action} to {current_branch_capex}")
            
            # Update CAPEX Budget for Supplier
            if capex_delta != 0 and hierarchy_data['branch'].get('custom_supplier'):
                supplier = hierarchy_data['branch'].get('custom_supplier')
                
                # Record transaction for supplier CAPEX
                transaction_id = record_budget_transaction(
                    entity_type="Supplier",
                    entity_name=supplier,
                    budget_type="CAPEX",
                    amount=-capex_delta,  # Negative for deduction
                    reference_doctype="Purchase Order",
                    reference_name=doc_name,
                    description=f"CAPEX budget adjustment of {abs(capex_delta)} from Purchase Order {doc_name}"
                )
                
                if transaction_id:
                    transactions.append(transaction_id)
                    
                    # Get the updated value (after transaction)
                    current_supplier_capex = frappe.db.get_value('Supplier', supplier, 'custom_capex_budget') or 0
                    
                    if capex_delta > 0:
                        action = f"decreased by {abs(capex_delta)}"
                    else:
                        action = f"increased by {abs(capex_delta)}"
                        
                    updates.append(f"Supplier Capex budget {action} to {current_supplier_capex}")
            
            # Update OPEX Budget for Branch
            if opex_delta != 0:
                # Record transaction for branch OPEX
                transaction_id = record_budget_transaction(
                    entity_type="Branch",
                    entity_name=current_po.custom_branch,
                    budget_type="OPEX",
                    amount=-opex_delta,  # Negative for deduction
                    reference_doctype="Purchase Order",
                    reference_name=doc_name,
                    description=f"OPEX budget adjustment of {abs(opex_delta)} from Purchase Order {doc_name}"
                )
                
                if transaction_id:
                    transactions.append(transaction_id)
                    
                    # Get the updated value (after transaction)
                    current_branch_opex = frappe.db.get_value('Branch', current_po.custom_branch, 'custom_opex_budget') or 0
                    
                    if opex_delta > 0:
                        action = f"decreased by {abs(opex_delta)}"
                    else:
                        action = f"increased by {abs(opex_delta)}"
                        
                    updates.append(f"Branch Opex budget {action} to {current_branch_opex}")
            
            # Update OPEX Budget for Supplier
            if opex_delta != 0 and hierarchy_data['branch'].get('custom_supplier'):
                supplier = hierarchy_data['branch'].get('custom_supplier')
                
                # Record transaction for supplier OPEX
                transaction_id = record_budget_transaction(
                    entity_type="Supplier",
                    entity_name=supplier,
                    budget_type="OPEX",
                    amount=-opex_delta,  # Negative for deduction
                    reference_doctype="Purchase Order",
                    reference_name=doc_name,
                    description=f"OPEX budget adjustment of {abs(opex_delta)} from Purchase Order {doc_name}"
                )
                
                if transaction_id:
                    transactions.append(transaction_id)
                    
                    # Get the updated value (after transaction)
                    current_supplier_opex = frappe.db.get_value('Supplier', supplier, 'custom_opex_budget') or 0
                    
                    if opex_delta > 0:
                        action = f"decreased by {abs(opex_delta)}"
                    else:
                        action = f"increased by {abs(opex_delta)}"
                        
                    updates.append(f"Supplier Opex budget {action} to {current_supplier_opex}")
        
        # For sub-branch level POs (has sub-branch)
        else:
            if not hierarchy_data['sub_branch']:
                return {
                    "status": "error",
                    "message": f"Could not fetch sub-branch details for '{current_po.custom_sub_branch}'. Please check if the sub-branch exists and is properly configured."
                }
            
            # Update CAPEX Budget for Sub-Branch
            if capex_delta != 0:
                # Record transaction for sub-branch CAPEX
                transaction_id = record_budget_transaction(
                    entity_type="Sub Branch",
                    entity_name=current_po.custom_sub_branch,
                    budget_type="CAPEX",
                    amount=-capex_delta,  # Negative for deduction
                    reference_doctype="Purchase Order",
                    reference_name=doc_name,
                    description=f"CAPEX budget adjustment of {abs(capex_delta)} from Purchase Order {doc_name}"
                )
                
                if transaction_id:
                    transactions.append(transaction_id)
                    
                    # Get the updated value (after transaction)
                    current_sub_branch_capex = frappe.db.get_value('Sub Branch', current_po.custom_sub_branch, 'capex_budget') or 0
                    
                    if capex_delta > 0:
                        action = f"decreased by {abs(capex_delta)}"
                    else:
                        action = f"increased by {abs(capex_delta)}"
                        
                    updates.append(f"Sub Branch Capex budget {action} to {current_sub_branch_capex}")
            
            # Update CAPEX Budget for Supplier
            if capex_delta != 0 and hierarchy_data['branch'] and hierarchy_data['branch'].get('custom_supplier'):
                supplier = hierarchy_data['branch'].get('custom_supplier')
                
                # Record transaction for supplier CAPEX
                transaction_id = record_budget_transaction(
                    entity_type="Supplier",
                    entity_name=supplier,
                    budget_type="CAPEX",
                    amount=-capex_delta,  # Negative for deduction
                    reference_doctype="Purchase Order",
                    reference_name=doc_name,
                    description=f"CAPEX budget adjustment of {abs(capex_delta)} from Purchase Order {doc_name}"
                )
                
                if transaction_id:
                    transactions.append(transaction_id)
                    
                    # Get the updated value (after transaction)
                    current_supplier_capex = frappe.db.get_value('Supplier', supplier, 'custom_capex_budget') or 0
                    
                    if capex_delta > 0:
                        action = f"decreased by {abs(capex_delta)}"
                    else:
                        action = f"increased by {abs(capex_delta)}"
                        
                    updates.append(f"Supplier Capex budget {action} to {current_supplier_capex}")
            
            # Update OPEX Budget for Sub-Branch
            if opex_delta != 0:
                # Record transaction for sub-branch OPEX
                transaction_id = record_budget_transaction(
                    entity_type="Sub Branch",
                    entity_name=current_po.custom_sub_branch,
                    budget_type="OPEX",
                    amount=-opex_delta,  # Negative for deduction
                    reference_doctype="Purchase Order",
                    reference_name=doc_name,
                    description=f"OPEX budget adjustment of {abs(opex_delta)} from Purchase Order {doc_name}"
                )
                
                if transaction_id:
                    transactions.append(transaction_id)
                    
                    # Get the updated value (after transaction)
                    current_sub_branch_opex = frappe.db.get_value('Sub Branch', current_po.custom_sub_branch, 'opex_budget') or 0
                    
                    if opex_delta > 0:
                        action = f"decreased by {abs(opex_delta)}"
                    else:
                        action = f"increased by {abs(opex_delta)}"
                        
                    updates.append(f"Sub Branch Opex budget {action} to {current_sub_branch_opex}")
            
            # Update OPEX Budget for Supplier
            if opex_delta != 0 and hierarchy_data['branch'] and hierarchy_data['branch'].get('custom_supplier'):
                supplier = hierarchy_data['branch'].get('custom_supplier')
                
                # Record transaction for supplier OPEX
                transaction_id = record_budget_transaction(
                    entity_type="Supplier",
                    entity_name=supplier,
                    budget_type="OPEX",
                    amount=-opex_delta,  # Negative for deduction
                    reference_doctype="Purchase Order",
                    reference_name=doc_name,
                    description=f"OPEX budget adjustment of {abs(opex_delta)} from Purchase Order {doc_name}"
                )
                
                if transaction_id:
                    transactions.append(transaction_id)
                    
                    # Get the updated value (after transaction)
                    current_supplier_opex = frappe.db.get_value('Supplier', supplier, 'custom_opex_budget') or 0
                    
                    if opex_delta > 0:
                        action = f"decreased by {abs(opex_delta)}"
                    else:
                        action = f"increased by {abs(opex_delta)}"
                        
                    updates.append(f"Supplier Opex budget {action} to {current_supplier_opex}")
        
        # Store transaction IDs in Purchase Order for reference
        if transactions:
            transaction_ids = ','.join(transactions)
            # Add a custom field in Purchase Order to store budget transaction IDs
            if not hasattr(current_po, 'custom_budget_transactions'):
                # If field doesn't exist yet, you might need to create it
                frappe.db.set_value('Purchase Order', doc_name, 'custom_budget_transactions', transaction_ids)
            else:
                # Append to existing transactions
                existing_ids = current_po.get('custom_budget_transactions', '')
                if existing_ids:
                    transaction_ids = f"{existing_ids},{transaction_ids}"
                frappe.db.set_value('Purchase Order', doc_name, 'custom_budget_transactions', transaction_ids)
        
        frappe.db.commit()
        
        return {
            "status": "success",
            "message": "Budgets updated successfully",
            "updates": updates,
            "transactions": transactions
        }
    
    except Exception as e:
        frappe.log_error(f"Error updating budgets for PO: {str(e)}", 
                       "Budget Update Error")
        return {
            "status": "error",
            "message": f"Error updating budgets: {str(e)}"
        }
    

@frappe.whitelist()
def get_current_budgets(branch=None, sub_branch=None):
    """Get current budget values for branch and sub-branch"""
    result = {
        'branch': None,
        'sub_branch': None,
        'is_branch_user': is_branch_level_user()
    }
    
    if branch:
        branch_data = frappe.get_value('Branch', branch,
            ['custom_supplier', 'custom_capex_budget', 'custom_opex_budget'],
            as_dict=1
        )
        result['branch'] = branch_data
    
    if sub_branch:
        sub_branch_data = frappe.get_value('Sub Branch', sub_branch,
            ['branch', 'capex_budget', 'opex_budget'],
            as_dict=1
        )
        result['sub_branch'] = sub_branch_data
    
    return result


def record_budget_transaction(entity_type, entity_name, budget_type, amount, reference_doctype=None, reference_name=None, description=None):
    """
    Create a budget transaction record
    """
    try:
        # Determine transaction type
        transaction_type = "Credit" if amount >= 0 else "Debit"
        abs_amount = abs(amount)
        
        # Get the appropriate field name based on entity type and budget type
        if entity_type == "Sub Branch":
            field_name = "capex_budget" if budget_type == "CAPEX" else "opex_budget"
        else:  # Branch or Supplier
            field_name = f"custom_{budget_type.lower()}_budget"
            
        # Get current budget value
        current_value = frappe.db.get_value(entity_type, entity_name, field_name) or 0
        current_value = flt(current_value)
        
        # Calculate new budget value
        if transaction_type == "Credit":
            new_value = current_value + abs_amount
        else:  # Debit
            new_value = current_value - abs_amount
        
        # Directly update the budget value
        frappe.db.set_value(entity_type, entity_name, field_name, new_value)
            
        # Generate a unique transaction ID
        transaction_id = f"BT-{uuid.uuid4().hex[:8].upper()}"
        
        # Create the transaction record
        transaction = frappe.new_doc("Budget Transaction")
        transaction.transaction_id = transaction_id
        transaction.transaction_date = now()
        transaction.created_by = frappe.session.user
        transaction.entity_type = entity_type
        transaction.entity_name = entity_name
        transaction.budget_type = budget_type
        transaction.amount = abs_amount  # Always store as positive
        transaction.transaction_type = transaction_type
        transaction.previous_budget_value = current_value
        transaction.new_budget_value = new_value
        
        # Set reference document if provided
        if reference_doctype and reference_name:
            transaction.reference_doctype = reference_doctype
            transaction.reference_name = reference_name
            
        # Set description
        if description:
            transaction.description = description
        else:
            transaction.description = f"{transaction_type} of {abs_amount} in {budget_type} budget for {entity_type} {entity_name}"
            
        # Save the transaction
        transaction.insert()
        
        # Try to submit with explicit error catching
        try:
            transaction.submit()
            frappe.db.commit()
        except Exception as submit_error:
            frappe.log_error(
                message=f"Failed to submit budget transaction {transaction_id}: {str(submit_error)}", 
                title="Budget Transaction Submit Error"
            )
            # Even if submission fails, we've still updated the budget value
        
        return transaction_id
    
    except Exception as e:
        frappe.log_error(
            message=f"Error recording budget transaction: {str(e)}", 
            title="Budget Transaction Error"
        )
        return None

@frappe.whitelist()
def get_sub_branch_requisition_approver(sub_branch):
    """Helper function to find sub-branch requisition approver information"""
    try:
        if not sub_branch:
            return None
            
        # Search for Employee with Requisition Approver role in custom_roles
        # and matching sub-branch
        employees = frappe.get_all(
            "Employee",
            filters={
                "custom_sub_branch": sub_branch,
                "custom_roles": ["like", "%Requisition Approver%"]
            },
            fields=["name", "employee_name", "custom_user_email"]
        )
        
        # If no employee found with exact match, try searching employees with access to this sub-branch
        if not employees:
            # Try to find employees with this sub-branch in their custom_sub_branch_list
            frappe.log_error(f"No direct requisition approver found for {sub_branch}, searching for employees with access", "Requisition Approver Debug")
            
            # Get all employees with Requisition Approver role
            potential_approvers = frappe.get_all(
                "Employee",
                filters={
                    "custom_roles": ["like", "%Requisition Approver%"]
                },
                fields=["name", "employee_name", "custom_user_email"]
            )
            
            # For each potential approver, check if they have access to this sub-branch
            for approver in potential_approvers:
                # Get the employee's sub branch list
                sub_branches = frappe.get_all(
                    "Sub Branch Table",
                    filters={"parent": approver.name},
                    fields=["sub_branch"],
                    pluck="sub_branch"
                )
                
                # If this sub-branch is in their list, use this approver
                if sub_branch in sub_branches:
                    employees = [approver]
                    break
        
        if not employees:
            frappe.log_error(f"No requisition approver found for sub-branch: {sub_branch}", "Requisition Approver Debug")
            return None
            
        # Take the first matching employee
        approver = employees[0]
        
        # Format approver information
        return f"{approver.employee_name}:{approver.custom_user_email}"
            
    except Exception as e:
        frappe.log_error(f"Error finding sub-branch requisition approver: {str(e)}", 
                        "Get Sub-Branch Requisition Approver Error")
        return None

@frappe.whitelist()
def set_requisition_approver_for_purchase_order(purchase_order_name):
    try:
        # Get the Purchase Order document
        po_doc = frappe.get_doc("Purchase Order", purchase_order_name)
        
        # Check if supplier has "3 way" approval flow
        if po_doc.supplier:
            approval_flow = frappe.db.get_value("Supplier", po_doc.supplier, "custom_approval_flow")
            if approval_flow != "3 way":
                # For non-3-way approval, don't set requisition approver
                return {
                    "status": "info",
                    "message": _("Requisition Approver only required for 3-way approval flow")
                }
        
        # Get the sub-branch from Purchase Order
        sub_branch = po_doc.custom_sub_branch
        
        if not sub_branch:
            frappe.throw(_("Purchase Order does not have a sub-branch assigned"), 
                        title=_("Missing Sub-Branch"))
        
        # Get the requisition approver
        approver_info = get_sub_branch_requisition_approver(sub_branch)
        
        if not approver_info:
            frappe.msgprint(
                _("No Requisition Approver found for sub-branch {0}").format(sub_branch),
                title=_("Approver Not Found")
            )
            return {
                "status": "warning",
                "message": _("No Requisition Approver found")
            }
        
        # Update the Purchase Order with approver name and email
        frappe.db.set_value("Purchase Order", purchase_order_name, 
                          "custom_requisition_approver_name_and_email", approver_info)
        
        # Extract and set the email in the dedicated email field
        approver_parts = approver_info.split(':', 1)
        if len(approver_parts) > 1:
            req_approver_email = approver_parts[1]
            frappe.db.set_value("Purchase Order", purchase_order_name, 
                              "custom_requisition_approver_email", req_approver_email)
        
        frappe.db.commit()
        
        return {
            "status": "success",
            "message": _("Requisition Approver set successfully"),
            "approver": approver_info
        }
            
    except Exception as e:
        frappe.log_error(f"Error setting requisition approver: {str(e)}", 
                        "Set Requisition Approver Error")
        return {
            "status": "error",
            "message": str(e)
        }

@frappe.whitelist()
def update_submitted_po_items(items_data, deleted_items=None):
    """
    Update submitted Purchase Order Items - Simplified version
    Only handles: quantity, unit rate, and item deletion
    Uses direct database updates to bypass ERPNext restrictions
    """
    import json
    
    # Parse items_data if it's a string
    if isinstance(items_data, str):
        items_data = json.loads(items_data)
    
    if isinstance(deleted_items, str):
        deleted_items = json.loads(deleted_items)
    
    if not deleted_items:
        deleted_items = []
    
    updated_items = []
    deleted_item_names = []
    updated_po_names = []
    
    try:
        # Handle item deletions first
        for item_name in deleted_items:
            # Get parent PO name before deletion
            po_name = frappe.db.get_value('Purchase Order Item', item_name, 'parent')
            
            # Check if user has permission
            if not frappe.has_permission('Purchase Order', 'write', po_name):
                frappe.throw(_('No permission to update Purchase Order {0}').format(po_name))
            
            # Direct database delete - bypasses all ERPNext restrictions
            frappe.db.sql("DELETE FROM `tabPurchase Order Item` WHERE name = %s", (item_name,))
            
            deleted_item_names.append(item_name)
            
            if po_name not in updated_po_names:
                updated_po_names.append(po_name)
        
        # Handle item updates (quantity and rate only)
        for item_data in items_data:
            item_name = item_data.get('name')
            changes = item_data.get('changes', {})
            
            if not item_name or not changes:
                continue
            
            # Get parent PO name
            po_name = frappe.db.get_value('Purchase Order Item', item_name, 'parent')
            
            # Check if user has permission
            if not frappe.has_permission('Purchase Order', 'write', po_name):
                frappe.throw(_('No permission to update Purchase Order {0}').format(po_name))
            
            # Only allow quantity and rate updates
            allowed_fields = ['qty', 'rate']
            
            # Update each changed field using direct database update
            for field, value in changes.items():
                if field in allowed_fields:
                    # Direct database update - bypasses all ERPNext restrictions
                    frappe.db.sql(
                        "UPDATE `tabPurchase Order Item` SET {0} = %s WHERE name = %s".format(field),
                        (value, item_name)
                    )
                    
                    # Calculate and update amount (qty * rate) and GSTN values
                    if field in ['qty', 'rate']:
                        # Get current qty, rate, and tax template
                        current_data = frappe.db.get_value('Purchase Order Item', item_name, ['qty', 'rate', 'item_tax_template'], as_dict=True)
                        if current_data:
                            new_amount = float(current_data.qty or 0) * float(current_data.rate or 0)
                            
                            # Calculate GSTN value based on tax template
                            gstn_value = 0.0
                            if current_data.item_tax_template:
                                # Get tax rate from tax template
                                # Try different field names for tax rate
                                tax_rate = None
                                possible_fields = ['tax_rate', 'rate', 'tax_percentage', 'gst_rate']
                                
                                for field in possible_fields:
                                    try:
                                        tax_rate = frappe.db.get_value('Item Tax Template', current_data.item_tax_template, field)
                                        if tax_rate:
                                            break
                                    except:
                                        continue
                                
                                if tax_rate:
                                    tax_rate_value = float(tax_rate) if tax_rate else 0
                                    gstn_value = new_amount * (tax_rate_value / 100)
                                else:
                                    # Default to 18% GST if no tax rate found
                                    gstn_value = new_amount * 0.18
                            
                            # Update amount, net_amount, base_amount, base_net_amount
                            frappe.db.sql(
                                """UPDATE `tabPurchase Order Item` 
                                   SET amount = %s, net_amount = %s, base_amount = %s, base_net_amount = %s
                                   WHERE name = %s""",
                                (new_amount, new_amount, new_amount, new_amount, item_name)
                            )
                            
                            # Try to update GSTN fields if they exist
                            try:
                                frappe.db.sql(
                                    """UPDATE `tabPurchase Order Item` 
                                       SET custom_gstn_value = %s, custom_grand_total = %s
                                       WHERE name = %s""",
                                    (gstn_value, new_amount + gstn_value, item_name)
                                )
                            except Exception as e:
                                # If custom fields don't exist, skip GSTN update
                                if "Unknown column" in str(e):
                                    frappe.log_error(f"GSTN custom fields not found in database: {e}", "GSTN Update Warning")
                                else:
                                    raise e
            
            updated_items.append(item_name)
            
            if po_name not in updated_po_names:
                updated_po_names.append(po_name)
        
        # Recalculate Purchase Order totals using direct database updates
        for po_name in updated_po_names:
            # Calculate totals from items
            totals = frappe.db.sql("""
                SELECT 
                    SUM(qty) as total_qty,
                    SUM(amount) as total,
                    SUM(net_amount) as net_total,
                    SUM(base_amount) as base_total,
                    SUM(base_net_amount) as base_net_total
                FROM `tabPurchase Order Item` 
                WHERE parent = %s
            """, (po_name,), as_dict=True)[0]
            
            # Try to get GSTN totals if custom fields exist
            total_gstn = 0
            try:
                gstn_totals = frappe.db.sql("""
                    SELECT SUM(custom_gstn_value) as total_gstn
                    FROM `tabPurchase Order Item` 
                    WHERE parent = %s
                """, (po_name,), as_dict=True)[0]
                total_gstn = gstn_totals.total_gstn or 0
            except Exception as e:
                if "Unknown column" in str(e):
                    frappe.log_error(f"GSTN custom fields not found in database: {e}", "GSTN Totals Warning")
                else:
                    raise e
            
            # Calculate grand total (net_total + total_gstn)
            grand_total = (totals.net_total or 0) + total_gstn
            base_grand_total = (totals.base_net_total or 0) + total_gstn
            
            # Update Purchase Order totals directly in database
            frappe.db.sql("""
                UPDATE `tabPurchase Order` 
                SET total_qty = %s, total = %s, net_total = %s, grand_total = %s,
                    base_total = %s, base_net_total = %s, base_grand_total = %s
                WHERE name = %s
            """, (
                totals.total_qty or 0,
                totals.total or 0,
                totals.net_total or 0,
                grand_total,
                totals.base_total or 0,
                totals.base_net_total or 0,
                base_grand_total,
                po_name
            ))
            
            # Try to update custom GSTN fields if they exist
            try:
                frappe.db.sql("""
                    UPDATE `tabPurchase Order` 
                    SET custom_total_gstn = %s, custom_grand_total = %s
                    WHERE name = %s
                """, (total_gstn, grand_total, po_name))
            except Exception as e:
                # If custom fields don't exist, skip GSTN update
                if "Unknown column" in str(e):
                    frappe.log_error(f"GSTN custom fields not found in Purchase Order: {e}", "PO GSTN Update Warning")
                else:
                    raise e
            
            # Add comment for audit trail
            comment_text = _('Items updated via Edit Submitted Items: {0} items updated, {1} items deleted by {2}').format(
                len(updated_items), len(deleted_item_names), frappe.session.user
            )
            frappe.db.sql("""
                INSERT INTO `tabComment` (name, comment_type, reference_doctype, reference_name, content, comment_by, creation, modified)
                VALUES (UUID(), 'Edit', 'Purchase Order', %s, %s, %s, NOW(), NOW())
            """, (po_name, comment_text, frappe.session.user))
        
        # Commit the transaction
        frappe.db.commit()
        
        # Return success response
        return {
            'status': 'success',
            'updated_items': updated_items,
            'deleted_items': deleted_item_names,
            'updated_po_count': len(updated_po_names),
            'message': _('Successfully updated {0} item(s) and deleted {1} item(s) in {2} Purchase Order(s)').format(
                len(updated_items), len(deleted_item_names), len(updated_po_names)
            )
        }
        
    except Exception as e:
        # Rollback on error
        frappe.db.rollback()
        
        # Log the error
        frappe.log_error(frappe.get_traceback(), 'Update Submitted PO Items Error')
        
        # Throw error to user
        frappe.throw(_('Error updating items: {0}').format(str(e)))

# Manually set the whitelist attribute to ensure the method is accessible
update_submitted_po_items.whitelisted = True