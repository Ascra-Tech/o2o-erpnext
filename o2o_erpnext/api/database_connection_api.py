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


@frappe.whitelist()
def get_connection_details(connection_name):
    """
    Get detailed information about a database connection
    
    Args:
        connection_name (str): Name of the Database Connection
        
    Returns:
        dict: Connection details
    """
    try:
        if not frappe.db.exists("Database Connection", connection_name):
            return {
                'success': False,
                'message': f'Database Connection "{connection_name}" not found'
            }
        
        conn_doc = frappe.get_doc("Database Connection", connection_name)
        
        # Get tunnel status if SSH is enabled
        tunnel_status = None
        if conn_doc.ssh_tunnel:
            tunnel_status = SSHTunnelManager.get_tunnel_status(connection_name)
        
        return {
            'success': True,
            'connection': {
                'name': conn_doc.name,
                'display_name': conn_doc.display_name,
                'database_type': conn_doc.database_type,
                'host': conn_doc.host,
                'port': conn_doc.port,
                'database_name': conn_doc.database_name,
                'username': conn_doc.username,
                'ssh_tunnel': conn_doc.ssh_tunnel,
                'ssh_host': conn_doc.ssh_host if conn_doc.ssh_tunnel else None,
                'ssh_port': conn_doc.ssh_port if conn_doc.ssh_tunnel else None,
                'ssh_username': conn_doc.ssh_username if conn_doc.ssh_tunnel else None,
                'connection_status': conn_doc.connection_status,
                'environment': conn_doc.environment,
                'is_active': conn_doc.is_active,
                'tunnel_status': tunnel_status
            }
        }
        
    except Exception as e:
        frappe.log_error(
            message=f"Get Connection Details Error: {str(e)}\n{traceback.format_exc()}",
            title=f"Get Connection Details Failed - {connection_name}"
        )
        return {
            'success': False,
            'message': str(e)
        }


@frappe.whitelist()
def enhanced_test_connection(connection_name, database_name=None, port=None, test_tables=True, test_write_access=False):
    """
    Enhanced database connection test with customizable options
    
    Args:
        connection_name (str): Name of the Database Connection
        database_name (str): Optional database name override
        port (int): Optional port override
        test_tables (bool): Whether to test table access
        test_write_access (bool): Whether to test write access
        
    Returns:
        dict: Detailed connection test results
    """
    import time
    
    try:
        if not frappe.db.exists("Database Connection", connection_name):
            return {
                'success': False,
                'message': f'Database Connection "{connection_name}" not found'
            }
        
        conn_doc = frappe.get_doc("Database Connection", connection_name)
        
        # Use provided values or defaults from connection
        db_name = database_name or conn_doc.database_name
        db_port = int(port) if port else conn_doc.port
        db_host = conn_doc.host
        db_user = conn_doc.username
        db_password = conn_doc.get_password('password')
        
        # For SSH connections, use tunnel
        if conn_doc.ssh_tunnel:
            tunnel_status = SSHTunnelManager.get_tunnel_status(connection_name)
            if tunnel_status['is_connected']:
                db_host = '127.0.0.1'
                db_port = tunnel_status['local_port']
            else:
                return {
                    'success': False,
                    'message': 'SSH tunnel is not active. Please start the tunnel first.'
                }
        
        # Test connection
        connection = None
        start_time = time.time()
        
        # Debug logging
        password_length = len(db_password) if db_password else 0
        frappe.log_error(
            message=f"Connection attempt with: host={db_host}, port={db_port}, user={db_user}, database={db_name}, ssl_required={conn_doc.ssl_required}, password_length={password_length}",
            title=f"Debug Connection Parameters - {connection_name}"
        )
        
        # Test the exact same connection that works directly
        if db_host == 'o2oproddb.cwjwq8yhqpn1.ap-south-1.rds.amazonaws.com' and db_user == 'o2oapp':
            frappe.log_error(
                message=f"Testing with hardcoded password for comparison",
                title=f"Debug Password Test - {connection_name}"
            )
            # Try with hardcoded password that we know works
            test_password = 'o2oapp4321'
            try:
                test_conn = pymysql.connect(
                    host=db_host,
                    port=db_port,
                    user=db_user,
                    password=test_password,
                    database=db_name,
                    charset='utf8mb4',
                    connect_timeout=10,
                    ssl_disabled=True
                )
                test_conn.close()
                frappe.log_error(
                    message=f"Hardcoded password test: SUCCESS",
                    title=f"Debug Password Test - {connection_name}"
                )
            except Exception as test_e:
                frappe.log_error(
                    message=f"Hardcoded password test: FAILED - {test_e}",
                    title=f"Debug Password Test - {connection_name}"
                )
        
        try:
            # Build connection parameters
            conn_params = {
                'host': db_host,
                'port': db_port,
                'user': db_user,
                'password': db_password,
                'database': db_name,
                'charset': 'utf8mb4',
                'cursorclass': pymysql.cursors.DictCursor,
                'connect_timeout': 10
            }
            
            # Only add SSL parameters if SSL is required
            if conn_doc.ssl_required:
                conn_params['ssl'] = {'ssl_disabled': False}
            else:
                conn_params['ssl_disabled'] = True
            
            connection = pymysql.connect(**conn_params)
            
            connection_time = int((time.time() - start_time) * 1000)
            
            with connection.cursor() as cursor:
                # Get database info
                cursor.execute("SELECT VERSION() as version, DATABASE() as db_name, USER() as user_name")
                db_info = cursor.fetchone()
                
                # Get table count and sample tables
                table_count = 0
                sample_tables = []
                
                if test_tables:
                    cursor.execute("SHOW TABLES")
                    tables = cursor.fetchall()
                    table_count = len(tables)
                    sample_tables = [list(t.values())[0] for t in tables[:10]]
                
                # Test write access
                write_test = False
                if test_write_access:
                    try:
                        cursor.execute("CREATE TABLE IF NOT EXISTS _test_write_access (id INT)")
                        cursor.execute("DROP TABLE _test_write_access")
                        write_test = True
                    except:
                        write_test = False
            
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
            
            return {
                'success': True,
                'message': 'Database connection successful',
                'details': {
                    'version': db_info.get('version'),
                    'database': db_info.get('db_name'),
                    'user': db_info.get('user_name'),
                    'host': db_host,
                    'port': db_port,
                    'table_count': table_count,
                    'sample_tables': sample_tables,
                    'connection_time': connection_time,
                    'write_test': write_test,
                    'local_port': db_port if conn_doc.ssh_tunnel else None
                }
            }
            
        except Exception as db_error:
            error_msg = str(db_error)
            
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
            message=f"Enhanced Test Connection Error: {str(e)}\n{traceback.format_exc()}",
            title=f"Enhanced Test Failed - {connection_name}"
        )
        return {
            'success': False,
            'message': str(e)
        }

