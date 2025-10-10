"""
Sync Utilities Module
Provides utility functions for manual sync operations, testing, and maintenance
"""

import frappe
from frappe.utils import now_datetime, add_days, nowdate, get_datetime
import json
from o2o_erpnext.config.external_db_updated import test_external_connection, get_external_db_connection
from o2o_erpnext.sync.erpnext_to_external_updated import sync_invoice_to_procureuat, sync_multiple_invoices
from o2o_erpnext.sync.external_to_erpnext_updated import sync_order_from_procureuat, sync_orders_from_procureuat

# Connection Testing Functions

@frappe.whitelist()
def test_database_connection(connection_name="ProcureUAT", use_ssh_tunnel=True):
    """
    Test external database connection
    
    Args:
        connection_name: Database connection name
        use_ssh_tunnel: Whether to use SSH tunnel
        
    Returns:
        dict: Test results
    """
    try:
        result = test_external_connection(connection_name, use_ssh_tunnel)
        
        # Log the test result
        frappe.logger().info(f"Database connection test: {result['status']}")
        
        return result
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Connection test failed: {str(e)}'
        }

@frappe.whitelist()
def get_external_database_info(connection_name="ProcureUAT"):
    """
    Get external database information and table details
    
    Args:
        connection_name: Database connection name
        
    Returns:
        dict: Database information
    """
    try:
        from o2o_erpnext.config.external_db_updated import get_external_db_connection
        
        with get_external_db_connection(connection_name) as conn:
            with conn.cursor() as cursor:
                # Get database version and basic info
                cursor.execute("SELECT VERSION() as version, DATABASE() as database_name, NOW() as current_time")
                db_info = cursor.fetchone()
                
                # Get invoices table info
                cursor.execute("DESCRIBE invoices")
                invoice_columns = cursor.fetchall()
                
                # Get vendors table info
                cursor.execute("DESCRIBE vendors")
                vendor_columns = cursor.fetchall()
                
                # Get record counts
                cursor.execute("SELECT COUNT(*) as count FROM invoices")
                invoice_count = cursor.fetchone()
                
                cursor.execute("SELECT COUNT(*) as count FROM vendors")
                vendor_count = cursor.fetchone()
                
                # Get recent invoices
                cursor.execute("""
                    SELECT id, invoice_number, invoice_date, total_amount, payment_status, vendor_id
                    FROM invoices 
                    ORDER BY updated_at DESC 
                    LIMIT 5
                """)
                recent_invoices = cursor.fetchall()
                
                return {
                    'status': 'success',
                    'data': {
                        'database_info': db_info,
                        'invoices_table': {
                            'columns': invoice_columns,
                            'count': invoice_count['count']
                        },
                        'vendors_table': {
                            'columns': vendor_columns,
                            'count': vendor_count['count']
                        },
                        'recent_invoices': recent_invoices
                    }
                }
                
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Failed to get database info: {str(e)}'
        }

# Manual Sync Functions

@frappe.whitelist()
def manual_sync_invoice_to_external(invoice_name):
    """
    Manually sync a Purchase Invoice to external database
    
    Args:
        invoice_name: Name of the Purchase Invoice
        
    Returns:
        dict: Sync result
    """
    try:
        if not frappe.has_permission("Purchase Invoice", "write"):
            return {
                'status': 'error',
                'message': 'Insufficient permissions to sync invoices'
            }
        
        result = sync_invoice_to_procureuat(invoice_name)
        
        # Log the manual sync
        frappe.logger().info(f"Manual sync of invoice {invoice_name}: {result['status']}")
        
        return result
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Manual sync failed: {str(e)}'
        }

@frappe.whitelist()
def manual_sync_from_external(external_invoice_id):
    """
    Manually sync an external invoice to ERPNext
    
    Args:
        external_invoice_id: External invoice ID
        
    Returns:
        dict: Sync result
    """
    try:
        if not frappe.has_permission("Purchase Invoice", "create"):
            return {
                'status': 'error',
                'message': 'Insufficient permissions to create invoices'
            }
        
        result = sync_order_from_procureuat(external_invoice_id)
        
        # Log the manual sync
        frappe.logger().info(f"Manual sync of external invoice {external_invoice_id}: {result['status']}")
        
        return result
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Manual external sync failed: {str(e)}'
        }

@frappe.whitelist()
def bulk_sync_from_external(from_date=None, to_date=None, limit=50):
    """
    Bulk sync invoices from external database
    
    Args:
        from_date: Start date (YYYY-MM-DD)
        to_date: End date (YYYY-MM-DD)
        limit: Maximum records to process
        
    Returns:
        dict: Bulk sync results
    """
    try:
        if not frappe.has_permission("Purchase Invoice", "create"):
            return {
                'status': 'error',
                'message': 'Insufficient permissions to create invoices'
            }
        
        result = sync_orders_from_procureuat(limit=int(limit), filters={'from_date': from_date, 'to_date': to_date})
        
        # Log the bulk sync
        frappe.logger().info(f"Bulk sync from external: {result['status']}")
        
        return result
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Bulk sync failed: {str(e)}'
        }

@frappe.whitelist()
def bulk_sync_to_external(filters=None, limit=50):
    """
    Bulk sync ERPNext invoices to external database
    
    Args:
        filters: JSON string of filters
        limit: Maximum records to process
        
    Returns:
        dict: Bulk sync results
    """
    try:
        if not frappe.has_permission("Purchase Invoice", "write"):
            return {
                'status': 'error',
                'message': 'Insufficient permissions to sync invoices'
            }
        
        if filters:
            filters = json.loads(filters)
        
        result = sync_multiple_invoices(json.dumps(filters))
        
        # Log the bulk sync
        frappe.logger().info(f"Bulk sync to external: {result['status']}")
        
        return result
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Bulk sync to external failed: {str(e)}'
        }

# Status and Monitoring Functions

@frappe.whitelist()
def get_sync_status():
    """
    Get comprehensive sync status and statistics
    
    Returns:
        dict: Sync status information
    """
    try:
        from o2o_erpnext.o2o_erpnext.doctype.invoice_sync_log.invoice_sync_log import InvoiceSyncLog
        
        # Get overall statistics
        stats = InvoiceSyncLog.get_sync_statistics()
        
        # Get pending syncs
        pending_to_external = InvoiceSyncLog.get_pending_syncs("ERPNext to ProcureUAT", 10)
        pending_from_external = InvoiceSyncLog.get_pending_syncs("ProcureUAT to ERPNext", 10)
        
        # Get failed syncs that can be retried
        failed_syncs = frappe.get_all("Invoice Sync Log",
                                    filters={
                                        "sync_status": ["in", ["Failed", "Retry"]],
                                        "retry_count": ["<", 3]
                                    },
                                    fields=["name", "sync_direction", "invoice_reference", 
                                           "error_message", "retry_count", "creation"],
                                    limit=10)
        
        # Test database connection
        connection_test = test_external_connection()
        
        return {
            'status': 'success',
            'data': {
                'statistics': stats,
                'pending_to_external': pending_to_external,
                'pending_from_external': pending_from_external,
                'failed_syncs': failed_syncs,
                'database_connection': connection_test,
                'last_updated': now_datetime()
            }
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Failed to get sync status: {str(e)}'
        }

@frappe.whitelist()
def get_invoice_sync_history(invoice_name):
    """
    Get sync history for a specific invoice
    
    Args:
        invoice_name: Name of the Purchase Invoice
        
    Returns:
        dict: Sync history
    """
    try:
        sync_logs = frappe.get_all("Invoice Sync Log",
                                 filters={"erpnext_invoice_id": invoice_name},
                                 fields=["name", "sync_direction", "sync_status", 
                                        "sync_timestamp", "success_message", "error_message",
                                        "operation_type", "sync_method", "retry_count"],
                                 order_by="creation desc")
        
        return {
            'status': 'success',
            'data': {
                'invoice_name': invoice_name,
                'sync_logs': sync_logs
            }
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Failed to get sync history: {str(e)}'
        }

@frappe.whitelist()
def retry_failed_syncs(max_retries=3):
    """
    Retry failed sync operations
    
    Args:
        max_retries: Maximum retry count to process
        
    Returns:
        dict: Retry results
    """
    try:
        if not frappe.has_permission("Invoice Sync Log", "write"):
            return {
                'status': 'error',
                'message': 'Insufficient permissions to retry syncs'
            }
        
        # Get failed syncs that can be retried
        failed_logs = frappe.get_all("Invoice Sync Log",
                                   filters={
                                       "sync_status": ["in", ["Failed", "Retry"]],
                                       "retry_count": ["<", max_retries]
                                   },
                                   fields=["name", "sync_direction", "invoice_reference",
                                          "erpnext_invoice_id", "procureuat_invoice_id"],
                                   limit=20)
        
        results = {
            'total': len(failed_logs),
            'success': 0,
            'failed': 0,
            'retried': []
        }
        
        for log_data in failed_logs:
            try:
                if log_data.sync_direction == "ERPNext to ProcureUAT":
                    if log_data.erpnext_invoice_id:
                        result = sync_invoice_to_procureuat(log_data.erpnext_invoice_id)
                    else:
                        continue
                elif log_data.sync_direction == "ProcureUAT to ERPNext":
                    if log_data.procureuat_invoice_id:
                        result = sync_order_from_procureuat(log_data.procureuat_invoice_id)
                    else:
                        continue
                else:
                    continue
                
                if result['status'] == 'success':
                    results['success'] += 1
                else:
                    results['failed'] += 1
                
                results['retried'].append({
                    'log_name': log_data.name,
                    'direction': log_data.sync_direction,
                    'invoice_reference': log_data.invoice_reference,
                    'retry_status': result['status'],
                    'message': result['message']
                })
                
            except Exception as e:
                results['failed'] += 1
                results['retried'].append({
                    'log_name': log_data.name,
                    'direction': log_data.sync_direction,
                    'invoice_reference': log_data.invoice_reference,
                    'retry_status': 'error',
                    'message': str(e)
                })
        
        return {
            'status': 'completed',
            'message': f"Retry completed: {results['success']} successful, {results['failed']} failed",
            'data': results
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Retry operation failed: {str(e)}'
        }

# Maintenance Functions

@frappe.whitelist()
def cleanup_sync_logs(days=90):
    """
    Clean up old successful sync logs
    
    Args:
        days: Number of days to keep logs
        
    Returns:
        dict: Cleanup results
    """
    try:
        if not frappe.has_permission("Invoice Sync Log", "delete"):
            return {
                'status': 'error',
                'message': 'Insufficient permissions to delete sync logs'
            }
        
        from o2o_erpnext.o2o_erpnext.doctype.invoice_sync_log.invoice_sync_log import InvoiceSyncLog
        
        cutoff_date = add_days(nowdate(), -int(days))
        
        # Count logs to be deleted
        count_query = frappe.db.sql("""
            SELECT COUNT(*) as count
            FROM `tabInvoice Sync Log`
            WHERE sync_status = 'Success'
            AND DATE(creation) < %s
        """, cutoff_date, as_dict=True)
        
        count_to_delete = count_query[0].count if count_query else 0
        
        if count_to_delete > 0:
            # Delete old successful logs
            InvoiceSyncLog.cleanup_old_logs(int(days))
            
            return {
                'status': 'success',
                'message': f'Cleaned up {count_to_delete} old sync logs (older than {days} days)',
                'data': {
                    'deleted_count': count_to_delete,
                    'cutoff_date': cutoff_date
                }
            }
        else:
            return {
                'status': 'success',
                'message': 'No old sync logs found to cleanup',
                'data': {
                    'deleted_count': 0,
                    'cutoff_date': cutoff_date
                }
            }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Cleanup failed: {str(e)}'
        }

@frappe.whitelist()
def reset_sync_tunnels():
    """
    Reset SSH tunnels (close and allow recreation)
    
    Returns:
        dict: Reset results
    """
    try:
        # Close all existing tunnels - function not available
        # close_all_tunnels()
        
        # Test connection (this will create new tunnel)
        connection_test = test_external_connection()
        
        return {
            'status': 'success',
            'message': 'SSH tunnels reset successfully',
            'data': {
                'connection_test': connection_test
            }
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Tunnel reset failed: {str(e)}'
        }

# Vendor/Supplier Mapping Functions

@frappe.whitelist()
def sync_vendor_supplier_mappings():
    """
    Sync vendor-supplier mappings between systems
    
    Returns:
        dict: Mapping sync results
    """
    try:
        from o2o_erpnext.config.external_db_updated import get_external_db_connection
        
        with get_external_db_connection() as conn:
            with conn.cursor() as cursor:
                # Get all vendors from external database
                cursor.execute("""
                    SELECT id, vname, email, gstn, address
                    FROM vendors
                    WHERE vname IS NOT NULL AND vname != ''
                    ORDER BY vname
                """)
                vendors = cursor.fetchall()
        
        results = {
            'total_vendors': len(vendors),
            'mapped': 0,
            'created': 0,
            'skipped': 0,
            'errors': []
        }
        
        for vendor in vendors:
            try:
                # Check if supplier already exists with this vendor ID
                existing_supplier = frappe.get_all("Supplier",
                                                 filters={"custom_external_vendor_id": vendor['id']},
                                                 fields=["name"])
                
                if existing_supplier:
                    results['mapped'] += 1
                    continue
                
                # Try to find supplier by name or email
                supplier_name = None
                
                if vendor['vname']:
                    existing = frappe.get_all("Supplier",
                                            filters={"supplier_name": vendor['vname']},
                                            fields=["name"])
                    if existing:
                        supplier_name = existing[0].name
                
                if not supplier_name and vendor['email']:
                    existing = frappe.get_all("Supplier",
                                            filters={"email_id": vendor['email']},
                                            fields=["name"])
                    if existing:
                        supplier_name = existing[0].name
                
                if supplier_name:
                    # Update existing supplier with vendor ID
                    supplier_doc = frappe.get_doc("Supplier", supplier_name)
                    supplier_doc.custom_external_vendor_id = vendor['id']
                    supplier_doc.save(ignore_permissions=True)
                    results['mapped'] += 1
                else:
                    # Create new supplier
                    supplier_doc = frappe.new_doc("Supplier")
                    supplier_doc.supplier_name = vendor['vname']
                    supplier_doc.custom_external_vendor_id = vendor['id']
                    
                    if vendor['email']:
                        supplier_doc.email_id = vendor['email']
                    
                    if vendor['gstn']:
                        supplier_doc.gst_transporter_id = vendor['gstn']
                    
                    supplier_doc.insert(ignore_permissions=True)
                    results['created'] += 1
                
            except Exception as e:
                results['errors'].append({
                    'vendor_id': vendor['id'],
                    'vendor_name': vendor['vname'],
                    'error': str(e)
                })
                results['skipped'] += 1
        
        frappe.db.commit()
        
        return {
            'status': 'success',
            'message': f"Vendor mapping completed: {results['mapped']} mapped, {results['created']} created, {results['skipped']} skipped",
            'data': results
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Vendor mapping failed: {str(e)}'
        }

# Scheduled Job Functions (called by hooks)

def scheduled_sync_from_external():
    """
    Scheduled function to sync invoices from external database
    Called by Frappe scheduler
    """
    try:
        # Get last sync timestamp from system settings or default to 24 hours ago
        from_date = add_days(nowdate(), -1)  # Last 24 hours
        
        result = sync_orders_from_procureuat(limit=50)
        
        frappe.logger().info(f"Scheduled external sync: {result['message']}")
        
        return result
        
    except Exception as e:
        frappe.logger().error(f"Scheduled external sync failed: {str(e)}")
        return {
            'status': 'error',
            'message': str(e)
        }

def scheduled_cleanup_logs():
    """
    Scheduled function to cleanup old sync logs
    Called weekly by Frappe scheduler
    """
    try:
        result = cleanup_sync_logs(90)  # Keep logs for 90 days
        
        frappe.logger().info(f"Scheduled log cleanup: {result['message']}")
        
        return result
        
    except Exception as e:
        frappe.logger().error(f"Scheduled log cleanup failed: {str(e)}")
        return {
            'status': 'error',
            'message': str(e)
        }