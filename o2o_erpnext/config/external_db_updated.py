"""
Updated External Database Connection Module for ProcureUAT
Uses actual database credentials and SSH tunnel configuration
Based on real procureuat.sql schema analysis
"""

import frappe
import pymysql
from sshtunnel import SSHTunnelForwarder
import os
from contextlib import contextmanager
from frappe import _

# Database connection settings (from actual working connection)
PROCUREUAT_CONFIG = {
    'ssh_host': '65.0.222.210',
    'ssh_port': 22,
    'ssh_username': 'ubuntu',
    'ssh_key_path': '/home/erpnext/frappe-bench/apps/o2o_erpnext/o2o-Research/o2o-uat-lightsail.pem',
    'db_host': '127.0.0.1',  # On remote server
    'db_port': 3306,
    'db_username': 'frappeo2o', 
    'db_password': 'Reppyq-pijry0-fyktyq',
    'db_name': 'procureuat'
}

def get_active_database_connection():
    """
    Get the active Database Connection from ERPNext
    
    Returns:
        dict: Active database connection configuration
    """
    try:
        # Get active database connection
        active_conn = frappe.get_all(
            'Database Connection',
            filters={'is_active': 1},
            fields=['name', 'display_name', 'database_type', 'host', 'port', 'database_name', 
                   'username', 'ssh_tunnel', 'ssh_host', 'ssh_port', 'ssh_username', 'ssh_key_file'],
            limit=1
        )
        
        if not active_conn:
            raise frappe.ValidationError("No active Database Connection found. Please activate a connection in Database Connection list.")
        
        conn_doc = frappe.get_doc('Database Connection', active_conn[0]['name'])
        password = conn_doc.get_password('password')
        
        config = {
            'name': conn_doc.name,
            'display_name': conn_doc.display_name,
            'database_type': conn_doc.database_type,
            'host': conn_doc.host,
            'port': conn_doc.port,
            'database_name': conn_doc.database_name,
            'username': conn_doc.username,
            'password': password,
            'ssh_tunnel': conn_doc.ssh_tunnel,
            'ssh_host': conn_doc.ssh_host if conn_doc.ssh_tunnel else None,
            'ssh_port': conn_doc.ssh_port if conn_doc.ssh_tunnel else None,
            'ssh_username': conn_doc.ssh_username if conn_doc.ssh_tunnel else None,
            'ssh_key_file': conn_doc.ssh_key_file if conn_doc.ssh_tunnel else None,
            'ssl_required': conn_doc.ssl_required
        }
        
        frappe.logger().info(f"Using active database connection: {config['display_name']} ({config['name']})")
        return config
        
    except Exception as e:
        frappe.logger().error(f"Failed to get active database connection: {str(e)}")
        # Fallback to hardcoded config for backward compatibility
        frappe.logger().warning("Falling back to hardcoded PROCUREUAT_CONFIG")
        return {
            'name': 'Legacy_Config',
            'display_name': 'Legacy ProcureUAT Config',
            'database_type': 'MySQL',
            'host': PROCUREUAT_CONFIG['db_host'],
            'port': PROCUREUAT_CONFIG['db_port'],
            'database_name': PROCUREUAT_CONFIG['db_name'],
            'username': PROCUREUAT_CONFIG['db_username'],
            'password': PROCUREUAT_CONFIG['db_password'],
            'ssh_tunnel': 1,
            'ssh_host': PROCUREUAT_CONFIG['ssh_host'],
            'ssh_port': PROCUREUAT_CONFIG['ssh_port'],
            'ssh_username': PROCUREUAT_CONFIG['ssh_username'],
            'ssh_key_file': PROCUREUAT_CONFIG['ssh_key_path'],
            'ssl_required': 0
        }

@contextmanager
def get_external_db_connection():
    """
    Get database connection to ProcureUAT using active Database Connection configuration
    
    Yields:
        pymysql.Connection: Database connection with DictCursor
    """
    tunnel = None
    connection = None
    
    try:
        # Get active database connection configuration
        config = get_active_database_connection()
        
        if config['ssh_tunnel']:
            # SSH tunnel connection
            ssh_key_path = config['ssh_key_file']
            if not os.path.exists(ssh_key_path):
                raise FileNotFoundError(f"SSH key not found: {ssh_key_path}")
            
            # Check file permissions
            file_stat = os.stat(ssh_key_path)
            if oct(file_stat.st_mode)[-3:] != '600':
                frappe.logger().warning(f"SSH key has incorrect permissions: {ssh_key_path}")
            
            # Create SSH tunnel
            tunnel = SSHTunnelForwarder(
                (config['ssh_host'], config['ssh_port']),
                ssh_username=config['ssh_username'],
                ssh_pkey=ssh_key_path,
                remote_bind_address=('127.0.0.1', 3306),  # Remote MySQL port
                local_bind_address=('127.0.0.1', 0)  # Use random available port
            )
            
            tunnel.start()
            local_port = tunnel.local_bind_port
            
            frappe.logger().info(f"SSH tunnel established on local port: {local_port}")
            
            # Create database connection through tunnel
            connection = pymysql.connect(
                host='127.0.0.1',
                port=local_port,
                user=config['username'],
                password=config['password'],
                database=config['database_name'],
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor,
                connect_timeout=30,
                read_timeout=30,
                write_timeout=30,
                autocommit=False
            )
        else:
            # Direct connection
            conn_params = {
                'host': config['host'],
                'port': config['port'],
                'user': config['username'],
                'password': config['password'],
                'database': config['database_name'],
                'charset': 'utf8mb4',
                'cursorclass': pymysql.cursors.DictCursor,
                'connect_timeout': 30,
                'read_timeout': 30,
                'write_timeout': 30,
                'autocommit': False
            }
            
            # Add SSL parameters if required
            if config.get('ssl_required'):
                conn_params['ssl'] = {'ssl_disabled': False}
            else:
                conn_params['ssl_disabled'] = True
            
            connection = pymysql.connect(**conn_params)
        
        # Test connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT DATABASE() as db_name, USER() as user_name, VERSION() as version")
            result = cursor.fetchone()
            frappe.logger().info(f"Connected to {config['display_name']}: {result}")
        
        yield connection
        
    except Exception as e:
        frappe.logger().error(f"External database connection failed: {str(e)}")
        raise
    finally:
        # Clean up resources
        if connection:
            try:
                connection.close()
            except:
                pass
        
        if tunnel:
            try:
                tunnel.stop()
            except:
                pass

def test_external_connection():
    """
    Test the external database connection
    Returns tuple (success: bool, message: str, data: dict)
    """
    try:
        with get_external_db_connection() as conn:
            with conn.cursor() as cursor:
                # Test basic connection
                cursor.execute("SELECT VERSION() as version, DATABASE() as db_name, USER() as user_name")
                db_info = cursor.fetchone()
                
                # Test table access
                cursor.execute("SHOW TABLES LIKE 'purchase_requisitions'")
                pr_table = cursor.fetchone()
                
                cursor.execute("SHOW TABLES LIKE 'purchase_order_items'")
                poi_table = cursor.fetchone()
                
                cursor.execute("SHOW TABLES LIKE 'vendors'")
                vendors_table = cursor.fetchone()
                
                # Get record counts
                cursor.execute("SELECT COUNT(*) as count FROM purchase_requisitions")
                pr_count = cursor.fetchone()['count']
                
                cursor.execute("SELECT COUNT(*) as count FROM purchase_order_items") 
                poi_count = cursor.fetchone()['count']
                
                cursor.execute("SELECT COUNT(*) as count FROM vendors WHERE status = 'active'")
                vendor_count = cursor.fetchone()['count']
                
                data = {
                    'database_info': db_info,
                    'tables_found': {
                        'purchase_requisitions': bool(pr_table),
                        'purchase_order_items': bool(poi_table),
                        'vendors': bool(vendors_table)
                    },
                    'record_counts': {
                        'purchase_requisitions': pr_count,
                        'purchase_order_items': poi_count,
                        'active_vendors': vendor_count
                    }
                }
                
                return True, "Connection successful", data
                
    except Exception as e:
        return False, f"Connection failed: {str(e)}", {}

def get_procureuat_vendors():
    """
    Get active vendors from ProcureUAT database
    Returns list of vendor dictionaries
    """
    try:
        with get_external_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id, name, code, email, gstn, address, contact_number, website, status
                    FROM vendors 
                    WHERE status = 'active'
                    ORDER BY name
                """)
                return cursor.fetchall()
    except Exception as e:
        frappe.logger().error(f"Error fetching vendors: {str(e)}")
        return []

def get_procureuat_purchase_requisitions(limit=10, offset=0, filters=None):
    """
    Get purchase requisitions from ProcureUAT database
    
    Args:
        limit (int): Number of records to fetch
        offset (int): Offset for pagination
        filters (dict): Additional filters
        
    Returns:
        list: Purchase requisitions data
    """
    try:
        with get_external_db_connection() as conn:
            with conn.cursor() as cursor:
                # Build query
                where_conditions = ["pr.is_delete = 0"]
                params = []
                
                if filters:
                    if filters.get('order_status'):
                        where_conditions.append("order_status = %s")
                        params.append(filters['order_status'])
                    
                    if filters.get('entity'):
                        where_conditions.append("entity = %s")
                        params.append(filters['entity'])
                    
                    if filters.get('invoice_generated'):
                        where_conditions.append("invoice_generated = %s")
                        params.append(filters['invoice_generated'])
                
                where_clause = " AND ".join(where_conditions)
                
                query = f"""
                    SELECT pr.id, pr.invoice_number, pr.entity, pr.subentity_id, pr.order_name, 
                           pr.challan_number, pr.status, pr.created_at, pr.approved_at,
                           pr.invoice_generated, pr.acknowledgement, pr.order_status,
                           e.name as entity_name, e.code as entity_code,
                           GROUP_CONCAT(DISTINCT s.name ORDER BY s.id SEPARATOR ', ') as subentity_names
                    FROM purchase_requisitions pr
                    LEFT JOIN entitys e ON pr.entity = e.id
                    LEFT JOIN subentitys s ON FIND_IN_SET(s.id, pr.subentity_id) > 0
                    WHERE {where_clause}
                    GROUP BY pr.id, pr.invoice_number, pr.entity, pr.subentity_id, pr.order_name, 
                             pr.challan_number, pr.status, pr.created_at, pr.approved_at,
                             pr.invoice_generated, pr.acknowledgement, pr.order_status,
                             e.name, e.code
                    ORDER BY pr.created_at DESC, pr.id DESC
                    LIMIT %s OFFSET %s
                """
                
                params.extend([limit, offset])
                cursor.execute(query, params)
                return cursor.fetchall()
                
    except Exception as e:
        frappe.logger().error(f"Error fetching purchase requisitions: {str(e)}")
        return []

def get_procureuat_purchase_order_items(purchase_order_id):
    """
    Get purchase order items for a specific purchase requisition
    
    Args:
        purchase_order_id (int): Purchase requisition ID
        
    Returns:
        list: Purchase order items data
    """
    try:
        with get_external_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id, purchase_order_id, category_id, subcategory_id, product_id,
                           vendor_id, quantity, unit_rate, uom, total_amt, gst_amt, cost,
                           status, created_at
                    FROM purchase_order_items 
                    WHERE purchase_order_id = %s
                    ORDER BY id
                """, (purchase_order_id,))
                return cursor.fetchall()
                
    except Exception as e:
        frappe.logger().error(f"Error fetching purchase order items: {str(e)}")
        return []

def execute_procureuat_query(query, params=None, fetch_all=True):
    """
    Execute a custom query on ProcureUAT database
    
    Args:
        query (str): SQL query to execute
        params (tuple): Query parameters
        fetch_all (bool): Whether to fetch all results or just one
        
    Returns:
        list/dict: Query results
    """
    try:
        with get_external_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params or ())
                
                if fetch_all:
                    return cursor.fetchall()
                else:
                    return cursor.fetchone()
                    
    except Exception as e:
        frappe.logger().error(f"Error executing query: {str(e)}")
        return [] if fetch_all else None


def get_external_orders_for_sync(limit=50):
    """
    Get orders from ProcureUAT system that can be synced to ERPNext
    
    Args:
        limit (int): Maximum number of orders to retrieve
        
    Returns:
        dict: Success status and list of orders
    """
    try:
        with get_external_db_connection() as conn:
            with conn.cursor() as cursor:
                # Get recent purchase requisitions with their items
                query = """
                SELECT DISTINCT
                    pr.id as requisition_id,
                    pr.order_code,
                    pr.vendor_id,
                    pr.entity_id,
                    pr.created_at,
                    pr.status,
                    pr.total_amount,
                    v.name as vendor_name,
                    COUNT(poi.id) as item_count,
                    SUM(poi.total_amount) as total_value
                FROM purchase_requisitions pr
                LEFT JOIN purchase_order_items poi ON pr.id = poi.purchase_requisition_id
                LEFT JOIN vendors v ON pr.vendor_id = v.id
                WHERE pr.status IN ('pending', 'approved', 'completed')
                GROUP BY pr.id
                ORDER BY pr.created_at DESC
                LIMIT %s
                """
                
                cursor.execute(query, (limit,))
                orders = cursor.fetchall()
                
                # Convert to list of dictionaries with proper data types
                order_list = []
                for order in orders:
                    order_dict = {
                        'requisition_id': order['requisition_id'],
                        'order_code': order['order_code'],
                        'vendor_id': order['vendor_id'],
                        'entity_id': order['entity_id'],
                        'created_at': order['created_at'].strftime('%Y-%m-%d %H:%M:%S') if order['created_at'] else None,
                        'status': order['status'],
                        'total_amount': float(order['total_amount']) if order['total_amount'] else 0.0,
                        'vendor_name': order['vendor_name'],
                        'item_count': order['item_count'] or 0,
                        'total_value': float(order['total_value']) if order['total_value'] else 0.0
                    }
                    order_list.append(order_dict)
                
                return {
                    'success': True,
                    'orders': order_list,
                    'count': len(order_list)
                }
                
    except Exception as e:
        return {
            'success': False,
            'error': f"Failed to get external orders: {str(e)}",
            'details': str(e)
        }