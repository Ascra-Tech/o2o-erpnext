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
                # Use direct SQL update to avoid concurrent modification issues
                update_fields = {}
                if billing_address:
                    update_fields["supplier_address"] = billing_address
                if shipping_address:
                    update_fields["shipping_address"] = shipping_address
                
                if update_fields:
                    try:
                        # Update directly using SQL to bypass document versioning
                        frappe.db.set_value("Purchase Order", purchase_order_name, update_fields)
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
    
    # For branch-level users, only get branch and supplier
    if result['is_branch_user']:
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
    
    # For sub-branch users, get the full hierarchy
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

@frappe.whitelist()
def validate_purchase_order(doc_name=None, doc_json=None):
    """Validate Purchase Order - comprehensive validation function"""
    try:
        if doc_name:
            doc = frappe.get_doc("Purchase Order", doc_name)
        elif doc_json:
            doc = json.loads(doc_json)
        else:
            return {
                "status": "error",
                "message": "Either doc_name or doc_json must be provided"
            }
        
        validation_results = {
            "status": "success",
            "validations": {},
            "capex_total": 0,
            "opex_total": 0
        }
        
        # Basic validations
        validation_results["validations"]["branch"] = validate_branch_mandatory(doc)
        validation_results["validations"]["sub_branch"] = validate_sub_branch_mandatory(doc)
        validation_results["validations"]["transaction_date"] = validate_transaction_date_mandatory(doc)
        validation_results["validations"]["hierarchy"] = validate_hierarchy(doc)
        
        # If we have items, do more validations
        if doc.get('items') and len(doc.get('items')) > 0:
            # Calculate CAPEX and OPEX totals
            capex_total, opex_total = calculate_capex_opex_totals(doc)
            validation_results["capex_total"] = capex_total
            validation_results["opex_total"] = opex_total
            
            # Validate order value and budget dates (always)
            validation_results["validations"]["order_value"] = validate_order_value(doc)
            validation_results["validations"]["budget_dates"] = validate_budget_dates(doc)
            
            # ONLY validate budgets for NEW documents (doc_json means new document)
            if doc_json:  # New document passed as JSON
                validation_results["validations"]["budgets"] = validate_budgets(doc, capex_total, opex_total)
            else:  # Existing document passed as doc_name - skip budget validation
                validation_results["validations"]["budgets"] = {"status": "success", "message": "Budget validation skipped for existing document"}
        
        # Check if any validation failed
        for key, result in validation_results["validations"].items():
            if result.get("status") == "error":
                validation_results["status"] = "error"
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

def validate_sub_branch_mandatory(doc):
    """Validate that sub-branch is provided (for non-branch users)"""
    # Skip for branch-level users
    if is_branch_level_user():
        return {"status": "success"}
    
    # For regular users, sub-branch is mandatory
    if not doc.get('custom_sub_branch'):
        return {
            "status": "error",
            "message": "Sub-branch is mandatory for Purchase Order"
        }
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
        
        # For branch-level users, just check if branch exists
        if hierarchy_data['is_branch_user']:
            if not hierarchy_data['branch']:
                return {
                    "status": "error",
                    "message": "Could not fetch branch details"
                }
            return {"status": "success"}
        
        # For sub-branch users, check the full hierarchy
        else:
            if not hierarchy_data['sub_branch']:
                return {
                    "status": "error",
                    "message": "Could not fetch sub-branch details"
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
        
        # For branch-level users
        if hierarchy_data['is_branch_user']:
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
                    "message": f"Total order value ({total}) must be at least {branch_min}"
                }
            
            # Branch maximum check
            branch_max = flt(hierarchy_data['branch'].get('custom_maximum_order_value'))
            if branch_max > 0 and total > branch_max:
                return {
                    "status": "error",
                    "message": f"Total order value ({total}) must not exceed {branch_max}"
                }
            
            # Supplier minimum check
            supplier_min = flt(hierarchy_data['supplier'].get('custom_minimum_order_value'))
            if supplier_min > 0 and total < supplier_min:
                return {
                    "status": "error",
                    "message": f"Total order value ({total}) must be at least {supplier_min}"
                }
            
            # Supplier maximum check
            supplier_max = flt(hierarchy_data['supplier'].get('custom_maximum_order_value'))
            if supplier_max > 0 and total > supplier_max:
                return {
                    "status": "error",
                    "message": f"Total order value ({total}) must not exceed {supplier_max}"
                }
        
        # For sub-branch users
        else:
            if not hierarchy_data['sub_branch']:
                return {
                    "status": "error",
                    "message": "Could not fetch sub-branch details"
                }
            
            # Sub-Branch minimum check
            sub_branch_min = flt(hierarchy_data['sub_branch'].get('minimum_order_value'))
            if sub_branch_min > 0 and total < sub_branch_min:
                return {
                    "status": "error",
                    "message": f"Total order value ({total}) must be at least {sub_branch_min}"
                }
            
            # Sub-Branch maximum check
            sub_branch_max = flt(hierarchy_data['sub_branch'].get('maximum_order_value'))
            if sub_branch_max > 0 and total > sub_branch_max:
                return {
                    "status": "error",
                    "message": f"Total order value ({total}) must not exceed {sub_branch_max}"
                }
            
            # Supplier minimum check
            supplier_min = flt(hierarchy_data['supplier'].get('custom_minimum_order_value'))
            if supplier_min > 0 and total < supplier_min:
                return {
                    "status": "error",
                    "message": f"Total order value ({total}) must be at least {supplier_min}"
                }
            
            # Supplier maximum check
            supplier_max = flt(hierarchy_data['supplier'].get('custom_maximum_order_value'))
            if supplier_max > 0 and total > supplier_max:
                return {
                    "status": "error",
                    "message": f"Total order value ({total}) must not exceed {supplier_max}"
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
        
        # For branch-level users
        if hierarchy_data['is_branch_user']:
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
        
        # For sub-branch users
        else:
            if not hierarchy_data['sub_branch']:
                return {
                    "status": "error",
                    "message": "Could not fetch sub-branch details"
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
            "message": f"Error validating budgets: {str(e)}"
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
        is_branch_user = is_branch_level_user()
        
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
        
        # For branch-level users
        if is_branch_user:
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
        
        # For sub-branch users
        else:
            if not hierarchy_data['sub_branch']:
                return {
                    "status": "error",
                    "message": "Could not fetch sub-branch details"
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
        is_branch_user = is_branch_level_user()
        
        # For branch-level users
        if is_branch_user:
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
        
        # For sub-branch users
        else:
            if not hierarchy_data['sub_branch']:
                return {
                    "status": "error",
                    "message": "Could not fetch sub-branch details"
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