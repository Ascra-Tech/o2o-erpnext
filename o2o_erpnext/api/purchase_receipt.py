import frappe
from frappe import _
from frappe.utils import flt, get_datetime
from frappe.exceptions import DoesNotExistError

@frappe.whitelist()
def validate_and_set_purchase_receipt_defaults(doc_name=None):
    """
    Validates and sets default values for a Purchase Receipt based on the logged-in user's Employee record.
    """
    try:
        user_email = frappe.session.user
        employee = frappe.get_value("Employee", 
                                  {"user_id": user_email}, 
                                  ["name", "custom_supplier", "branch", "custom_sub_branch"],
                                  as_dict=1)
        
        if not employee:
            frappe.throw(_("No Employee record found linked to your User ID"), title=_("Employee Not Found"))
            
        if doc_name:
            pr_doc = frappe.get_doc("Purchase Receipt", doc_name)
        else:
            pr_doc = frappe.new_doc("Purchase Receipt")
            
        if employee.custom_supplier:
            pr_doc.supplier = employee.custom_supplier
            
        if employee.branch:
            pr_doc.custom_branch = employee.branch
            
        if employee.custom_sub_branch:
            pr_doc.custom_sub_branch = employee.custom_sub_branch
            
        if not doc_name:
            return {
                "status": "success",
                "message": _("Default values set successfully"),
                "data": {
                    "supplier": employee.custom_supplier,
                    "custom_branch": employee.branch,
                    "custom_sub_branch": employee.custom_sub_branch
                }
            }
        
        pr_doc.save()
        frappe.db.commit()
        
        return {
            "status": "success",
            "message": _("Purchase Receipt updated successfully")
        }
            
    except Exception as e:
        frappe.log_error(f"Error in Purchase Receipt auto-fill: {str(e)}", 
                        "Purchase Receipt API Error")
        raise e

@frappe.whitelist()
def get_supplier_vendors(supplier):
    """
    Fetches the list of vendors associated with a specific supplier.
    """
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
def check_linked_purchase_invoices(purchase_receipt):
    """Check if a Purchase Receipt has linked Purchase Invoices in Draft or Submitted status"""
    if not purchase_receipt:
        return {"success": False, "message": "Purchase Receipt name is required"}
   
    try:
        # Log start of check (concise)
        frappe.log_error(f"Checking PR: {purchase_receipt}", "PI Check")
        
        # First, get all linked invoices
        linked_invoices = frappe.db.sql("""
            SELECT pi.name, pi.status, pi.docstatus, pi.is_return, pi.return_against
            FROM `tabPurchase Invoice` pi
            JOIN `tabPurchase Invoice Item` pii ON pii.parent = pi.name
            WHERE pii.purchase_receipt = %s
            AND pi.docstatus IN (0, 1)
        """, purchase_receipt, as_dict=1)
        
        # Log count only to avoid truncation
        frappe.log_error(f"Found {len(linked_invoices)} invoices", "PI Check")
        
        if not linked_invoices:
            return {
                "success": True,
                "message": "No linked Purchase Invoices found",
                "has_active_invoices": False,
                "invoices": []
            }
        
        # Build a dictionary of return invoices keyed by the original invoice they're returning
        return_invoices = {}
        for inv in linked_invoices:
            if inv.get("is_return") and inv.get("return_against"):
                if inv.get("return_against") not in return_invoices:
                    return_invoices[inv.get("return_against")] = []
                return_invoices[inv.get("return_against")].append(inv.get("name"))
        
        # Now filter to find active, non-fully-returned invoices
        active_invoices = []
        for inv in linked_invoices:
            # Skip return invoices themselves
            if inv.get("is_return"):
                continue
                
            # Check if this invoice has been fully returned
            fully_returned = False
            if inv.get("name") in return_invoices:
                # For simplicity, we'll consider an invoice with any return against it as "fully returned"
                # In a real system, you might want to check the amounts to determine if it's fully or partially returned
                fully_returned = True
                
            if not fully_returned and inv.get("docstatus") in [0, 1]:  # Draft or Submitted
                active_invoices.append(inv)
                # Log each active invoice separately
                frappe.log_error(f"Active: {inv.name} status={inv.status} docstatus={inv.docstatus}", "PI Check")
        
        if active_invoices:
            return {
                "success": True,
                "message": f"Found {len(active_invoices)} active linked Purchase Invoices",
                "has_active_invoices": True,
                "invoices": active_invoices
            }
        else:
            return {
                "success": True,
                "message": "No active linked Purchase Invoices found",
                "has_active_invoices": False,
                "invoices": linked_invoices
            }
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        frappe.log_error(error_msg, "PI Check Error")
        return {
            "success": False,
            "message": error_msg,
            "has_active_invoices": False,
            "invoices": []
        }

@frappe.whitelist()
def block_invoice_creation_if_linked(purchase_receipt):
    """
    Checks if any linked purchase invoices exist for a purchase receipt and blocks
    creation of new invoices if active ones are found.
    
    This function considers an invoice as "inactive" if it has been fully returned.
    
    Returns:
        dict: {
            "allow_creation": True/False,
            "message": str,
            "invoices": list of invoices (if any)
        }
    """
    try:
        result = check_linked_purchase_invoices(purchase_receipt)
        
        if not result["success"]:
            return {
                "allow_creation": False,
                "message": result["message"],
                "invoices": []
            }
        
        if result["has_active_invoices"]:
            invoice_details = [f"{inv['name']} ({inv['status']})" for inv in result["invoices"]]
            return {
                "allow_creation": False,
                "message": f"Cannot create Purchase Invoice. This Purchase Receipt is already linked to active invoices: {', '.join(invoice_details)}",
                "invoices": result["invoices"]
            }
        
        return {
            "allow_creation": True,
            "message": "No active Purchase Invoices found. You can create a new one.",
            "invoices": []
        }
    except Exception as e:
        frappe.log_error(f"Error in block_invoice_creation: {str(e)}", 
                        "Purchase Receipt API Error")
        return {
            "allow_creation": False,
            "message": f"Error checking linked invoices: {str(e)}",
            "invoices": []
        }

def get_permission_query_conditions(user, doctype):
    """
    Returns SQL conditions to filter Purchase Receipt based on user roles and related employee/supplier data.
    """
    roles = frappe.get_roles(user)

    if "Administrator" in roles:
        return None  # Administrator can see all
    
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
            conditions.append(f"`tabPurchase Receipt`.supplier = '{employee.custom_supplier}'")
        if employee.branch:
            conditions.append(f"`tabPurchase Receipt`.custom_branch = '{employee.branch}'")

        # --- Sub-Branch Filtering (Primary OR any secondary sub-branch) ---
        sub_branch_conditions = []

        # 1. Primary Sub-Branch (custom_sub_branch)
        if employee.custom_sub_branch:
            sub_branch_conditions.append(f"`tabPurchase Receipt`.custom_sub_branch = '{employee.custom_sub_branch}'")

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
                        sub_branch_conditions.append(f"`tabPurchase Receipt`.custom_sub_branch = '{sub_branch}'")
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
            conditions.append(f"`tabPurchase Receipt`.supplier = '{employee.custom_supplier}'")
        if employee.branch:
            conditions.append(f"`tabPurchase Receipt`.custom_branch = '{employee.branch}'")
        if employee.custom_sub_branch:
            conditions.append(f"`tabPurchase Receipt`.custom_sub_branch = '{employee.custom_sub_branch}'")
            
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
        return f"`tabPurchase Receipt`.supplier = '{supplier}'"

    # Check if user has Vendor User role
    elif "Vendor User" in roles:
        # Get vendor linked to the user
        vendor = frappe.db.get_value("Vendor", {"user_id": user}, "name")
        
        if not vendor:
            return "1=0"  # Return false condition if no vendor found
            
        # Return condition to match PO custom_vendor with user's vendor
        return f"`tabPurchase Receipt`.custom_vendor = '{vendor}'"
    
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


def update_custom_fields_from_first_item(doc, method=None):
    """
    Update custom_purchase_order and custom_purchase_invoice fields 
    from the first item in the Purchase Receipt
    """
    # Only run on draft documents
    if doc.docstatus != 0:
        return
    
    if doc.items and len(doc.items) > 0:
        first_item = doc.items[0]
        
        # Get values from first item
        po_value = getattr(first_item, 'purchase_order', '') or ''
        pi_value = getattr(first_item, 'purchase_invoice', '') or ''
        
        # Update custom fields
        doc.custom_purchase_order = po_value
        doc.custom_purchase_invoice = pi_value
        
        frappe.logger().info(f"Updated Purchase Receipt {doc.name}: PO={po_value}, PI={pi_value}")
    else:
        # Clear fields if no items
        doc.custom_purchase_order = ''
        doc.custom_purchase_invoice = ''

@frappe.whitelist()
def update_submitted_pr_items(items_data, deleted_items=None):
    """
    Update items in a submitted Purchase Receipt using direct database updates.
    This bypasses ERPNext's restrictions on editing submitted documents.
    
    Args:
        items_data: JSON string or list of item changes with name, changes dict
        deleted_items: JSON string or list of item names to delete
    
    Returns:
        dict with status and message
    """
    import json
    
    try:
        # Parse input data
        if isinstance(items_data, str):
            items_data = json.loads(items_data)
        if isinstance(deleted_items, str):
            deleted_items = json.loads(deleted_items) if deleted_items else []
        elif deleted_items is None:
            deleted_items = []
            
        if not items_data and not deleted_items:
            return {
                "status": "error",
                "message": _("No items data or deleted items provided")
            }
        
        # Validate user permissions
        if not frappe.has_permission("Purchase Receipt", "write"):
            frappe.throw(_("You don't have permission to edit Purchase Receipts"))
        
        updated_items = []
        updated_pr_names = []
        deleted_item_names = []
        
        # Process deleted items first
        for item_name in deleted_items:
            try:
                # Get the Purchase Receipt name before deletion
                pr_name = frappe.db.get_value("Purchase Receipt Item", item_name, "parent")
                if not pr_name:
                    continue
                    
                # Delete the item directly from database
                frappe.db.sql("DELETE FROM `tabPurchase Receipt Item` WHERE name = %s", (item_name,))
                
                deleted_item_names.append(item_name)
                if pr_name not in updated_pr_names:
                    updated_pr_names.append(pr_name)
                    
            except Exception as e:
                frappe.log_error(f"Error deleting Purchase Receipt item {item_name}: {str(e)}", "PR Item Deletion Error")
                continue
        
        # Process item updates
        for item_update in items_data:
            item_name = item_update.get("name")
            changes = item_update.get("changes", {})
            
            if not item_name or not changes:
                continue
                
            try:
                # Get the Purchase Receipt name
                pr_name = frappe.db.get_value("Purchase Receipt Item", item_name, "parent")
                if not pr_name:
                    continue
                
                # Validate user has write permission for this Purchase Receipt
                if not frappe.has_permission("Purchase Receipt", "write", pr_name):
                    frappe.throw(_("You don't have permission to edit Purchase Receipt {0}").format(pr_name))
                
                # Allowed fields for editing
                allowed_fields = ['qty', 'rate', 'amount', 'base_amount', 'base_rate', 'base_qty', 'received_qty']
                
                # Update each changed field using direct database update
                for field, value in changes.items():
                    if field in allowed_fields:
                        # Direct database update - bypasses all ERPNext restrictions
                        frappe.db.sql(
                            "UPDATE `tabPurchase Receipt Item` SET {0} = %s WHERE name = %s".format(field),
                            (value, item_name)
                        )
                        
                        # Calculate and update amount (qty * rate) and GSTN values
                        if field in ['qty', 'rate']:
                            # Get current qty, rate, and tax template
                            current_data = frappe.db.get_value('Purchase Receipt Item', item_name, ['qty', 'rate', 'item_tax_template'], as_dict=True)
                            if current_data:
                                new_amount = float(current_data.qty or 0) * float(current_data.rate or 0)
                                
                                # Calculate GSTN value based on tax template using percentage-wise logic
                                gstn_value = 0.0
                                template = current_data.item_tax_template or ""
                                gst_rate = 0
                                
                                # Extract GST rate from template name (same logic as Purchase Invoice)
                                if "GST 5%" in template:
                                    gst_rate = 5
                                elif "GST 12%" in template:
                                    gst_rate = 12
                                elif "GST 18%" in template:
                                    gst_rate = 18
                                elif "GST 28%" in template:
                                    gst_rate = 28
                                
                                # Calculate and set GST value if applicable
                                if gst_rate > 0:
                                    gstn_value = round(new_amount * gst_rate / 100, 2)
                                    
                                    # Calculate SGST, CGST, IGST (typically split equally for intra-state, full IGST for inter-state)
                                    # Assuming intra-state transactions: SGST = CGST = GST/2, IGST = 0
                                    # For inter-state: SGST = 0, CGST = 0, IGST = GST
                                    # We'll use intra-state logic by default (SGST = CGST = GST/2)
                                    sgst_amount = round(gstn_value / 2, 2)
                                    cgst_amount = round(gstn_value / 2, 2)
                                    igst_amount = 0  # For intra-state transactions
                                
                                # Update amount, base_amount
                                frappe.db.sql(
                                    """UPDATE `tabPurchase Receipt Item` 
                                       SET amount = %s, base_amount = %s
                                       WHERE name = %s""",
                                    (new_amount, new_amount, item_name)
                                )
                                
                                # Try to update GSTN fields if they exist
                                try:
                                    frappe.db.sql(
                                        """UPDATE `tabPurchase Receipt Item` 
                                           SET custom_gstn_value = %s, custom_grand_total = %s,
                                               custom_sgst_amount = %s, custom_cgst_amount = %s, custom_igst_amount = %s
                                           WHERE name = %s""",
                                        (gstn_value, new_amount + gstn_value, sgst_amount, cgst_amount, igst_amount, item_name)
                                    )
                                except Exception as e:
                                    # If custom fields don't exist, skip GSTN update
                                    if "Unknown column" in str(e):
                                        frappe.log_error(f"GSTN custom fields not found in database: {e}", "GSTN Update Warning")
                                    else:
                                        raise e
                
                updated_items.append(item_name)
                
                if pr_name not in updated_pr_names:
                    updated_pr_names.append(pr_name)
            
            except Exception as e:
                frappe.log_error(f"Error updating Purchase Receipt item {item_name}: {str(e)}", "PR Item Update Error")
                continue
        
        # Recalculate Purchase Receipt totals using percentage-wise GST logic
        for pr_name in updated_pr_names:
            # Get all items for this Purchase Receipt to calculate GST totals
            items = frappe.db.sql("""
                SELECT qty, rate, amount, item_tax_template, custom_gstn_value
                FROM `tabPurchase Receipt Item` 
                WHERE parent = %s
            """, (pr_name,), as_dict=True)
            
            # Initialize summary values (same as Purchase Invoice)
            gst_5_total = 0
            gst_12_total = 0
            gst_18_total = 0
            gst_28_total = 0
            goods_5_total = 0
            goods_12_total = 0
            goods_18_total = 0
            goods_28_total = 0
            total_qty = 0
            total_amount = 0
            total_base_amount = 0
            
            # Initialize SGST, CGST, IGST totals
            total_sgst = 0
            total_cgst = 0
            total_igst = 0
            
            # Process each item with percentage-wise GST calculation
            for item in items:
                template = item.get('item_tax_template') or ""
                amount = float(item.get('amount') or 0)
                gst_rate = 0
                
                # Extract GST rate from template name
                if "GST 5%" in template:
                    gst_rate = 5
                elif "GST 12%" in template:
                    gst_rate = 12
                elif "GST 18%" in template:
                    gst_rate = 18
                elif "GST 28%" in template:
                    gst_rate = 28
                
                # Calculate and set GST value if applicable
                if gst_rate > 0:
                    gstn_value = round(amount * gst_rate / 100, 2)
                    
                    # Calculate SGST, CGST, IGST (typically split equally for intra-state, full IGST for inter-state)
                    # Assuming intra-state transactions: SGST = CGST = GST/2, IGST = 0
                    # For inter-state: SGST = 0, CGST = 0, IGST = GST
                    # We'll use intra-state logic by default (SGST = CGST = GST/2)
                    sgst_amount = round(gstn_value / 2, 2)
                    cgst_amount = round(gstn_value / 2, 2)
                    igst_amount = 0  # For intra-state transactions
                    
                    # Add to appropriate totals
                    if gst_rate == 5:
                        gst_5_total += gstn_value
                        goods_5_total += amount
                    elif gst_rate == 12:
                        gst_12_total += gstn_value
                        goods_12_total += amount
                    elif gst_rate == 18:
                        gst_18_total += gstn_value
                        goods_18_total += amount
                    elif gst_rate == 28:
                        gst_28_total += gstn_value
                        goods_28_total += amount
                    
                    # Add to SGST, CGST, IGST totals
                    total_sgst += sgst_amount
                    total_cgst += cgst_amount
                    total_igst += igst_amount
                
                # Update basic totals
                total_qty += float(item.get('qty') or 0)
                total_amount += amount
                total_base_amount += amount  # Assuming base_amount is same as amount for simplicity
            
            # Calculate total GSTN value
            total_gstn = round(gst_5_total + gst_12_total + gst_18_total + gst_28_total, 2)
            
            # Calculate grand total (total + total_gstn)
            grand_total = total_amount + total_gstn
            base_grand_total = total_base_amount + total_gstn
            
            # Update Purchase Receipt totals directly in database
            frappe.db.sql("""
                UPDATE `tabPurchase Receipt` 
                SET total_qty = %s, total = %s, base_total = %s, grand_total = %s, base_grand_total = %s
                WHERE name = %s
            """, (
                total_qty or 0,
                total_amount or 0,
                total_base_amount or 0,
                grand_total,
                base_grand_total,
                pr_name
            ))
            
            # Update custom GST percentage-wise fields if they exist
            try:
                frappe.db.sql("""
                    UPDATE `tabPurchase Receipt` 
                    SET custom_gst_5__ot = %s, custom_gst_12__ot = %s, custom_gst_18__ot = %s, custom_gst_28__ot = %s,
                        custom_5_goods_value = %s, custom_12_goods_value = %s, custom_18_goods_value = %s, custom_28_goods_value = %s,
                        custom_total_gstn = %s, custom_grand_total = %s,
                        custom_total_sgst = %s, custom_total_cgst = %s, custom_total_igst = %s
                    WHERE name = %s
                """, (
                    round(gst_5_total, 2),
                    round(gst_12_total, 2),
                    round(gst_18_total, 2),
                    round(gst_28_total, 2),
                    round(goods_5_total, 2),
                    round(goods_12_total, 2),
                    round(goods_18_total, 2),
                    round(goods_28_total, 2),
                    total_gstn,
                    grand_total,
                    round(total_sgst, 2),
                    round(total_cgst, 2),
                    round(total_igst, 2),
                    pr_name
                ))
            except Exception as e:
                # If custom fields don't exist, skip GSTN update
                if "Unknown column" in str(e):
                    frappe.log_error(f"GSTN custom fields not found in Purchase Receipt: {e}", "PR GSTN Update Warning")
                else:
                    raise e
            
            # Add comment for audit trail
            comment_text = _('Items updated via Edit Submitted Items: {0} items updated, {1} items deleted by {2}').format(
                len(updated_items), len(deleted_item_names), frappe.session.user
            )
            frappe.db.sql("""
                INSERT INTO `tabComment` (name, comment_type, reference_doctype, reference_name, content, comment_by, creation, modified)
                VALUES (UUID(), 'Edit', 'Purchase Receipt', %s, %s, %s, NOW(), NOW())
            """, (pr_name, comment_text, frappe.session.user))
        
        # Commit the transaction
        frappe.db.commit()
        
        return {
            "status": "success",
            "message": _("Purchase Receipt items updated successfully: {0} items updated, {1} items deleted").format(
                len(updated_items), len(deleted_item_names)
            ),
            "updated_items": updated_items,
            "deleted_items": deleted_item_names
        }
        
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(f"Error updating Purchase Receipt items: {str(e)}", "PR Update Error")
        frappe.throw(_('Error updating items: {0}').format(str(e)))

# Manual whitelist for additional security
update_submitted_pr_items.whitelisted = True