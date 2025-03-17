import frappe
from frappe import _
from frappe.utils import random_string

@frappe.whitelist()
def create_user(employee, email=None, password=None):
    """
    Create user for employee with clean role assignment
    with option to set custom password
    """
    if not employee:
        frappe.throw(_("Please specify Employee"))
    
    try:
        employee_doc = frappe.get_doc("Employee", employee)
        
        # Use provided email or custom_user_email
        email = email or employee_doc.custom_user_email
        if not email:
            frappe.throw(_("Please enter Email"))
            
        # Prepare roles list
        roles_to_assign = ["Employee"]  # Always include Employee role
        
        # Add custom roles if specified
        if employee_doc.custom_roles:
            custom_roles = employee_doc.custom_roles.split(',') if isinstance(employee_doc.custom_roles, str) else [employee_doc.custom_roles]
            for role in custom_roles:
                role = role.strip()
                if role and frappe.db.exists("Role", role) and role not in roles_to_assign:
                    roles_to_assign.append(role)
        
        # Check if user already exists
        if frappe.db.exists("User", email):
            existing_user = frappe.get_doc("User", email)
            
            # First update employee link
            employee_doc.db_set('user_id', email, update_modified=False)
            frappe.db.commit()
            
            # Then update roles
            existing_roles = [r.role for r in existing_user.roles]
            for role in roles_to_assign:
                if role not in existing_roles:
                    existing_user.append("roles", {"role": role})
            
            # Set module_profile to "Default Module"
            existing_user.module_profile = "Default Module"
            
            existing_user.save(ignore_permissions=True)
            frappe.db.commit()
            
            frappe.msgprint(_("User {0} updated with roles: {1} and Default Module profile").format(
                email, ", ".join(roles_to_assign)
            ))
            
            return existing_user
        
        # First set the user_id in employee to prevent role removal message
        employee_doc.db_set('user_id', email, update_modified=False)
        frappe.db.commit()
        
        # Use provided password or set default password to "admin@123"
        user_password = password if password else "admin@123"
        
        # Create new user with roles
        user = frappe.get_doc({
            "doctype": "User",
            "email": email,
            "first_name": employee_doc.first_name,
            "middle_name": employee_doc.middle_name,
            "last_name": employee_doc.last_name,
            "enabled": 1,
            "user_type": "System User",
            "send_welcome_email": 0,
            "new_password": user_password,
            "module_profile": "Default Module",  # Set module_profile to "Default Module"
            "roles": [{"role": role} for role in roles_to_assign]
        })
        
        user.flags.ignore_permissions = True
        user.flags.no_welcome_mail = True
        user.insert()
        
        # Commit changes
        frappe.db.commit()
        
        # Only send welcome email if we're using the default password
        if not password:
            try:
                user.send_welcome_mail()
                frappe.msgprint(_("Welcome email sent to {0} with default password (admin@123)").format(email))
            except Exception as mail_error:
                frappe.log_error(f"Failed to send welcome email: {str(mail_error)}", "Welcome Email Error")
                frappe.msgprint(_("User created with default password (admin@123) but welcome email could not be sent. Please check email settings."))
        else:
            frappe.msgprint(_("User created with custom password. No welcome email sent."))
        
        # Verify and report final status
        user.reload()
        final_roles = [r.role for r in user.roles]
        frappe.msgprint(_("User {0} created successfully with roles: {1} and Default Module profile").format(
            email, ", ".join(final_roles)
        ))
        
        return user
        
    except Exception as e:
        frappe.log_error(
            f"Error in user creation for employee {employee}: {str(e)}\n{frappe.get_traceback()}",
            "User Creation Error"
        )
        frappe.throw(_("Error creating user: {0}").format(str(e)))

@frappe.whitelist()
def reset_user_password(employee, password):
    """
    Reset password for the user linked to the specified employee
    """
    if not employee:
        frappe.throw(_("Please specify Employee"))
        
    if not password:
        frappe.throw(_("Please specify new password"))
        
    try:
        # Get employee document
        employee_doc = frappe.get_doc("Employee", employee)
        
        # Check if employee has a linked user
        if not employee_doc.user_id:
            frappe.throw(_("No user linked to this employee"))
        
        # Check if user exists
        if not frappe.db.exists("User", employee_doc.user_id):
            frappe.throw(_("Linked user {0} does not exist").format(employee_doc.user_id))
            
        # Get user document
        user = frappe.get_doc("User", employee_doc.user_id)
        
        # Update password
        user.new_password = password
        user.save(ignore_permissions=True)
        frappe.db.commit()
        
        return {"success": True, "message": _("Password updated successfully")}
        
    except Exception as e:
        frappe.log_error(
            f"Error in password reset for employee {employee}: {str(e)}\n{frappe.get_traceback()}",
            "Password Reset Error"
        )
        frappe.throw(_("Error resetting password: {0}").format(str(e)))