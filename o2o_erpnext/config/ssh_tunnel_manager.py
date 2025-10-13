"""
SSH Tunnel Manager Module
Provides persistent SSH tunnel management for Database Connections
Maintains active tunnels in a global registry
"""

import frappe
from frappe import _
from sshtunnel import SSHTunnelForwarder
import os
from datetime import datetime
import threading

# Global registry to store active tunnels
_active_tunnels = {}
_tunnel_lock = threading.Lock()


class SSHTunnelManager:
    """Manages persistent SSH tunnels for database connections"""
    
    @staticmethod
    def start_tunnel(connection_name):
        """
        Start SSH tunnel for a database connection
        
        Args:
            connection_name (str): Name of the Database Connection
            
        Returns:
            dict: Status with success, message, and tunnel details
        """
        try:
            # Get Database Connection document
            if not frappe.db.exists("Database Connection", connection_name):
                return {
                    'success': False,
                    'message': f'Database Connection "{connection_name}" not found'
                }
            
            conn_doc = frappe.get_doc("Database Connection", connection_name)
            
            # Validate SSH tunnel is enabled
            if not conn_doc.ssh_tunnel:
                return {
                    'success': False,
                    'message': 'SSH Tunnel is not enabled for this connection'
                }
            
            # Check if tunnel already exists and is active
            with _tunnel_lock:
                if connection_name in _active_tunnels:
                    tunnel_info = _active_tunnels[connection_name]
                    if tunnel_info['tunnel'].is_active:
                        return {
                            'success': True,
                            'message': 'Tunnel already active',
                            'status': SSHTunnelManager.get_tunnel_status(connection_name)
                        }
                    else:
                        # Clean up dead tunnel
                        SSHTunnelManager._cleanup_tunnel(connection_name)
            
            # Validate SSH settings
            ssh_host = conn_doc.get('ssh_host') or '127.0.0.1'
            ssh_port = conn_doc.get('ssh_port') or 22
            ssh_username = conn_doc.get('ssh_username')
            ssh_key_file = conn_doc.get('secure_key')  # Using existing secure_key field (Attach type)
            
            if not ssh_username:
                return {
                    'success': False,
                    'message': 'SSH username not configured'
                }
            
            if not ssh_key_file:
                return {
                    'success': False,
                    'message': 'SSH key file not attached. Please attach the key file in the "Secure Key" field.'
                }
            
            # Get the full file path from the attached file
            # Frappe stores attached files, we need to resolve to absolute path
            if ssh_key_file.startswith('/files/') or ssh_key_file.startswith('/private/files/'):
                # Remove leading slash and get the bench path
                bench_path = frappe.utils.get_bench_path()
                site_name = frappe.local.site
                
                # Build the full path: bench_path/sites/site_name/public/files/filename
                if ssh_key_file.startswith('/private/files/'):
                    # Private file
                    file_relative = ssh_key_file.replace('/private/files/', '')
                    ssh_key_file = os.path.join(bench_path, 'sites', site_name, 'private', 'files', file_relative)
                else:
                    # Public file
                    file_relative = ssh_key_file.replace('/files/', '')
                    ssh_key_file = os.path.join(bench_path, 'sites', site_name, 'public', 'files', file_relative)
            elif not ssh_key_file.startswith('/'):
                # If it's just a filename, assume it's in public files
                bench_path = frappe.utils.get_bench_path()
                site_name = frappe.local.site
                ssh_key_file = os.path.join(bench_path, 'sites', site_name, 'public', 'files', ssh_key_file)
            
            # Check if SSH key file exists
            if not os.path.exists(ssh_key_file):
                return {
                    'success': False,
                    'message': f'SSH key file not found: {ssh_key_file}'
                }
            
            # Check and fix SSH key file permissions
            file_stat = os.stat(ssh_key_file)
            current_permissions = oct(file_stat.st_mode)[-3:]
            if current_permissions != '600':
                frappe.logger().info(f"SSH key has permissions {current_permissions}, fixing to 600: {ssh_key_file}")
                try:
                    os.chmod(ssh_key_file, 0o600)
                    frappe.logger().info(f"SSH key permissions fixed to 600: {ssh_key_file}")
                except Exception as perm_error:
                    frappe.logger().warning(f"Could not fix SSH key permissions: {str(perm_error)}")
                    # Continue anyway, as it might still work
            
            # Get database connection details
            db_host = conn_doc.host or '127.0.0.1'
            db_port = conn_doc.port or 3306
            
            # Create SSH tunnel
            tunnel = SSHTunnelForwarder(
                (ssh_host, ssh_port),
                ssh_username=ssh_username,
                ssh_pkey=ssh_key_file,
                remote_bind_address=(db_host, db_port),
                local_bind_address=('127.0.0.1', 0)  # Use random available port
            )
            
            # Start tunnel
            tunnel.start()
            local_port = tunnel.local_bind_port
            
            # Store tunnel info in registry
            with _tunnel_lock:
                _active_tunnels[connection_name] = {
                    'tunnel': tunnel,
                    'connection_name': connection_name,
                    'local_port': local_port,
                    'started_at': datetime.now(),
                    'ssh_host': ssh_host,
                    'ssh_port': ssh_port,
                    'db_host': db_host,
                    'db_port': db_port
                }
            
            # Update Database Connection status
            frappe.db.set_value(
                'Database Connection',
                connection_name,
                {
                    'connection_status': 'Connected',
                    'last_connected': datetime.now(),
                    'tunnel_status': frappe.as_json({
                        'local_port': local_port,
                        'started_at': str(datetime.now())
                    })
                },
                update_modified=False
            )
            frappe.db.commit()
            
            frappe.logger().info(f"SSH tunnel started for {connection_name} on local port {local_port}")
            
            return {
                'success': True,
                'message': f'SSH tunnel started successfully on local port {local_port}',
                'status': SSHTunnelManager.get_tunnel_status(connection_name)
            }
            
        except Exception as e:
            error_msg = str(e)
            frappe.logger().error(f"Failed to start SSH tunnel for {connection_name}: {error_msg}")
            
            # Update error status
            try:
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
            except:
                pass
            
            return {
                'success': False,
                'message': f'Failed to start tunnel: {error_msg}'
            }
    
    @staticmethod
    def stop_tunnel(connection_name):
        """
        Stop SSH tunnel for a database connection
        
        Args:
            connection_name (str): Name of the Database Connection
            
        Returns:
            dict: Status with success and message
        """
        try:
            with _tunnel_lock:
                if connection_name not in _active_tunnels:
                    return {
                        'success': False,
                        'message': 'No active tunnel found for this connection'
                    }
                
                tunnel_info = _active_tunnels[connection_name]
                tunnel = tunnel_info['tunnel']
                
                if tunnel.is_active:
                    tunnel.stop()
                
                # Remove from registry
                del _active_tunnels[connection_name]
            
            # Update Database Connection status
            frappe.db.set_value(
                'Database Connection',
                connection_name,
                {
                    'connection_status': 'Disconnected',
                    'tunnel_status': None
                },
                update_modified=False
            )
            frappe.db.commit()
            
            frappe.logger().info(f"SSH tunnel stopped for {connection_name}")
            
            return {
                'success': True,
                'message': 'SSH tunnel stopped successfully'
            }
            
        except Exception as e:
            error_msg = str(e)
            frappe.logger().error(f"Failed to stop SSH tunnel for {connection_name}: {error_msg}")
            return {
                'success': False,
                'message': f'Failed to stop tunnel: {error_msg}'
            }
    
    @staticmethod
    def get_tunnel_status(connection_name):
        """
        Get current status of SSH tunnel
        
        Args:
            connection_name (str): Name of the Database Connection
            
        Returns:
            dict: Tunnel status information
        """
        with _tunnel_lock:
            if connection_name not in _active_tunnels:
                return {
                    'is_connected': False,
                    'local_port': None,
                    'started_at': None,
                    'connection_name': connection_name
                }
            
            tunnel_info = _active_tunnels[connection_name]
            tunnel = tunnel_info['tunnel']
            
            # Check if tunnel is still active
            is_active = tunnel.is_active if tunnel else False
            
            if not is_active:
                # Clean up dead tunnel
                SSHTunnelManager._cleanup_tunnel(connection_name)
                return {
                    'is_connected': False,
                    'local_port': None,
                    'started_at': None,
                    'connection_name': connection_name
                }
            
            return {
                'is_connected': True,
                'local_port': tunnel_info['local_port'],
                'started_at': tunnel_info['started_at'].isoformat(),
                'connection_name': connection_name,
                'ssh_host': tunnel_info.get('ssh_host'),
                'ssh_port': tunnel_info.get('ssh_port'),
                'db_host': tunnel_info.get('db_host'),
                'db_port': tunnel_info.get('db_port')
            }
    
    @staticmethod
    def _cleanup_tunnel(connection_name):
        """Internal method to cleanup a dead tunnel"""
        if connection_name in _active_tunnels:
            try:
                tunnel = _active_tunnels[connection_name]['tunnel']
                if tunnel:
                    tunnel.stop()
            except:
                pass
            del _active_tunnels[connection_name]
    
    @staticmethod
    def get_all_tunnels_status():
        """
        Get status of all active tunnels
        
        Returns:
            list: List of tunnel status dicts
        """
        with _tunnel_lock:
            statuses = []
            for connection_name in list(_active_tunnels.keys()):
                status = SSHTunnelManager.get_tunnel_status(connection_name)
                statuses.append(status)
            return statuses
    
    @staticmethod
    def stop_all_tunnels():
        """Stop all active SSH tunnels"""
        with _tunnel_lock:
            connection_names = list(_active_tunnels.keys())
        
        results = []
        for connection_name in connection_names:
            result = SSHTunnelManager.stop_tunnel(connection_name)
            results.append({
                'connection_name': connection_name,
                'result': result
            })
        
        return results


# Cleanup on module reload/shutdown
def cleanup_on_exit():
    """Cleanup all tunnels on module exit"""
    SSHTunnelManager.stop_all_tunnels()

