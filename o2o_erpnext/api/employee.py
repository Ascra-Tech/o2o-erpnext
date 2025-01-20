import frappe
from frappe import _
from frappe.utils import random_string

@frappe.whitelist()
def create_user(employee, email=None):
    """
    Create user for employee with clean role assignment
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
            
            existing_user.save(ignore_permissions=True)
            frappe.db.commit()
            
            frappe.msgprint(_("User {0} updated with roles: {1}").format(
                email, ", ".join(roles_to_assign)
            ))
            return existing_user

        # First set the user_id in employee to prevent role removal message
        employee_doc.db_set('user_id', email, update_modified=False)
        frappe.db.commit()

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
            "new_password": random_string(10),
            "roles": [{"role": role} for role in roles_to_assign]
        })

        user.flags.ignore_permissions = True
        user.flags.no_welcome_mail = True
        user.insert()
        
        # Commit changes
        frappe.db.commit()
        
        # Try to send welcome email
        try:
            user.send_welcome_mail()
            frappe.msgprint(_("Welcome email sent to {0}").format(email))
        except Exception as mail_error:
            frappe.log_error(f"Failed to send welcome email: {str(mail_error)}", "Welcome Email Error")
            frappe.msgprint(_("User created but welcome email could not be sent. Please check email settings."))
        
        # Verify and report final status
        user.reload()
        final_roles = [r.role for r in user.roles]
        frappe.msgprint(_("User {0} created successfully with roles: {1}").format(
            email, ", ".join(final_roles)
        ))
        
        return user
        
    except Exception as e:
        frappe.log_error(
            f"Error in user creation for employee {employee}: {str(e)}\n{frappe.get_traceback()}",
            "User Creation Error"
        )
        frappe.throw(_("Error creating user: {0}").format(str(e)))