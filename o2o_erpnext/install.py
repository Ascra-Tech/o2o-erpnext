"""
Installation Script for o2o_erpnext App
Creates predefined Database Connections for both staging and production
"""

import frappe
from frappe import _


def after_install():
    """
    Called after app installation
    Creates default database connections for both environments
    """
    try:
        create_procureuat_staging_connection()
        create_procureuat_production_connection()
        frappe.db.commit()
        print("✅ o2o_erpnext installation completed successfully")
        print_post_installation_instructions()
    except Exception as e:
        frappe.log_error(
            message=f"Installation error: {str(e)}",
            title="o2o_erpnext Installation Failed"
        )
        print(f"❌ Installation error: {str(e)}")


def create_procureuat_staging_connection():
    """
    Create ProcureUAT Staging Database Connection with SSH tunnel settings
    """
    try:
        connection_name = "ProcureUAT_Staging"
        
        # Check if connection already exists
        if frappe.db.exists("Database Connection", connection_name):
            print(f"ℹ️  {connection_name} connection already exists, skipping creation")
            return
        
        # Create staging Database Connection (SSH tunnel)
        doc = frappe.get_doc({
            'doctype': 'Database Connection',
            'connection_name': connection_name,
            'display_name': 'ProcureUAT Staging (SSH Tunnel)',
            'database_type': 'MySQL',
            'host': '127.0.0.1',  # Through SSH tunnel
            'port': 3306,
            'database_name': 'procureuat',
            'username': 'frappeo2o',
            'password': 'FILL_STAGING_PASSWORD_HERE',
            'is_active': 0,  # Inactive by default
            'environment': 'Staging',
            'connection_status': 'Unknown',
            
            # SSH Tunnel Settings
            'ssh_tunnel': 1,
            'ssh_host': '65.0.222.210',
            'ssh_port': 22,
            'ssh_username': 'ubuntu',
            'ssh_key_file': '/home/erpnext/frappe-bench/apps/o2o_erpnext/o2o-Research/o2o-uat-lightsail.pem',
            
            # Sync Settings
            'full_duplex_sync': 1,
            'frappe_to_external': 1,
            '3rd_party_to_frappe': 1,
            
            # SSL
            'ssl_required': 0,
            'vpn_connection': 0
        })
        
        doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
        print(f"✅ Created {connection_name} Database Connection")
        
    except Exception as e:
        frappe.log_error(
            message=f"Failed to create staging connection: {str(e)}",
            title="Staging Connection Creation Failed"
        )
        print(f"❌ Failed to create staging connection: {str(e)}")
        raise


def create_procureuat_production_connection():
    """
    Create ProcureUAT Production Database Connection for MySQL RDS with IAM Authentication
    """
    try:
        connection_name = "ProcureUAT_Production"
        
        # Check if connection already exists
        if frappe.db.exists("Database Connection", connection_name):
            print(f"ℹ️  {connection_name} connection already exists, skipping creation")
            return
        
        # Create production Database Connection (MySQL RDS)
        doc = frappe.get_doc({
            'doctype': 'Database Connection',
            'connection_name': connection_name,
            'display_name': 'ProcureUAT Production (MySQL RDS)',
            'database_type': 'MySQL',
            'host': 'o2oproddb.cwjwq8yhqpn1.ap-south-1.rds.amazonaws.com',
            'port': 4406,
            'database_name': 'procureprod',
            'username': 'o2oapp',
            'password': 'o2oapp4321',
            'is_active': 0,  # Inactive by default
            'environment': 'Production',
            'connection_status': 'Unknown',
            
            # No SSH Tunnel for MySQL RDS
            'ssh_tunnel': 0,
            'ssh_host': '',
            'ssh_port': 22,
            'ssh_username': '',
            'ssh_key_file': '',
            
            # Sync Settings
            'full_duplex_sync': 1,
            'frappe_to_external': 1,
            '3rd_party_to_frappe': 1,
            
            # SSL not required for existing setup
            'ssl_required': 0,
            'vpn_connection': 0
        })
        
        doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
        print(f"✅ Created {connection_name} Database Connection with existing credentials")
        
    except Exception as e:
        frappe.log_error(
            message=f"Failed to create production connection: {str(e)}",
            title="Production Connection Creation Failed"
        )
        print(f"❌ Failed to create production connection: {str(e)}")
        raise


def print_post_installation_instructions():
    """
    Print instructions for manual configuration steps
    """
    print("\n" + "="*60)
    print("📋 POST-INSTALLATION CONFIGURATION REQUIRED")
    print("="*60)
    
    print("\n🔧 STAGING CONNECTION (ProcureUAT_Staging):")
    print("   1. Update Password: Replace 'FILL_STAGING_PASSWORD_HERE'")
    print("   2. Verify SSH Key Path: Ensure .pem file exists and has 600 permissions")
    print("   3. Test Connection: Use 'Test Connection' button")
    
    print("\n🚀 PRODUCTION CONNECTION (ProcureUAT_Production):")
    print("   1. ✅ Database Credentials: Pre-configured with existing 'o2oapp' user")
    print("   2. ✅ Connection Details: Host, port (4406), and database (procureprod)")
    print("   3. ✅ VPC Security Groups: Configured for production server 13.202.254.92")
    print("   4. ✅ SSL: Disabled to match existing setup")
    print("   5. Test Connection: Use 'Test Connection' button")
    
    print("\n⚙️  ENVIRONMENT ACTIVATION:")
    print("   • Activate appropriate connection based on your environment")
    print("   • Only one connection should be active at a time")
    
    print("\n🔍 VERIFICATION:")
    print("   • Go to: Database Connection list")
    print("   • Test connections before enabling sync")
    print("   • Production connection should work immediately with existing credentials")
    print("="*60)


# Legacy function for backward compatibility
def create_procureuat_connection():
    """
    Legacy function - now creates staging connection
    Maintained for backward compatibility
    """
    return create_procureuat_staging_connection()

