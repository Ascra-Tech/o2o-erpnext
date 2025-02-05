import frappe
from frappe import _
from frappe.utils import flt, get_datetime

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
            
        if employee.branch:
            po_doc.custom_branch = employee.branch
            
        if employee.custom_sub_branch:
            po_doc.custom_sub_branch = employee.custom_sub_branch
            
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

class PurchaseOrderValidation:
    def __init__(self, doc, method):
        self.doc = doc
        self.stored_capex_total = 0
        self.stored_opex_total = 0

    def validate_transaction_date_mandatory(self):
        if not self.doc.transaction_date:
            frappe.throw(_("Transaction Date is mandatory"), title=_("Missing Date"))
        return True

    def validate_branch_has_supplier(self, branch):
        if not branch.custom_supplier:
            frappe.throw(_("Branch must have an associated supplier"), title=_("Missing Supplier"))
        return True

    def validate_order_value(self, branch, supplier):
        if not self.doc.items:
            return True

        total = flt(self.doc.total)
        branch_min_value = flt(branch.custom_minimum_order_value)
        branch_max_value = flt(branch.custom_maximum_order_value)
        
        both_branch_values_zero = branch_min_value == 0 and branch_max_value == 0
        
        if not both_branch_values_zero:
            if not (branch_min_value <= total <= branch_max_value):
                frappe.throw(
                    _("Total order value ({0}) must be between branch's minimum value {1} and maximum value {2}").format(
                        total, branch_min_value, branch_max_value
                    ),
                    title=_("Invalid Order Value")
                )
            return True
        
        supplier_min_value = flt(supplier.custom_minimum_order_value)
        supplier_max_value = flt(supplier.custom_maximum_order_value)
        
        if not (supplier_min_value <= total <= supplier_max_value):
            frappe.throw(
                _("Total order value ({0}) must be between supplier's minimum value {1} and maximum value {2}").format(
                    total, supplier_min_value, supplier_max_value
                ),
                title=_("Invalid Order Value")
            )
        return True

    def validate_budget_dates(self, supplier):
        transaction_date = get_datetime(self.doc.transaction_date)
        transaction_day = transaction_date.day
        budget_start_day = int(supplier.custom_budget_start_date)
        budget_end_day = int(supplier.custom_budget_end_date)
        
        if not (budget_start_day <= transaction_day <= budget_end_day):
            frappe.throw(
                _("Transaction date day ({0}) must be within supplier's budget days range: {1} to {2}").format(
                    transaction_day, budget_start_day, budget_end_day
                ),
                title=_("Invalid Transaction Date")
            )
        return True

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

    def validate_budgets(self, branch):
        if not self.doc.items:
            return True
            
        capex_total = opex_total = 0
        
        for item in self.doc.items:
            if not item.custom_product_type:
                frappe.throw(
                    _("Product Type must be set for item: {0}").format(item.item_code or item.idx),
                    title=_("Product Type Missing")
                )
                
            item_amount = flt(item.amount)
            if item_amount:
                if item.custom_product_type == 'Capex':
                    capex_total += item_amount
                elif item.custom_product_type == 'Opex':
                    opex_total += item_amount
        
        self.stored_capex_total = capex_total
        self.stored_opex_total = opex_total
        
        if capex_total > 0:
            branch_capex_budget = flt(branch.custom_capex_budget)
            if branch_capex_budget > 0:
                if capex_total > branch_capex_budget:
                    frappe.throw(
                        _("Total Capex amount ({0}) exceeds branch Capex budget ({1})").format(
                            capex_total, branch_capex_budget
                        ),
                        title=_("Capex Budget Exceeded")
                    )
            else:
                supplier = frappe.get_doc("Supplier", branch.custom_supplier)
                supplier_capex_budget = flt(supplier.custom_capex_budget)
                if capex_total > supplier_capex_budget:
                    frappe.throw(
                        _("Total Capex amount ({0}) exceeds supplier Capex budget ({1})").format(
                            capex_total, supplier_capex_budget
                        ),
                        title=_("Capex Budget Exceeded")
                    )
        
        if opex_total > 0:
            branch_opex_budget = flt(branch.custom_opex_budget)
            if branch_opex_budget > 0:
                if opex_total > branch_opex_budget:
                    frappe.throw(
                        _("Total Opex amount ({0}) exceeds branch Opex budget ({1})").format(
                            opex_total, branch_opex_budget
                        ),
                        title=_("Opex Budget Exceeded")
                    )
            else:
                supplier = frappe.get_doc("Supplier", branch.custom_supplier)
                supplier_opex_budget = flt(supplier.custom_opex_budget)
                if opex_total > supplier_opex_budget:
                    frappe.throw(
                        _("Total Opex amount ({0}) exceeds supplier Opex budget ({1})").format(
                            opex_total, supplier_opex_budget
                        ),
                        title=_("Opex Budget Exceeded")
                    )
        return True

    def update_budgets(self, branch):
        try:
            if self.stored_capex_total > 0:
                branch_capex_budget = flt(branch.custom_capex_budget)
                if branch_capex_budget > 0:
                    new_branch_capex_budget = branch_capex_budget - flt(self.stored_capex_total)
                    frappe.db.set_value('Branch', self.doc.custom_branch, 
                                      'custom_capex_budget', new_branch_capex_budget)
                    frappe.msgprint(_("Branch Capex budget updated to {0}").format(new_branch_capex_budget))
                else:
                    supplier = frappe.get_doc("Supplier", branch.custom_supplier)
                    new_supplier_capex_budget = flt(supplier.custom_capex_budget) - flt(self.stored_capex_total)
                    frappe.db.set_value('Supplier', branch.custom_supplier, 
                                      'custom_capex_budget', new_supplier_capex_budget)
                    frappe.msgprint(_("Supplier Capex budget updated to {0}").format(new_supplier_capex_budget))

            if self.stored_opex_total > 0:
                branch_opex_budget = flt(branch.custom_opex_budget)
                if branch_opex_budget > 0:
                    new_branch_opex_budget = branch_opex_budget - flt(self.stored_opex_total)
                    frappe.db.set_value('Branch', self.doc.custom_branch, 
                                      'custom_opex_budget', new_branch_opex_budget)
                    frappe.msgprint(_("Branch Opex budget updated to {0}").format(new_branch_opex_budget))
                else:
                    supplier = frappe.get_doc("Supplier", branch.custom_supplier)
                    new_supplier_opex_budget = flt(supplier.custom_opex_budget) - flt(self.stored_opex_total)
                    frappe.db.set_value('Supplier', branch.custom_supplier, 
                                      'custom_opex_budget', new_supplier_opex_budget)
                    frappe.msgprint(_("Supplier Opex budget updated to {0}").format(new_supplier_opex_budget))
        except Exception as e:
            frappe.log_error("Error updating budgets", e)
            frappe.throw(_("Failed to update budgets"), title=_("Error"))

    def validate(self):
        self.validate_transaction_date_mandatory()
        
        branch = frappe.get_doc("Branch", self.doc.custom_branch)
        self.validate_branch_has_supplier(branch)
        
        supplier = frappe.get_doc("Supplier", branch.custom_supplier)
        self.validate_budget_dates(supplier)
        
        if self.doc.items:
            self.validate_order_value(branch, supplier)
            self.validate_budgets(branch)
            
        self.validate_vendor_access()
        
        return True

    def on_submit(self):
        if (self.stored_capex_total > 0 or self.stored_opex_total > 0) and self.doc.custom_branch:
            branch = frappe.get_doc("Branch", self.doc.custom_branch)
            self.update_budgets(branch)

def validate_purchase_order(doc, method):
    validator = PurchaseOrderValidation(doc, method)
    validator.validate()

def on_submit_purchase_order(doc, method):
    validator = PurchaseOrderValidation(doc, method)
    validator.on_submit()

def get_permission_query_conditions(user):
    """
    Returns query conditions for Purchase Order list view based on user role
    """
    if not user:
        user = frappe.session.user
    
    roles = frappe.get_roles(user)
    
    # First check if user is Administrator - show all POs
    if "Administrator" in roles:
        return ""  # Empty string means no conditions - show all records
    
    # Check for Approver roles (Requisition Approver and PO Approver)
    elif "Requisition Approver" in roles or "PO Approver" in roles:
        # Get employee linked to the user and their sub-branches
        employee = frappe.db.get_value("Employee", 
            {"user_id": user}, 
            ["name", "custom_supplier", "branch", "custom_sub_branch"], 
            as_dict=1
        )
        
        if not employee:
            return "1=0"  # Return false condition if no employee found
            
        # Get additional sub-branches from custom_sub_branch_list
        additional_sub_branches = frappe.get_all("Employee Sub Branch List",
            filters={"parent": employee.name},
            pluck="custom_sub_branch"
        )
        
        conditions = []
        
        # Build conditions based on employee details
        if employee.custom_supplier:
            conditions.append(f"`tabPurchase Order`.supplier = '{employee.custom_supplier}'")
        if employee.branch:
            conditions.append(f"`tabPurchase Order`.custom_branch = '{employee.branch}'")
        
        # Build sub-branch condition to include both primary and additional sub-branches
        sub_branch_conditions = []
        if employee.custom_sub_branch:
            sub_branch_conditions.append(f"`tabPurchase Order`.custom_sub_branch = '{employee.custom_sub_branch}'")
        
        # Add conditions for additional sub-branches
        for sub_branch in additional_sub_branches:
            sub_branch_conditions.append(f"`tabPurchase Order`.custom_sub_branch = '{sub_branch}'")
        
        # Combine sub-branch conditions with OR
        if sub_branch_conditions:
            conditions.append(f"({' OR '.join(sub_branch_conditions)})")
            
        # If any conditions exist, join them with AND
        if conditions:
            return " AND ".join(conditions)
        else:
            return "1=0"  # Return false condition if no matching criteria
    
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
            
        # Get additional sub-branches
        additional_sub_branches = frappe.get_all("Employee Sub Branch List",
            filters={"parent": employee.name},
            pluck="custom_sub_branch"
        )
        
        # Check if document matches employee criteria
        matches_supplier = (doc.supplier == employee.custom_supplier)
        matches_branch = (doc.custom_branch == employee.branch)
        
        # Check if document's sub-branch matches either primary or any additional sub-branch
        matches_sub_branch = (doc.custom_sub_branch == employee.custom_sub_branch or 
                            doc.custom_sub_branch in additional_sub_branches)
        
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