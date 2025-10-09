"""
ERPNext to ProcureUAT Sync Module
Handles synchronization of Purchase Invoices from ERPNext to ProcureUAT database
"""

import frappe
from frappe.utils import now_datetime, get_datetime
import json
from o2o_erpnext.config.external_db import get_external_db_connection
from o2o_erpnext.config.field_mappings import (
    map_erpnext_to_procureuat, 
    validate_mapping_data,
    get_vendor_id_from_supplier
)

def sync_invoice_to_external(doc, method=None):
    """
    Main function to sync Purchase Invoice from ERPNext to ProcureUAT
    Called by document hooks
    
    Args:
        doc: Purchase Invoice document
        method: Hook method name
    """
    # Skip sync in certain conditions
    if should_skip_sync(doc, method):
        return
    
    try:
        # Check if sync is already in progress for this invoice
        if hasattr(doc, '_sync_in_progress') and doc._sync_in_progress:
            return
        
        # Mark sync in progress to avoid recursive calls
        doc._sync_in_progress = True
        
        # Create or get sync log
        log_doc = get_or_create_sync_log(doc)
        log_doc.mark_in_progress()
        
        # Perform the sync
        result = perform_erpnext_to_external_sync(doc, log_doc)
        
        if result['success']:
            log_doc.mark_success(
                success_message=result['message'],
                target_data=result.get('target_data')
            )
            frappe.logger().info(f"Successfully synced invoice {doc.name} to ProcureUAT")
        else:
            log_doc.mark_failed(result['message'], retry=True)
            frappe.logger().error(f"Failed to sync invoice {doc.name} to ProcureUAT: {result['message']}")
            
    except Exception as e:
        error_msg = f"Error syncing invoice {doc.name}: {str(e)}"
        frappe.logger().error(error_msg)
        
        # Update sync log if it exists
        try:
            log_doc = get_or_create_sync_log(doc)
            log_doc.mark_failed(error_msg, retry=True)
        except Exception:
            pass  # Don't fail if we can't update the log
            
        # Don't raise the exception to avoid breaking the main transaction
        
    finally:
        # Clear sync in progress flag
        if hasattr(doc, '_sync_in_progress'):
            delattr(doc, '_sync_in_progress')

def should_skip_sync(doc, method):
    """
    Determine if sync should be skipped for this invoice
    
    Args:
        doc: Purchase Invoice document
        method: Hook method name
        
    Returns:
        bool: True if sync should be skipped
    """
    # Skip if it's a return invoice
    if getattr(doc, 'is_return', 0):
        return True
    
    # Skip if invoice is in draft status and method is not after_insert
    if doc.docstatus == 0 and method != "after_insert":
        return True
    
    # Skip if already cancelled and method is not on_cancel
    if doc.docstatus == 2 and method != "on_cancel":
        return True
    
    # Skip if sync is disabled for this invoice
    if getattr(doc, 'custom_skip_external_sync', 0):
        return True
    
    # Skip if supplier is not mapped to a vendor
    vendor_id = get_vendor_id_from_supplier(doc.supplier)
    if not vendor_id:
        frappe.logger().warning(f"Skipping sync for invoice {doc.name}: Supplier {doc.supplier} not mapped to vendor")
        return True
    
    return False

def get_or_create_sync_log(doc):
    """
    Get existing sync log or create new one
    
    Args:
        doc: Purchase Invoice document
        
    Returns:
        InvoiceSyncLog: Sync log document
    """
    from o2o_erpnext.o2o_erpnext.doctype.invoice_sync_log.invoice_sync_log import InvoiceSyncLog
    
    # Try to get existing log
    existing_log = InvoiceSyncLog.get_existing_log(
        sync_direction="ERPNext to ProcureUAT",
        invoice_reference=doc.name
    )
    
    if existing_log:
        return existing_log
    
    # Create new log
    return InvoiceSyncLog.create_sync_log(
        sync_direction="ERPNext to ProcureUAT",
        invoice_reference=doc.name,
        erpnext_invoice_id=doc.name,
        external_invoice_id=getattr(doc, 'custom_external_invoice_id', None),
        operation_type="Upsert",
        sync_method="Automatic",
        source_data=json.dumps(doc.as_dict(), default=str)
    )

def perform_erpnext_to_external_sync(doc, log_doc):
    """
    Perform the actual sync operation
    
    Args:
        doc: Purchase Invoice document
        log_doc: Invoice Sync Log document
        
    Returns:
        dict: Result with success status and message
    """
    try:
        # Map ERPNext data to ProcureUAT format
        mapped_data = map_erpnext_to_procureuat(doc)
        
        # Validate mapped data
        is_valid, validation_msg = validate_mapping_data(mapped_data, "erpnext_to_procureuat")
        if not is_valid:
            return {
                'success': False,
                'message': f"Data validation failed: {validation_msg}"
            }
        
        # Connect to external database and sync
        with get_external_db_connection() as conn:
            with conn.cursor() as cursor:
                # Check if invoice already exists
                existing_invoice = None
                if doc.custom_external_invoice_id:
                    cursor.execute(
                        "SELECT * FROM invoices WHERE id = %s",
                        (doc.custom_external_invoice_id,)
                    )
                    existing_invoice = cursor.fetchone()
                
                # If not found by ID, try to find by invoice number
                if not existing_invoice:
                    cursor.execute(
                        "SELECT * FROM invoices WHERE invoice_number = %s",
                        (doc.name,)
                    )
                    existing_invoice = cursor.fetchone()
                
                if existing_invoice:
                    # Update existing invoice
                    result = update_external_invoice(cursor, existing_invoice['id'], mapped_data, doc)
                    operation = "Update"
                    external_id = existing_invoice['id']
                else:
                    # Insert new invoice
                    result = insert_external_invoice(cursor, mapped_data, doc)
                    operation = "Insert"
                    external_id = result.get('external_id')
                
                if result['success']:
                    # Update ERPNext invoice with external ID if it's a new record
                    if operation == "Insert" and external_id:
                        update_erpnext_external_id(doc, external_id)
                    
                    return {
                        'success': True,
                        'message': f"{operation} successful in ProcureUAT (ID: {external_id})",
                        'target_data': {
                            'external_id': external_id,
                            'operation': operation,
                            'mapped_data': mapped_data
                        }
                    }
                else:
                    return result
                    
    except Exception as e:
        return {
            'success': False,
            'message': f"Sync operation failed: {str(e)}"
        }

def insert_external_invoice(cursor, mapped_data, doc):
    """
    Insert new invoice into ProcureUAT database
    
    Args:
        cursor: Database cursor
        mapped_data: Mapped invoice data
        doc: ERPNext Purchase Invoice document
        
    Returns:
        dict: Result with success status and external ID
    """
    try:
        # Prepare insert query
        fields = list(mapped_data.keys())
        placeholders = ', '.join(['%s'] * len(fields))
        field_names = ', '.join(fields)
        
        query = f"INSERT INTO invoices ({field_names}) VALUES ({placeholders})"
        values = list(mapped_data.values())
        
        # Execute insert
        cursor.execute(query, values)
        external_id = cursor.lastrowid
        
        frappe.logger().info(f"Inserted invoice {doc.name} into ProcureUAT with ID {external_id}")
        
        return {
            'success': True,
            'external_id': external_id,
            'message': f"Invoice inserted successfully with ID {external_id}"
        }
        
    except Exception as e:
        error_msg = f"Failed to insert invoice: {str(e)}"
        frappe.logger().error(error_msg)
        return {
            'success': False,
            'message': error_msg
        }

def update_external_invoice(cursor, external_id, mapped_data, doc):
    """
    Update existing invoice in ProcureUAT database
    
    Args:
        cursor: Database cursor
        external_id: External invoice ID
        mapped_data: Mapped invoice data
        doc: ERPNext Purchase Invoice document
        
    Returns:
        dict: Result with success status
    """
    try:
        # Remove ID from mapped data as we don't want to update it
        update_data = {k: v for k, v in mapped_data.items() if k != 'id'}
        
        # Prepare update query
        set_clause = ', '.join([f"{field} = %s" for field in update_data.keys()])
        query = f"UPDATE invoices SET {set_clause} WHERE id = %s"
        values = list(update_data.values()) + [external_id]
        
        # Execute update
        cursor.execute(query, values)
        affected_rows = cursor.rowcount
        
        if affected_rows > 0:
            frappe.logger().info(f"Updated invoice {doc.name} in ProcureUAT (ID: {external_id})")
            return {
                'success': True,
                'message': f"Invoice updated successfully (ID: {external_id})"
            }
        else:
            return {
                'success': False,
                'message': f"No rows updated for invoice ID {external_id}"
            }
            
    except Exception as e:
        error_msg = f"Failed to update invoice: {str(e)}"
        frappe.logger().error(error_msg)
        return {
            'success': False,
            'message': error_msg
        }

def update_erpnext_external_id(doc, external_id):
    """
    Update ERPNext invoice with external ID
    
    Args:
        doc: Purchase Invoice document
        external_id: External invoice ID
    """
    try:
        # Avoid recursive sync call
        doc._sync_in_progress = True
        
        # Update the document
        frappe.db.set_value(
            "Purchase Invoice", 
            doc.name, 
            "custom_external_invoice_id", 
            external_id,
            update_modified=False
        )
        frappe.db.commit()
        
        # Update the in-memory document as well
        doc.custom_external_invoice_id = external_id
        
        frappe.logger().info(f"Updated ERPNext invoice {doc.name} with external ID {external_id}")
        
    except Exception as e:
        frappe.logger().error(f"Failed to update ERPNext invoice with external ID: {str(e)}")
    finally:
        if hasattr(doc, '_sync_in_progress'):
            delattr(doc, '_sync_in_progress')

def handle_invoice_cancellation(doc, method=None):
    """
    Handle invoice cancellation sync
    
    Args:
        doc: Purchase Invoice document
        method: Hook method name
    """
    try:
        if not doc.custom_external_invoice_id:
            return
        
        with get_external_db_connection() as conn:
            with conn.cursor() as cursor:
                # Update status to cancelled in external system
                cursor.execute(
                    "UPDATE invoices SET payment_status = %s WHERE id = %s",
                    ('cancelled', doc.custom_external_invoice_id)
                )
                
                if cursor.rowcount > 0:
                    frappe.logger().info(f"Marked invoice {doc.name} as cancelled in ProcureUAT")
                    
                    # Log the cancellation
                    from o2o_erpnext.o2o_erpnext.doctype.invoice_sync_log.invoice_sync_log import InvoiceSyncLog
                    InvoiceSyncLog.create_sync_log(
                        sync_direction="ERPNext to ProcureUAT",
                        invoice_reference=doc.name,
                        erpnext_invoice_id=doc.name,
                        external_invoice_id=doc.custom_external_invoice_id,
                        operation_type="Update",
                        sync_method="Automatic",
                        sync_status="Success",
                        success_message="Invoice cancelled successfully"
                    )
                    
    except Exception as e:
        frappe.logger().error(f"Failed to cancel invoice {doc.name} in ProcureUAT: {str(e)}")

# Utility functions for manual sync operations

def force_sync_invoice(invoice_name):
    """
    Force sync a specific invoice
    
    Args:
        invoice_name: Name of the Purchase Invoice
        
    Returns:
        dict: Sync result
    """
    try:
        doc = frappe.get_doc("Purchase Invoice", invoice_name)
        
        # Bypass skip conditions by temporarily setting flags
        original_skip = getattr(doc, 'custom_skip_external_sync', 0)
        doc.custom_skip_external_sync = 0
        
        # Force sync
        sync_invoice_to_external(doc, method="force_sync")
        
        # Restore original flag
        doc.custom_skip_external_sync = original_skip
        
        return {
            'status': 'success',
            'message': f'Invoice {invoice_name} synced successfully'
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Failed to sync invoice {invoice_name}: {str(e)}'
        }

def bulk_sync_invoices(filters=None, limit=100):
    """
    Bulk sync multiple invoices
    
    Args:
        filters: Optional filters for invoices
        limit: Maximum number of invoices to sync
        
    Returns:
        dict: Bulk sync results
    """
    try:
        if not filters:
            filters = {
                'docstatus': 1,  # Submitted invoices only
                'is_return': 0   # Not return invoices
            }
        
        invoices = frappe.get_all(
            "Purchase Invoice",
            filters=filters,
            fields=['name'],
            limit=limit
        )
        
        results = {
            'total': len(invoices),
            'success': 0,
            'failed': 0,
            'errors': []
        }
        
        for invoice in invoices:
            result = force_sync_invoice(invoice.name)
            if result['status'] == 'success':
                results['success'] += 1
            else:
                results['failed'] += 1
                results['errors'].append({
                    'invoice': invoice.name,
                    'error': result['message']
                })
        
        return {
            'status': 'completed',
            'message': f"Bulk sync completed: {results['success']} successful, {results['failed']} failed",
            'data': results
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Bulk sync failed: {str(e)}'
        }