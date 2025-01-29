import frappe
from frappe import _
from frappe.utils import random_string

@frappe.whitelist()
def create_vendor_user(vendor):
    """
    Create user for vendor with Vendor User role
    """
    if not vendor:
        frappe.throw(_("Please specify Vendor"))
    
    try:
        # Fetch vendor details using frappe.db directly to avoid controller import
        vendor_data = frappe.db.get_value('Vendor', 
            vendor, 
            ['email_id', 'vendor_name', 'user_id'],
            as_dict=1
        )
        
        if not vendor_data:
            frappe.throw(_("Vendor not found"))
            
        email = vendor_data.email_id
        
        if not email:
            frappe.throw(_("Please enter Email ID"))
        
        # Fixed role for vendor
        roles_to_assign = ["Vendor User"]

        # First check if role exists
        if not frappe.db.exists("Role", "Vendor User"):
            frappe.throw(_("Role 'Vendor User' does not exist. Please create it first."))
        
        # Check if user already exists
        if frappe.db.exists("User", email):
            existing_user = frappe.get_doc("User", email)
            
            # Update vendor's user_id field
            frappe.db.set_value('Vendor', vendor, 'user_id', email, update_modified=False)
            frappe.db.commit()
            
            # Update roles
            existing_roles = [r.role for r in existing_user.roles]
            for role in roles_to_assign:
                if role not in existing_roles:
                    existing_user.append("roles", {"role": role})
            existing_user.save(ignore_permissions=True)
            frappe.db.commit()
            
            frappe.msgprint(_("User {0} updated with role: Vendor User").format(email))
            return existing_user
        
        # Set user_id in vendor
        frappe.db.set_value('Vendor', vendor, 'user_id', email, update_modified=False)
        frappe.db.commit()
        
        # Create new user
        user = frappe.get_doc({
            "doctype": "User",
            "email": email,
            "first_name": vendor_data.vendor_name,
            "enabled": 1,
            "user_type": "System User",
            "send_welcome_email": 0,
            "new_password": random_string(10),
            "roles": [{"role": "Vendor User"}]
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
        
        frappe.msgprint(_("User {0} created successfully with role: Vendor User").format(email))
        return user
        
    except Exception as e:
        frappe.log_error(
            f"Error in user creation for vendor {vendor}: {str(e)}\n{frappe.get_traceback()}",
            "Vendor User Creation Error"
        )
        frappe.throw(_("Error creating user: {0}").format(str(e)))