"""
Database Connection API
Provides API endpoints for SSH tunnel management and database connection testing
"""

import frappe
from frappe import _
import pymysql
import traceback
from o2o_erpnext.config.ssh_tunnel_manager import SSHTunnelManager


@frappe.whitelist()
def start_ssh_tunnel(connection_name):
    """
    Start SSH tunnel for a database connection
    
    Args:
        connection_name (str): Name of the Database Connection
        
    Returns:
        dict: Success status and tunnel details
    """
    try:
        result = SSHTunnelManager.start_tunnel(connection_name)
        
        if result['success']:
            frappe.msgprint(
                _('SSH Tunnel started successfully'),
                title=_('Success'),
                indicator='green'
            )
        
        return result
        
    except Exception as e:
        frappe.log_error(
            message=f"Start SSH Tunnel Error: {str(e)}\n{traceback.format_exc()}",
            title=f"SSH Tunnel Start Failed - {connection_name}"
        )
        return {
            'success': False,
            'message': str(e)
        }


@frappe.whitelist()
def stop_ssh_tunnel(connection_name):
    """
    Stop SSH tunnel for a database connection
    
    Args:
        connection_name (str): Name of the Database Connection
        
    Returns:
        dict: Success status
    """
    try:
        result = SSHTunnelManager.stop_tunnel(connection_name)
        
        if result['success']:
            frappe.msgprint(
                _('SSH Tunnel stopped successfully'),
                title=_('Success'),
                indicator='orange'
            )
        
        return result
        
    except Exception as e:
        frappe.log_error(
            message=f"Stop SSH Tunnel Error: {str(e)}\n{traceback.format_exc()}",
            title=f"SSH Tunnel Stop Failed - {connection_name}"
        )
        return {
            'success': False,
            'message': str(e)
        }


@frappe.whitelist()
def get_ssh_tunnel_status(connection_name):
    """
    Get current status of SSH tunnel
    
    Args:
        connection_name (str): Name of the Database Connection
        
    Returns:
        dict: Tunnel status information
    """
    try:
        status = SSHTunnelManager.get_tunnel_status(connection_name)
        return {
            'success': True,
            'status': status
        }
        
    except Exception as e:
        frappe.log_error(
            message=f"Get SSH Tunnel Status Error: {str(e)}\n{traceback.format_exc()}",
            title=f"Get Tunnel Status Failed - {connection_name}"
        )
        return {
            'success': False,
            'message': str(e)
        }


@frappe.whitelist()
def get_all_ssh_connections():
    """
    Get all database connections that have SSH tunnel enabled
    
    Returns:
        dict: List of connections with their status
    """
    try:
        connections = frappe.get_all(
            'Database Connection',
            filters={'ssh_tunnel': 1},
            fields=['name', 'display_name', 'connection_status', 'database_type', 
                    'host', 'database_name', 'is_active', 'environment']
        )
        
        # Get status for each connection
        for conn in connections:
            status = SSHTunnelManager.get_tunnel_status(conn['name'])
            conn['tunnel_status'] = status
        
        return {
            'success': True,
            'connections': connections
        }
        
    except Exception as e:
        frappe.log_error(
            message=f"Get All SSH Connections Error: {str(e)}\n{traceback.format_exc()}",
            title="Get SSH Connections Failed"
        )
        return {
            'success': False,
            'message': str(e)
        }


@frappe.whitelist()
def test_database_connection(connection_name):
    """
    Test database connection through SSH tunnel
    
    Args:
        connection_name (str): Name of the Database Connection
        
    Returns:
        dict: Connection test results
    """
    try:
        # Get Database Connection document
        if not frappe.db.exists("Database Connection", connection_name):
            return {
                'success': False,
                'message': f'Database Connection "{connection_name}" not found'
            }
        
        conn_doc = frappe.get_doc("Database Connection", connection_name)
        
        # Get tunnel status
        tunnel_status = SSHTunnelManager.get_tunnel_status(connection_name)
        
        if not tunnel_status['is_connected']:
            return {
                'success': False,
                'message': 'SSH tunnel is not active. Please start the tunnel first.'
            }
        
        # Get connection details
        local_port = tunnel_status['local_port']
        db_user = conn_doc.username
        db_password = conn_doc.get_password('password')
        db_name = conn_doc.database_name
        
        if not db_user:
            return {
                'success': False,
                'message': 'Database username not configured'
            }
        
        # Test database connection
        connection = None
        try:
            connection = pymysql.connect(
                host='127.0.0.1',
                port=local_port,
                user=db_user,
                password=db_password,
                database=db_name,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor,
                connect_timeout=10
            )
            
            with connection.cursor() as cursor:
                cursor.execute("SELECT VERSION() as version, DATABASE() as db_name, USER() as user_name")
                db_info = cursor.fetchone()
                
                # Get table count
                cursor.execute("SHOW TABLES")
                tables = cursor.fetchall()
                table_count = len(tables)
            
            # Update connection status
            frappe.db.set_value(
                'Database Connection',
                connection_name,
                {
                    'connection_status': 'Connected',
                    'last_connected': frappe.utils.now_datetime(),
                    'error_log': None
                },
                update_modified=False
            )
            frappe.db.commit()
            
            frappe.msgprint(
                _('Database connection successful!'),
                title=_('Success'),
                indicator='green'
            )
            
            return {
                'success': True,
                'message': 'Database connection successful',
                'details': {
                    'version': db_info.get('version'),
                    'database': db_info.get('db_name'),
                    'user': db_info.get('user_name'),
                    'table_count': table_count,
                    'local_port': local_port
                }
            }
            
        except Exception as db_error:
            error_msg = str(db_error)
            
            # Update error status
            frappe.db.set_value(
                'Database Connection',
                connection_name,
                {
                    'connection_status': 'Error',
                    'error_log': error_msg
                },
                update_modified=False
            )
            frappe.db.commit()
            
            return {
                'success': False,
                'message': f'Database connection failed: {error_msg}'
            }
            
        finally:
            if connection:
                connection.close()
        
    except Exception as e:
        frappe.log_error(
            message=f"Test Database Connection Error: {str(e)}\n{traceback.format_exc()}",
            title=f"Database Test Failed - {connection_name}"
        )
        return {
            'success': False,
            'message': str(e)
        }


@frappe.whitelist()
def restart_ssh_tunnel(connection_name):
    """
    Restart SSH tunnel (stop and start)
    
    Args:
        connection_name (str): Name of the Database Connection
        
    Returns:
        dict: Success status
    """
    try:
        # Stop tunnel if active
        stop_result = SSHTunnelManager.stop_tunnel(connection_name)
        
        # Wait a moment
        import time
        time.sleep(1)
        
        # Start tunnel
        start_result = SSHTunnelManager.start_tunnel(connection_name)
        
        if start_result['success']:
            frappe.msgprint(
                _('SSH Tunnel restarted successfully'),
                title=_('Success'),
                indicator='green'
            )
        
        return start_result
        
    except Exception as e:
        frappe.log_error(
            message=f"Restart SSH Tunnel Error: {str(e)}\n{traceback.format_exc()}",
            title=f"SSH Tunnel Restart Failed - {connection_name}"
        )
        return {
            'success': False,
            'message': str(e)
        }

