"""
Purchase Invoice Sync API
Provides API endpoints for synchronizing Purchase Invoices with ProcureUAT system
"""
import frappe
from frappe import _
import traceback
import json
from o2o_erpnext.sync.erpnext_to_external_updated import sync_invoice_to_procureuat
from o2o_erpnext.sync.external_to_erpnext_updated import sync_order_from_procureuat


@frappe.whitelist()
def sync_to_external(invoice_name):
    """
    Sync a single Purchase Invoice to ProcureUAT system
    
    Args:
        invoice_name (str): Name of the Purchase Invoice to sync
        
    Returns:
        dict: Success/error status with details
    """
    try:
        # Validate invoice exists and user has permission
        if not frappe.db.exists("Purchase Invoice", invoice_name):
            return {
                'success': False,
                'error': f'Purchase Invoice {invoice_name} not found'
            }
        
        # Check permissions
        if not frappe.has_permission("Purchase Invoice", "read", invoice_name):
            return {
                'success': False,
                'error': 'Insufficient permissions to sync this invoice'
            }
        
        # Perform sync
        result = sync_invoice_to_procureuat(invoice_name)
        
        if result.get('success'):
            return {
                'success': True,
                'message': f'Invoice {invoice_name} synced successfully to ProcureUAT',
                'external_id': result.get('external_id'),
                'details': result.get('details')
            }
        else:
            return {
                'success': False,
                'error': result.get('error', 'Unknown sync error'),
                'details': result.get('details')
            }
            
    except Exception as e:
        frappe.log_error(
            message=f"Sync to external error for {invoice_name}: {str(e)}\n{traceback.format_exc()}",
            title="Purchase Invoice Sync Error"
        )
        return {
            'success': False,
            'error': f'Sync failed: {str(e)}'
        }


@frappe.whitelist()
def sync_from_external(external_order_id):
    """
    Sync an order from ProcureUAT to ERPNext
    
    Args:
        external_order_id (str): ID of the order in ProcureUAT system
        
    Returns:
        dict: Success/error status with details
    """
    try:
        # Perform sync from external system
        result = sync_order_from_procureuat(external_order_id)
        
        if result.get('success'):
            return {
                'success': True,
                'message': f'Order {external_order_id} synced successfully from ProcureUAT',
                'invoice_name': result.get('invoice_name'),
                'details': result.get('details')
            }
        else:
            return {
                'success': False,
                'error': result.get('error', 'Unknown sync error'),
                'details': result.get('details')
            }
            
    except Exception as e:
        frappe.log_error(
            message=f"Sync from external error for {external_order_id}: {str(e)}\n{traceback.format_exc()}",
            title="Purchase Invoice Sync Error"
        )
        return {
            'success': False,
            'error': f'Sync failed: {str(e)}'
        }


@frappe.whitelist()
def bulk_sync_to_external(invoice_names):
    """
    Sync multiple Purchase Invoices to ProcureUAT system
    
    Args:
        invoice_names (str): JSON string of invoice names list
        
    Returns:
        dict: Bulk sync results with success/failure counts
    """
    try:
        # Parse invoice names
        if isinstance(invoice_names, str):
            invoice_names = json.loads(invoice_names)
        
        results = {
            'success_count': 0,
            'error_count': 0,
            'results': [],
            'errors': []
        }
        
        for invoice_name in invoice_names:
            try:
                result = sync_invoice_to_procureuat(invoice_name)
                
                if result.get('success'):
                    results['success_count'] += 1
                    results['results'].append({
                        'invoice': invoice_name,
                        'status': 'success',
                        'external_id': result.get('external_id')
                    })
                else:
                    results['error_count'] += 1
                    results['errors'].append({
                        'invoice': invoice_name,
                        'error': result.get('error', 'Unknown error')
                    })
                    
            except Exception as e:
                results['error_count'] += 1
                results['errors'].append({
                    'invoice': invoice_name,
                    'error': str(e)
                })
        
        return {
            'success': True,
            'message': f'Bulk sync completed: {results["success_count"]} successful, {results["error_count"]} failed',
            'results': results
        }
        
    except Exception as e:
        frappe.log_error(
            message=f"Bulk sync error: {str(e)}\n{traceback.format_exc()}",
            title="Purchase Invoice Bulk Sync Error"
        )
        return {
            'success': False,
            'error': f'Bulk sync failed: {str(e)}'
        }


@frappe.whitelist()
def get_sync_status(invoice_name):
    """
    Get sync status for a Purchase Invoice
    
    Args:
        invoice_name (str): Name of the Purchase Invoice
        
    Returns:
        dict: Sync status information
    """
    try:
        # Check if invoice exists
        if not frappe.db.exists("Purchase Invoice", invoice_name):
            return {
                'success': False,
                'error': f'Purchase Invoice {invoice_name} not found'
            }
        
        # Get custom fields for sync status
        doc = frappe.get_doc("Purchase Invoice", invoice_name)
        
        sync_status = {
            'invoice_name': invoice_name,
            'external_id': getattr(doc, 'external_order_id', None),
            'sync_status': getattr(doc, 'sync_status', 'Not Synced'),
            'last_sync_date': getattr(doc, 'last_sync_date', None),
            'sync_direction': getattr(doc, 'sync_direction', None),
            'sync_errors': getattr(doc, 'sync_errors', None),
            'is_synced': bool(getattr(doc, 'external_order_id', None))
        }
        
        return {
            'success': True,
            'sync_status': sync_status
        }
        
    except Exception as e:
        frappe.log_error(
            message=f"Get sync status error for {invoice_name}: {str(e)}\n{traceback.format_exc()}",
            title="Get Sync Status Error"
        )
        return {
            'success': False,
            'error': f'Failed to get sync status: {str(e)}'
        }


@frappe.whitelist()
def test_external_connection():
    """
    Test connection to ProcureUAT external database
    
    Returns:
        dict: Connection test results
    """
    try:
        from o2o_erpnext.config.external_db_updated import test_external_connection as test_conn
        
        success, message, data = test_conn()
        
        if success:
            return {
                'success': True,
                'message': message,
                'details': data
            }
        else:
            return {
                'success': False,
                'error': message,
                'details': data
            }
            
    except Exception as e:
        frappe.log_error(
            message=f"External connection test error: {str(e)}\n{traceback.format_exc()}",
            title="External Connection Test Error"
        )
        return {
            'success': False,
            'error': f'Connection test failed: {str(e)}'
        }


@frappe.whitelist()
def get_pending_sync_invoices():
    """
    Get list of Purchase Invoices that haven't been synced to external system
    
    Returns:
        dict: List of pending sync invoices
    """
    try:
        # Query for unsynced invoices
        invoices = frappe.db.sql("""
            SELECT 
                name,
                supplier,
                posting_date,
                grand_total,
                COALESCE(sync_status, 'Not Synced') as sync_status,
                external_order_id
            FROM `tabPurchase Invoice`
            WHERE 
                docstatus = 1
                AND (external_order_id IS NULL OR external_order_id = '')
            ORDER BY posting_date DESC
            LIMIT 100
        """, as_dict=True)
        
        return {
            'success': True,
            'invoices': invoices,
            'count': len(invoices)
        }
        
    except Exception as e:
        frappe.log_error(
            message=f"Get pending sync invoices error: {str(e)}\n{traceback.format_exc()}",
            title="Get Pending Sync Invoices Error"
        )
        return {
            'success': False,
            'error': f'Failed to get pending invoices: {str(e)}'
        }


@frappe.whitelist()
def get_external_orders():
    """
    Get list of orders from ProcureUAT system that can be synced to ERPNext
    
    Returns:
        dict: List of external orders
    """
    try:
        from o2o_erpnext.config.external_db_updated import get_external_orders_for_sync
        
        result = get_external_orders_for_sync()
        
        if result.get('success'):
            return {
                'success': True,
                'orders': result.get('orders', []),
                'count': len(result.get('orders', []))
            }
        else:
            return {
                'success': False,
                'error': result.get('error', 'Failed to get external orders'),
                'details': result.get('details')
            }
            
    except Exception as e:
        frappe.log_error(
            message=f"Get external orders error: {str(e)}\n{traceback.format_exc()}",
            title="Get External Orders Error"
        )
        return {
            'success': False,
            'error': f'Failed to get external orders: {str(e)}'
        }