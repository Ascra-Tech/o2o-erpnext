import frappe
from frappe.utils import validate_email_address
from frappe import _

def get_user_linked_supplier(user):
    """Helper function to get supplier linked to user"""
    # Check if user has supplier role
    user_roles = frappe.get_roles(user)
    if 'Supplier' in user_roles:
        # Get supplier linked to user
        suppliers = frappe.get_all('Supplier',
            filters={'custom_user': user},
            fields=['name'],
            limit=1
        )
        if suppliers:
            return suppliers[0].name
    return None

def before_validate(doc, method=None):
    """Set custom_supplier based on user role before validation"""
    user = frappe.session.user
    if user:
        # Get user's roles
        user_roles = frappe.get_roles(user)
        
        # If user has Supplier role
        if 'Supplier' in user_roles:
            # Get linked supplier
            suppliers = frappe.get_all('Supplier',
                filters={'custom_user': user},
                fields=['name'],
                limit=1
            )
            
            if suppliers:
                # Set custom_supplier field
                doc.custom_supplier = suppliers[0].name
                
                # Debug log
                frappe.logger().debug(f"Setting custom_supplier to {doc.custom_supplier} for user {user}")

def validate_employee(doc, method=None):
    """Validates employee document"""
    if doc.custom_sub_branch:
        # Check if the sub branch exists
        if not frappe.db.exists("Sub Branch", doc.custom_sub_branch):
            frappe.throw(_("Sub Branch {0} does not exist").format(doc.custom_sub_branch))
            
    # Validate supplier for supplier role users
    user = frappe.session.user
    user_roles = frappe.get_roles(user)
    
    if 'Supplier' in user_roles:
        # Get linked supplier
        linked_supplier = get_user_linked_supplier(user)
        if linked_supplier and doc.custom_supplier != linked_supplier:
            frappe.throw(_("As a supplier user, you can only use your linked supplier"))

def create_user_for_employee(doc, method=None):
    """Creates a new user when a new employee is created"""
    if hasattr(doc, '_user_created'):
        return

    if not doc.custom_user_email:
        return

    try:
        validate_email_address(doc.custom_user_email, throw=True)
    except frappe.InvalidEmailAddressError:
        frappe.throw("Please enter a valid email address in Custom User Email")

    if frappe.db.exists("User", doc.custom_user_email):
        frappe.msgprint(f"User already exists with email {doc.custom_user_email}")
        return

    try:
        user = frappe.get_doc({
            "doctype": "User",
            "email": doc.custom_user_email,
            "first_name": doc.first_name,
            "last_name": doc.last_name or "",
            "enabled": 1,
            "user_type": "System User",
            "send_welcome_email": 0
        })

        if doc.custom_roles:
            roles = doc.custom_roles.split(',') if isinstance(doc.custom_roles, str) else [doc.custom_roles]
            for role in roles:
                role = role.strip()
                if role and frappe.db.exists("Role", role):
                    user.append("roles", {
                        "role": role
                    })

        user.insert(ignore_permissions=True)
        frappe.db.set_value('Employee', doc.name, 'user_id', user.name, update_modified=False)
        doc._user_created = True
        frappe.msgprint(f"User {doc.custom_user_email} created and linked to employee")

    except Exception as e:
        error_msg = str(e)[:900]
        frappe.log_error(
            message=f"Failed to create user for employee {doc.name}: {error_msg}",
            title="User Creation Error"
        )
        frappe.throw(f"Failed to create user: {error_msg}", title="Error")