# Copyright (c) 2025, Ascratech LLP and contributors
# For license information, please see license.txt

from frappe.model.document import Document
import frappe
from frappe import _
from frappe.utils import cint
from frappe.model.document import Document
from frappe.permissions import has_permission

class SubBranch(Document):
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