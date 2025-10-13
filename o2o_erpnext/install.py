"""
Installation Script for o2o_erpnext App
Creates predefined Database Connections and performs initial setup
"""

import frappe
from frappe import _


def after_install():
    """
    Called after app installation
    Creates default database connections
    """
    try:
        create_procureuat_connection()
        frappe.db.commit()
        print("✅ o2o_erpnext installation completed successfully")
    except Exception as e:
        frappe.log_error(
            message=f"Installation error: {str(e)}",
            title="o2o_erpnext Installation Failed"
        )
        print(f"❌ Installation error: {str(e)}")


def create_procureuat_connection():
    """
    Create ProcureUAT Database Connection with SSH tunnel settings
    User needs to fill in username and password manually
    """
    try:
        # Check if connection already exists
        if frappe.db.exists("Database Connection", "ProcureUAT"):
            print("ℹ️  ProcureUAT connection already exists, skipping creation")
            return
        
        # Create new Database Connection
        doc = frappe.get_doc({
            'doctype': 'Database Connection',
            'connection_name': 'ProcureUAT',
            'display_name': 'ProcureUAT Database',
            'database_type': 'MySQL',
            'host': '127.0.0.1',
            'port': 3306,
            'database_name': 'procureuat',
            'username': 'FILL_USERNAME_HERE',  # User fills manually
            'password': 'FILL_PASSWORD_HERE',  # User fills manually
            'is_active': 0,
            'environment': 'Production',
            'connection_status': 'Unknown',
            
            # SSH Tunnel Settings
            'ssh_tunnel': 1,
            'ssh_host': '65.0.222.210',  # Correct remote server IP
            'ssh_port': 22,
            'ssh_username': 'ubuntu',
            # Note: SSH key should be attached manually using the 'Secure Key' field
            
            # Sync Settings
            'full_duplex_sync': 1,
            'frappe_to_external': 1,
            '3rd_party_to_frappe': 1,
            
            # SSL
            'ssl_required': 0,
            'vpn_connection': 0
        })
        
        doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
        
        print("✅ Created ProcureUAT Database Connection")
        print("⚠️  ACTION REQUIRED:")
        print("   1. Update Username: Replace 'FILL_USERNAME_HERE' with 'frappeo2o'")
        print("   2. Update Password: Set your actual database password")
        print("   3. Attach SSH Key: Click 'Secure Key' field and attach your .pem file")
        
    except Exception as e:
        frappe.log_error(
            message=f"Failed to create ProcureUAT connection: {str(e)}",
            title="ProcureUAT Connection Creation Failed"
        )
        print(f"❌ Failed to create ProcureUAT connection: {str(e)}")
        raise

