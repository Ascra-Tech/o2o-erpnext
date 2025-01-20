# o2o_erpnext/o2o_erpnext/controllers/permissions.py

import frappe
from frappe import _
from frappe.utils import cstr

class BasePermissionController:
    def __init__(self, doctype, field_name):
        self.doctype = doctype
        self.field_name = field_name

    def get_user_roles(self, user=None):
        if not user:
            user = frappe.session.user
        return frappe.get_roles(user)

class SupplierPermissionController(BasePermissionController):
    def __init__(self, doctype, supplier_field="supplier"):
        super().__init__(doctype, supplier_field)

    def get_supplier_for_user(self, user):
        """Get supplier linked to user directly"""
        return frappe.get_value("Supplier", 
            filters={"custom_user": user}, 
            fieldname="name")

    def get_vendor_user_suppliers(self, user):
        """Get all suppliers accessible to a vendor user"""
        # Find employee linked to user
        employee = frappe.get_value("Employee", 
            filters={"user_id": user}, 
            fieldname="name")
            
        if not employee:
            return []
            
        suppliers = []
        
        # Get primary supplier from custom field
        primary_supplier = frappe.get_value("Employee", employee, "custom_supplier")
        if primary_supplier:
            suppliers.append(primary_supplier)
            
        # Get additional suppliers from child table
        supplier_list = frappe.get_all(
            "Supplier Access List",
            filters={"parent": employee},
            fields=["supplier"],
            pluck="supplier"
        )
        
        if supplier_list:
            suppliers.extend(supplier_list)
        
        # Remove duplicates and None values
        return list(set(filter(None, suppliers)))

    def get_permission_query_conditions(self, user=None):
        """Generate SQL conditions for list views"""
        if not user:
            user = frappe.session.user

        user_roles = self.get_user_roles(user)
        conditions = []

        try:
            # Handle Supplier role
            if "Supplier" in user_roles:
                supplier = self.get_supplier_for_user(user)
                if supplier:
                    conditions.append(
                        f"`tab{self.doctype}`.{self.field_name} = {frappe.db.escape(supplier)}"
                    )
                else:
                    return "1=0"

            # Handle Vendor User role
            elif "Vendor User" in user_roles:
                suppliers = self.get_vendor_user_suppliers(user)
                if suppliers:
                    suppliers_str = "', '".join([frappe.db.escape(s) for s in suppliers])
                    conditions.append(
                        f"`tab{self.doctype}`.{self.field_name} in ('{suppliers_str}')"
                    )
                else:
                    return "1=0"

            # If neither role has access conditions, return empty string for default permissions
            return " and ".join(conditions) if conditions else ""

        except Exception as e:
            frappe.log_error(
                f"Error in supplier permission query for {self.doctype}: {str(e)}",
                "Permission Query Error"
            )
            return "1=0"

    def has_permission(self, doc, user=None, permission_type=None):
        """Check document level permissions"""
        if not user:
            user = frappe.session.user

        try:
            user_roles = self.get_user_roles(user)
            doc_supplier = getattr(doc, self.field_name, None)

            # Handle Supplier role
            if "Supplier" in user_roles:
                supplier = self.get_supplier_for_user(user)
                return bool(supplier and doc_supplier == supplier)

            # Handle Vendor User role
            elif "Vendor User" in user_roles:
                suppliers = self.get_vendor_user_suppliers(user)
                return bool(suppliers and doc_supplier in suppliers)

            # For other roles, use standard permissions
            return True

        except Exception as e:
            frappe.log_error(
                f"Error checking document permission for {self.doctype}: {str(e)}",
                "Permission Check Error"
            )
            return False

class CustomerPermissionController(BasePermissionController):
    def __init__(self, doctype, customer_field="customer"):
        super().__init__(doctype, customer_field)

    def get_customer_for_user(self, user):
        return frappe.get_value("Customer", 
            filters={"custom_user": user}, 
            fieldname="name")

    def get_permission_query_conditions(self, user=None):
        if not user:
            user = frappe.session.user

        try:
            if "Customer" in self.get_user_roles(user):
                customer = self.get_customer_for_user(user)
                if customer:
                    return f"`tab{self.doctype}`.{self.field_name} = {frappe.db.escape(customer)}"
                return "1=0"
            return ""

        except Exception as e:
            frappe.log_error(
                f"Error in customer permission query for {self.doctype}: {str(e)}",
                "Permission Query Error"
            )
            return "1=0"

    def has_permission(self, doc, user=None, permission_type=None):
        if not user:
            user = frappe.session.user

        try:
            if "Customer" in self.get_user_roles(user):
                customer = self.get_customer_for_user(user)
                doc_customer = getattr(doc, self.field_name, None)
                return bool(customer and doc_customer == customer)
            return True

        except Exception as e:
            frappe.log_error(
                f"Error checking document permission for {self.doctype}: {str(e)}",
                "Permission Check Error"
            )
            return False

# Permission handlers for Purchase Order
def get_purchase_order_permissions(user=None):
    controller = SupplierPermissionController("Purchase Order", "supplier")
    return controller.get_permission_query_conditions(user)

def has_purchase_order_permission(doc, user=None, permission_type=None):
    controller = SupplierPermissionController("Purchase Order", "supplier")
    return controller.has_permission(doc, user, permission_type)

# Permission handlers for Purchase Invoice
def get_purchase_invoice_permissions(user=None):
    controller = SupplierPermissionController("Purchase Invoice", "supplier")
    return controller.get_permission_query_conditions(user)

def has_purchase_invoice_permission(doc, user=None, permission_type=None):
    controller = SupplierPermissionController("Purchase Invoice", "supplier")
    return controller.has_permission(doc, user, permission_type)

# Permission handlers for Purchase Receipt
def get_purchase_receipt_permissions(user=None):
    controller = SupplierPermissionController("Purchase Receipt", "supplier")
    return controller.get_permission_query_conditions(user)

def has_purchase_receipt_permission(doc, user=None, permission_type=None):
    controller = SupplierPermissionController("Purchase Receipt", "supplier")
    return controller.has_permission(doc, user, permission_type)

# Permission handlers for Sales Order
def get_sales_order_permissions(user=None):
    controller = CustomerPermissionController("Sales Order", "customer")
    return controller.get_permission_query_conditions(user)

def has_sales_order_permission(doc, user=None, permission_type=None):
    controller = CustomerPermissionController("Sales Order", "customer")
    return controller.has_permission(doc, user, permission_type)

# Permission handlers for Sales Invoice
def get_sales_invoice_permissions(user=None):
    controller = CustomerPermissionController("Sales Invoice", "customer")
    return controller.get_permission_query_conditions(user)

def has_sales_invoice_permission(doc, user=None, permission_type=None):
    controller = CustomerPermissionController("Sales Invoice", "customer")
    return controller.has_permission(doc, user, permission_type)

# Permission handlers for Delivery Note
def get_delivery_note_permissions(user=None):
    controller = CustomerPermissionController("Delivery Note", "customer")
    return controller.get_permission_query_conditions(user)

def has_delivery_note_permission(doc, user=None, permission_type=None):
    controller = CustomerPermissionController("Delivery Note", "customer")
    return controller.has_permission(doc, user, permission_type)