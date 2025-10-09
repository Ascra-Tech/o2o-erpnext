"""
External Database Connection Module with SSH Tunneling Support
Handles connections to ProcureUAT MySQL database via SSH tunnel
"""

import frappe
import pymysql
import subprocess
import time
import os
import threading
from contextlib import contextmanager
from frappe.utils import get_datetime, now_datetime
from frappe import _

class SSHTunnelManager:
    """Manages SSH tunnel for database connections"""
    
    def __init__(self):
        self.tunnel_process = None
        self.tunnel_active = False
        self.local_port = 3307  # Local port for tunnel
        self.lock = threading.Lock()
        
    def get_connection_config(self, connection_name="ProcureUAT"):
        """Get database connection configuration from Database Connection doctype"""
        try:
            conn_doc = frappe.get_doc("Database Connection", connection_name)
            if not conn_doc.is_active:
                raise frappe.ValidationError(f"Database connection '{connection_name}' is not active")
                
            return {
                'host': conn_doc.host,
                'port': conn_doc.port,
                'database': conn_doc.database_name,
                'username': conn_doc.username,
                'password': conn_doc.get_password('password'),
                'host_ip': conn_doc.host_ip or conn_doc.host
            }
        except frappe.DoesNotExistError:
            frappe.throw(_("Database Connection '{0}' not found. Please create it first.").format(connection_name))
        except Exception as e:
            frappe.throw(_("Error getting database configuration: {0}").format(str(e)))
    
    def get_ssh_config(self):
        """Get SSH configuration for tunnel"""
        # Get the correct path to the PEM file based on our actual location
        pem_file_path = "/home/erpnext/frappe-bench/apps/o2o_erpnext/o2o Research/o2o-uat-lightsail.pem"
        
        if not os.path.exists(pem_file_path):
            frappe.throw(_("SSH key file not found at: {0}").format(pem_file_path))
        
        # Check file permissions (SSH keys need 600 permissions)
        file_stat = os.stat(pem_file_path)
        if oct(file_stat.st_mode)[-3:] != '600':
            frappe.throw(_("SSH key file has incorrect permissions. Run: chmod 600 {0}").format(pem_file_path))
        
        return {
            'ssh_host': '65.0.222.210',
            'ssh_port': 22,
            'ssh_username': 'ubuntu',
            'ssh_key_path': pem_file_path,
            'remote_bind_host': '127.0.0.1',
            'remote_bind_port': 3306
        }
        
        if not os.path.exists(pem_file_path):
            frappe.throw(_("SSH PEM file not found at: {0}").format(pem_file_path))
            
        # Ensure correct permissions
        os.chmod(pem_file_path, 0o400)
        
        return {
            'ssh_host': '65.0.222.210',
            'ssh_user': 'ubuntu',  # Default Lightsail user
            'ssh_key': pem_file_path,
            'remote_host': 'localhost',  # MySQL on remote server
            'remote_port': 3306,
            'local_port': self.local_port
        }
    
    def create_tunnel(self):
        """Create SSH tunnel to remote database"""
        if self.tunnel_active and self.tunnel_process and self.tunnel_process.poll() is None:
            return True
            
        with self.lock:
            try:
                ssh_config = self.get_ssh_config()
                
                # Kill any existing process on the local port
                self._cleanup_port(ssh_config['local_port'])
                
                # Build SSH command
                ssh_cmd = [
                    'ssh',
                    '-i', ssh_config['ssh_key'],
                    '-N',  # No remote command
                    '-o', 'ServerAliveInterval=60',
                    '-o', 'ServerAliveCountMax=3',
                    '-o', 'ExitOnForwardFailure=yes',
                    '-o', 'StrictHostKeyChecking=no',
                    '-L', f"{ssh_config['local_port']}:{ssh_config['remote_host']}:{ssh_config['remote_port']}",
                    f"{ssh_config['ssh_user']}@{ssh_config['ssh_host']}"
                ]
                
                # Start SSH tunnel
                self.tunnel_process = subprocess.Popen(
                    ssh_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    preexec_fn=os.setsid
                )
                
                # Wait a moment for tunnel to establish
                time.sleep(2)
                
                # Check if tunnel is running
                if self.tunnel_process.poll() is None:
                    self.tunnel_active = True
                    frappe.logger().info(f"SSH tunnel established on port {ssh_config['local_port']}")
                    return True
                else:
                    stderr_output = self.tunnel_process.stderr.read().decode()
                    frappe.logger().error(f"SSH tunnel failed: {stderr_output}")
                    return False
                    
            except Exception as e:
                frappe.logger().error(f"Error creating SSH tunnel: {str(e)}")
                self.tunnel_active = False
                return False
    
    def _cleanup_port(self, port):
        """Kill any process using the specified port"""
        try:
            result = subprocess.run(
                ['lsof', '-ti', f':{port}'],
                capture_output=True,
                text=True
            )
            if result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    if pid:
                        subprocess.run(['kill', '-9', pid], capture_output=True)
        except Exception:
            pass  # Ignore errors in cleanup
    
    def close_tunnel(self):
        """Close SSH tunnel"""
        with self.lock:
            if self.tunnel_process:
                try:
                    # Terminate the process group
                    os.killpg(os.getpgid(self.tunnel_process.pid), 15)
                    time.sleep(1)
                    
                    # Force kill if still running
                    if self.tunnel_process.poll() is None:
                        os.killpg(os.getpgid(self.tunnel_process.pid), 9)
                        
                except Exception as e:
                    frappe.logger().error(f"Error closing SSH tunnel: {str(e)}")
                finally:
                    self.tunnel_process = None
                    self.tunnel_active = False
    
    def is_tunnel_active(self):
        """Check if tunnel is active"""
        if not self.tunnel_process:
            return False
        return self.tunnel_process.poll() is None

# Global tunnel manager instance
tunnel_manager = SSHTunnelManager()

@contextmanager
def get_external_db_connection(connection_name="ProcureUAT", use_ssh_tunnel=True):
    """
    Context manager for external database connections with SSH tunneling
    
    Args:
        connection_name (str): Name of the Database Connection record
        use_ssh_tunnel (bool): Whether to use SSH tunnel for connection
        
    Yields:
        pymysql.Connection: Database connection object
    """
    connection = None
    
    try:
        # Get connection configuration
        config = tunnel_manager.get_connection_config(connection_name)
        
        if use_ssh_tunnel:
            # Create SSH tunnel
            if not tunnel_manager.create_tunnel():
                raise frappe.ValidationError("Failed to establish SSH tunnel")
            
            # Use tunnel for connection
            host = '127.0.0.1'
            port = tunnel_manager.local_port
        else:
            # Direct connection
            host = config['host_ip']
            port = config['port']
        
        # Create database connection
        connection = pymysql.connect(
            host=host,
            port=port,
            user=config['username'],
            password=config['password'],
            database=config['database'],
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True
        )
        
        # Test connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 as test")
            result = cursor.fetchone()
            if not result or result.get('test') != 1:
                raise frappe.ValidationError("Database connection test failed")
        
        # Update connection status
        update_connection_status(connection_name, "Connected", None)
        
        yield connection
        
    except Exception as e:
        error_msg = str(e)
        frappe.logger().error(f"Database connection error: {error_msg}")
        update_connection_status(connection_name, "Error", error_msg)
        raise
        
    finally:
        if connection:
            try:
                connection.close()
            except Exception:
                pass

def update_connection_status(connection_name, status, error_log=None):
    """Update Database Connection status"""
    try:
        conn_doc = frappe.get_doc("Database Connection", connection_name)
        conn_doc.connection_status = status
        conn_doc.last_connected = now_datetime()
        if error_log:
            conn_doc.error_log = error_log
        conn_doc.save(ignore_permissions=True)
        frappe.db.commit()
    except Exception:
        pass  # Don't fail if we can't update status

def test_external_connection(connection_name="ProcureUAT", use_ssh_tunnel=True):
    """
    Test external database connection
    
    Args:
        connection_name (str): Name of the Database Connection record
        use_ssh_tunnel (bool): Whether to use SSH tunnel
        
    Returns:
        dict: Test results with status and message
    """
    try:
        with get_external_db_connection(connection_name, use_ssh_tunnel) as conn:
            with conn.cursor() as cursor:
                # Test basic connectivity
                cursor.execute("SELECT VERSION() as version, NOW() as current_time")
                result = cursor.fetchone()
                
                # Test procureuat database access
                cursor.execute("SHOW TABLES LIKE 'invoices'")
                invoices_table = cursor.fetchone()
                
                cursor.execute("SHOW TABLES LIKE 'vendors'")
                vendors_table = cursor.fetchone()
                
                return {
                    'status': 'success',
                    'message': 'Database connection successful',
                    'data': {
                        'mysql_version': result.get('version'),
                        'current_time': str(result.get('current_time')),
                        'invoices_table_exists': bool(invoices_table),
                        'vendors_table_exists': bool(vendors_table),
                        'tunnel_used': use_ssh_tunnel,
                        'tunnel_active': tunnel_manager.is_tunnel_active() if use_ssh_tunnel else False
                    }
                }
                
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Database connection failed: {str(e)}',
            'data': {
                'tunnel_used': use_ssh_tunnel,
                'tunnel_active': tunnel_manager.is_tunnel_active() if use_ssh_tunnel else False
            }
        }

def close_all_tunnels():
    """Close all SSH tunnels - cleanup function"""
    tunnel_manager.close_tunnel()

# Cleanup on module exit
import atexit
atexit.register(close_all_tunnels)