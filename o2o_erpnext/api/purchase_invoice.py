import frappe
from frappe import _
from frappe.utils import flt, get_datetime
from frappe.exceptions import DoesNotExistError

@frappe.whitelist()
def validate_and_set_purchase_invoice_defaults(doc_name=None):
    try:
        user_email = frappe.session.user
        employee = frappe.get_value("Employee", 
                                  {"user_id": user_email}, 
                                  ["name", "custom_supplier", "branch", "custom_sub_branch"],
                                  as_dict=1)
        
        if not employee:
            frappe.throw(_("No Employee record found linked to your User ID"), title=_("Employee Not Found"))
            
        if doc_name:
            pi_doc = frappe.get_doc("Purchase Invoice", doc_name)
        else:
            pi_doc = frappe.new_doc("Purchase Invoice")
            
        if employee.custom_supplier:
            pi_doc.supplier = employee.custom_supplier
            
        if employee.branch:
            pi_doc.custom_branch = employee.branch
            
        if employee.custom_sub_branch:
            pi_doc.custom_sub_branch = employee.custom_sub_branch
            
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
        
        pi_doc.save()
        frappe.db.commit()
        
        return {
            "status": "success",
            "message": _("Purchase Invoice updated successfully")
        }
            
    except Exception as e:
        frappe.log_error(f"Error in Purchase Invoice auto-fill: {str(e)}", 
                        "Purchase Invoice API Error")
        raise e

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

class PurchaseInvoiceValidation:
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
    Returns SQL conditions to filter Purchase Invoices based on user roles and related employee/supplier data.
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
            conditions.append(f"`tabPurchase Invoice`.supplier = '{employee.custom_supplier}'")
        if employee.branch:
            conditions.append(f"`tabPurchase Invoice`.custom_branch = '{employee.branch}'")

        # --- Sub-Branch Filtering (Primary OR any secondary sub-branch) ---
        sub_branch_conditions = []

        # 1. Primary Sub-Branch (custom_sub_branch)
        if employee.custom_sub_branch:
            sub_branch_conditions.append(f"`tabPurchase Invoice`.custom_sub_branch = '{employee.custom_sub_branch}'")

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
                        sub_branch_conditions.append(f"`tabPurchase Invoice`.custom_sub_branch = '{sub_branch}'")
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
            conditions.append(f"`tabPurchase Invoice`.supplier = '{employee.custom_supplier}'")
        if employee.branch:
            conditions.append(f"`tabPurchase Invoice`.custom_branch = '{employee.branch}'")
        if employee.custom_sub_branch:
            conditions.append(f"`tabPurchase Invoice`.custom_sub_branch = '{employee.custom_sub_branch}'")
            
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
        return f"`tabPurchase Invoice`.supplier = '{supplier}'"

    # Check if user has Vendor User role
    elif "Vendor User" in roles:
        # Get vendor linked to the user
        vendor = frappe.db.get_value("Vendor", {"user_id": user}, "name")
        
        if not vendor:
            return "1=0"  # Return false condition if no vendor found
            
        # Return condition to match PO custom_vendor with user's vendor
        return f"`tabPurchase Invoice`.custom_vendor = '{vendor}'"
    
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
@frappe.whitelist()
def calculate_gst_values_for_purchase_invoice(doc_name):
    """
    Calculate GST values for Purchase Invoice and save the document.
    Based on existing client-side GST calculation logic.
    """
    try:
        # Get the Purchase Invoice document
        pi_doc = frappe.get_doc("Purchase Invoice", doc_name)
        
        # Initialize summary values
        gst_5_total = 0
        gst_12_total = 0
        gst_18_total = 0
        gst_28_total = 0
        goods_5_total = 0
        goods_12_total = 0
        goods_18_total = 0
        goods_28_total = 0
        
        # Process each item in the invoice
        for item in pi_doc.get('items', []):
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
                item.custom_gstn_value = gstn_value
                
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
        
        # Set document-level summary fields
        pi_doc.custom_gst_5__ot = round(gst_5_total, 2)
        pi_doc.custom_gst_12__ot = round(gst_12_total, 2)
        pi_doc.custom_gst_18__ot = round(gst_18_total, 2)
        pi_doc.custom_gst_28__ot = round(gst_28_total, 2)
        pi_doc.custom_5_goods_value = round(goods_5_total, 2)
        pi_doc.custom_12_goods_value = round(goods_12_total, 2)
        pi_doc.custom_18_goods_value = round(goods_18_total, 2)
        pi_doc.custom_28_goods_value = round(goods_28_total, 2)
        
        # Calculate total GSTN value
        total_gstn = round(gst_5_total + gst_12_total + gst_18_total + gst_28_total, 2)
        
        # Set total GSTN if the field exists
        if hasattr(pi_doc, 'gstn_value'):
            pi_doc.gstn_value = total_gstn
        
        # Save the document
        pi_doc.save(ignore_permissions=True)
        frappe.db.commit()
        
        return {
            "status": "success",
            "message": "GST values calculated successfully"
        }
    
    except Exception as e:
        frappe.log_error(f"Error calculating GST values for Purchase Invoice: {str(e)}", 
                        "GST Calculation Error")
        return {
            "status": "error",
            "message": str(e)
        }

@frappe.whitelist()
def update_submitted_pi_items(items_data, deleted_items=None):
    """
    Update items in a submitted Purchase Invoice using direct database updates.
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
        if not frappe.has_permission("Purchase Invoice", "write"):
            frappe.throw(_("You don't have permission to edit Purchase Invoices"))
        
        updated_items = []
        updated_pi_names = []
        deleted_item_names = []
        
        # Process deleted items first
        for item_name in deleted_items:
            try:
                # Get the Purchase Invoice name before deletion
                pi_name = frappe.db.get_value("Purchase Invoice Item", item_name, "parent")
                if not pi_name:
                    continue
                    
                # Delete the item directly from database
                frappe.db.sql("DELETE FROM `tabPurchase Invoice Item` WHERE name = %s", (item_name,))
                
                deleted_item_names.append(item_name)
                if pi_name not in updated_pi_names:
                    updated_pi_names.append(pi_name)
                    
            except Exception as e:
                frappe.log_error(f"Error deleting Purchase Invoice item {item_name}: {str(e)}", "PI Item Deletion Error")
                continue
        
        # Process item updates
        for item_update in items_data:
            item_name = item_update.get("name")
            changes = item_update.get("changes", {})
            
            if not item_name or not changes:
                continue
                
            try:
                # Get the Purchase Invoice name
                pi_name = frappe.db.get_value("Purchase Invoice Item", item_name, "parent")
                if not pi_name:
                    continue
                
                # Validate user has write permission for this Purchase Invoice
                if not frappe.has_permission("Purchase Invoice", "write", pi_name):
                    frappe.throw(_("You don't have permission to edit Purchase Invoice {0}").format(pi_name))
                
                # Allowed fields for editing
                allowed_fields = ['qty', 'rate', 'amount', 'base_amount', 'base_rate', 'base_qty']
                
                # Update each changed field using direct database update
                for field, value in changes.items():
                    if field in allowed_fields:
                        # Direct database update - bypasses all ERPNext restrictions
                        frappe.db.sql(
                            "UPDATE `tabPurchase Invoice Item` SET {0} = %s WHERE name = %s".format(field),
                            (value, item_name)
                        )
                        
                        # Calculate and update amount (qty * rate) and GSTN values
                        if field in ['qty', 'rate']:
                            # Get current qty, rate, and tax template
                            current_data = frappe.db.get_value('Purchase Invoice Item', item_name, ['qty', 'rate', 'item_tax_template'], as_dict=True)
                            if current_data:
                                new_amount = float(current_data.qty or 0) * float(current_data.rate or 0)
                                
                                # Calculate GSTN value based on tax template using percentage-wise logic
                                gstn_value = 0.0
                                template = current_data.item_tax_template or ""
                                gst_rate = 0
                                
                                # Extract GST rate from template name (same logic as calculate_gst_values_for_purchase_invoice)
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
                                
                                # Update amount, net_amount, base_amount, base_net_amount
                                frappe.db.sql(
                                    """UPDATE `tabPurchase Invoice Item` 
                                       SET amount = %s, base_amount = %s
                                       WHERE name = %s""",
                                    (new_amount, new_amount, item_name)
                                )
                                
                                # Try to update GSTN fields if they exist
                                try:
                                    frappe.db.sql(
                                        """UPDATE `tabPurchase Invoice Item` 
                                           SET custom_gstn_value = %s, custom_grand_total = %s,
                                               sgst_amount = %s, cgst_amount = %s, igst_amount = %s
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
                
                if pi_name not in updated_pi_names:
                    updated_pi_names.append(pi_name)
            
            except Exception as e:
                frappe.log_error(f"Error updating Purchase Invoice item {item_name}: {str(e)}", "PI Item Update Error")
                continue
        
        # Recalculate Purchase Invoice totals using percentage-wise GST logic
        for pi_name in updated_pi_names:
            # Get all items for this Purchase Invoice to calculate GST totals
            items = frappe.db.sql("""
                SELECT qty, rate, amount, item_tax_template, custom_gstn_value
                FROM `tabPurchase Invoice Item` 
                WHERE parent = %s
            """, (pi_name,), as_dict=True)
            
            # Initialize summary values (same as calculate_gst_values_for_purchase_invoice)
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
            
            # Update Purchase Invoice totals directly in database
            frappe.db.sql("""
                UPDATE `tabPurchase Invoice` 
                SET total_qty = %s, total = %s, base_total = %s, grand_total = %s, base_grand_total = %s
                WHERE name = %s
            """, (
                total_qty or 0,
                total_amount or 0,
                total_base_amount or 0,
                grand_total,
                base_grand_total,
                pi_name
            ))
            
            # Update custom GST percentage-wise fields if they exist
            try:
                frappe.db.sql("""
                    UPDATE `tabPurchase Invoice` 
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
                    pi_name
                ))
            except Exception as e:
                # If custom fields don't exist, skip GSTN update
                if "Unknown column" in str(e):
                    frappe.log_error(f"GSTN custom fields not found in Purchase Invoice: {e}", "PI GSTN Update Warning")
                else:
                    raise e
            
            # Add comment for audit trail
            comment_text = _('Items updated via Edit Submitted Items: {0} items updated, {1} items deleted by {2}').format(
                len(updated_items), len(deleted_item_names), frappe.session.user
            )
            frappe.db.sql("""
                INSERT INTO `tabComment` (name, comment_type, reference_doctype, reference_name, content, comment_by, creation, modified)
                VALUES (UUID(), 'Edit', 'Purchase Invoice', %s, %s, %s, NOW(), NOW())
            """, (pi_name, comment_text, frappe.session.user))
        
        # Commit the transaction
        frappe.db.commit()
        
        return {
            "status": "success",
            "message": _("Purchase Invoice items updated successfully: {0} items updated, {1} items deleted").format(
                len(updated_items), len(deleted_item_names)
            ),
            "updated_items": updated_items,
            "deleted_items": deleted_item_names
        }
        
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(f"Error updating Purchase Invoice items: {str(e)}", "PI Update Error")
        frappe.throw(_('Error updating items: {0}').format(str(e)))

# Manual whitelist for additional security
update_submitted_pi_items.whitelisted = True