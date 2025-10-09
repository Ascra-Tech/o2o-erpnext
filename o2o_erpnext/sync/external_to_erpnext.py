"""
ProcureUAT to ERPNext Sync Module
Handles synchronization of invoices from ProcureUAT database to ERPNext Purchase Invoices
"""

import frappe
from frappe.utils import now_datetime, get_datetime, getdate, flt
import json
from o2o_erpnext.config.external_db import get_external_db_connection
from o2o_erpnext.config.field_mappings import (
    map_procureuat_to_erpnext,
    validate_mapping_data,
    get_supplier_from_vendor_id,
    STATUS_MAPPING_PROCUREUAT_TO_ERPNEXT
)

def sync_invoices_from_external(from_date=None, to_date=None, limit=100):
    """
    Main function to sync invoices from ProcureUAT to ERPNext
    Called by scheduler
    
    Args:
        from_date: Start date for sync (optional)
        to_date: End date for sync (optional)
        limit: Maximum number of records to process
        
    Returns:
        dict: Sync results
    """
    try:
        # Get modified invoices from external database
        external_invoices = get_modified_external_invoices(from_date, to_date, limit)
        
        results = {
            'total': len(external_invoices),
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'errors': [],
            'processed_invoices': []
        }
        
        for invoice_data in external_invoices:
            try:
                result = process_external_invoice(invoice_data)
                
                if result['status'] == 'success':
                    results['success'] += 1
                elif result['status'] == 'skipped':
                    results['skipped'] += 1
                else:
                    results['failed'] += 1
                    results['errors'].append({
                        'external_id': invoice_data.get('id'),
                        'error': result['message']
                    })
                
                results['processed_invoices'].append({
                    'external_id': invoice_data.get('id'),
                    'invoice_number': invoice_data.get('invoice_number'),
                    'status': result['status'],
                    'message': result['message']
                })
                
            except Exception as e:
                results['failed'] += 1
                results['errors'].append({
                    'external_id': invoice_data.get('id'),
                    'error': str(e)
                })
        
        # Log overall sync results
        frappe.logger().info(f"External sync completed: {results['success']} success, {results['failed']} failed, {results['skipped']} skipped")
        
        return {
            'status': 'completed',
            'message': f"Sync completed: {results['success']} successful, {results['failed']} failed, {results['skipped']} skipped",
            'data': results
        }
        
    except Exception as e:
        error_msg = f"External to ERPNext sync failed: {str(e)}"
        frappe.logger().error(error_msg)
        return {
            'status': 'error',
            'message': error_msg
        }

def get_modified_external_invoices(from_date=None, to_date=None, limit=100):
    """
    Get modified invoices from ProcureUAT database
    
    Args:
        from_date: Start date filter
        to_date: End date filter
        limit: Maximum records to fetch
        
    Returns:
        list: List of invoice data dictionaries
    """
    try:
        with get_external_db_connection() as conn:
            with conn.cursor() as cursor:
                # Build query with date filters
                where_conditions = []
                params = []
                
                if from_date:
                    where_conditions.append("DATE(updated_at) >= %s")
                    params.append(from_date)
                
                if to_date:
                    where_conditions.append("DATE(updated_at) <= %s")
                    params.append(to_date)
                
                # Only sync invoices that don't have sync_source = 'erpnext' to avoid circular sync
                where_conditions.append("(sync_source IS NULL OR sync_source != 'erpnext')")
                
                where_clause = ""
                if where_conditions:
                    where_clause = "WHERE " + " AND ".join(where_conditions)
                
                query = f"""
                    SELECT 
                        id, invoice_number, invoice_date, due_date,
                        total_amount, invoice_amount, gst_amount, gst_percentage,
                        payment_status, vendor_id, vendor_name,
                        bill_number, bill_date, description,
                        created_at, updated_at
                    FROM invoices
                    {where_clause}
                    ORDER BY updated_at DESC
                    LIMIT %s
                """
                
                params.append(limit)
                cursor.execute(query, params)
                return cursor.fetchall()
                
    except Exception as e:
        frappe.logger().error(f"Failed to fetch external invoices: {str(e)}")
        return []

def process_external_invoice(invoice_data):
    """
    Process a single external invoice
    
    Args:
        invoice_data: Invoice data from ProcureUAT
        
    Returns:
        dict: Processing result
    """
    try:
        external_id = invoice_data['id']
        invoice_number = invoice_data.get('invoice_number')
        
        # Check if we should skip this invoice
        if should_skip_external_invoice(invoice_data):
            return {
                'status': 'skipped',
                'message': 'Invoice skipped due to skip conditions'
            }
        
        # Check if sync log already exists and is successful
        from o2o_erpnext.o2o_erpnext.doctype.invoice_sync_log.invoice_sync_log import InvoiceSyncLog
        
        existing_log = InvoiceSyncLog.get_existing_log(
            sync_direction="ProcureUAT to ERPNext",
            invoice_reference=f"PROC-{external_id}",
            sync_status="Success"
        )
        
        if existing_log:
            # Check if external invoice was modified after last sync
            last_sync = get_datetime(existing_log.sync_timestamp)
            invoice_updated = get_datetime(invoice_data.get('updated_at'))
            
            if invoice_updated <= last_sync:
                return {
                    'status': 'skipped',
                    'message': 'Invoice not modified since last sync'
                }
        
        # Create or get sync log
        log_doc = get_or_create_external_sync_log(invoice_data)
        log_doc.mark_in_progress()
        
        # Map data from ProcureUAT to ERPNext format
        mapped_data = map_procureuat_to_erpnext(invoice_data)
        
        # Validate mapped data
        is_valid, validation_msg = validate_mapping_data(mapped_data, "procureuat_to_erpnext")
        if not is_valid:
            log_doc.mark_failed(f"Data validation failed: {validation_msg}")
            return {
                'status': 'failed',
                'message': f"Data validation failed: {validation_msg}"
            }
        
        # Check if ERPNext invoice already exists
        existing_invoice = find_existing_erpnext_invoice(invoice_data, mapped_data)
        
        if existing_invoice:
            # Update existing invoice
            result = update_erpnext_invoice(existing_invoice, mapped_data, invoice_data, log_doc)
        else:
            # Create new invoice
            result = create_erpnext_invoice(mapped_data, invoice_data, log_doc)
        
        if result['success']:
            log_doc.mark_success(
                success_message=result['message'],
                target_data=result.get('target_data')
            )
            
            # Update external invoice to mark it as synced
            mark_external_invoice_synced(external_id)
            
            return {
                'status': 'success',
                'message': result['message'],
                'erpnext_invoice': result.get('invoice_name')
            }
        else:
            log_doc.mark_failed(result['message'], retry=True)
            return {
                'status': 'failed',
                'message': result['message']
            }
            
    except Exception as e:
        error_msg = f"Error processing external invoice {invoice_data.get('id')}: {str(e)}"
        frappe.logger().error(error_msg)
        return {
            'status': 'failed',
            'message': error_msg
        }

def should_skip_external_invoice(invoice_data):
    """
    Determine if external invoice should be skipped
    
    Args:
        invoice_data: Invoice data from ProcureUAT
        
    Returns:
        bool: True if should skip
    """
    # Skip if no vendor mapping
    vendor_id = invoice_data.get('vendor_id')
    if not vendor_id:
        return True
    
    supplier = get_supplier_from_vendor_id(vendor_id)
    if not supplier:
        frappe.logger().warning(f"No supplier mapping found for vendor ID {vendor_id}")
        return True
    
    # Skip if essential data is missing
    if not invoice_data.get('invoice_number') or not invoice_data.get('total_amount'):
        return True
    
    # Skip if invoice is cancelled
    if invoice_data.get('payment_status') == 'cancelled':
        return True
    
    return False

def get_or_create_external_sync_log(invoice_data):
    """
    Get or create sync log for external invoice
    
    Args:
        invoice_data: Invoice data from ProcureUAT
        
    Returns:
        InvoiceSyncLog: Sync log document
    """
    from o2o_erpnext.o2o_erpnext.doctype.invoice_sync_log.invoice_sync_log import InvoiceSyncLog
    
    external_id = invoice_data['id']
    invoice_ref = f"PROC-{external_id}"
    
    # Try to get existing log
    existing_log = InvoiceSyncLog.get_existing_log(
        sync_direction="ProcureUAT to ERPNext",
        invoice_reference=invoice_ref
    )
    
    if existing_log:
        return existing_log
    
    # Create new log
    return InvoiceSyncLog.create_sync_log(
        sync_direction="ProcureUAT to ERPNext",
        invoice_reference=invoice_ref,
        procureuat_invoice_id=external_id,
        operation_type="Upsert",
        sync_method="Scheduled",
        source_data=json.dumps(invoice_data, default=str)
    )

def find_existing_erpnext_invoice(invoice_data, mapped_data):
    """
    Find existing ERPNext invoice for external invoice
    
    Args:
        invoice_data: External invoice data
        mapped_data: Mapped ERPNext data
        
    Returns:
        Purchase Invoice document or None
    """
    try:
        external_id = invoice_data['id']
        
        # First try to find by external invoice ID
        existing = frappe.get_all("Purchase Invoice",
                                filters={"custom_external_invoice_id": external_id},
                                fields=["name"])
        
        if existing:
            return frappe.get_doc("Purchase Invoice", existing[0].name)
        
        # Try to find by invoice number and supplier combination
        supplier = mapped_data.get('supplier')
        if supplier and invoice_data.get('invoice_number'):
            existing = frappe.get_all("Purchase Invoice",
                                    filters={
                                        "bill_no": invoice_data['invoice_number'],
                                        "supplier": supplier
                                    },
                                    fields=["name"])
            
            if existing:
                return frappe.get_doc("Purchase Invoice", existing[0].name)
        
        return None
        
    except Exception as e:
        frappe.logger().error(f"Error finding existing ERPNext invoice: {str(e)}")
        return None

def create_erpnext_invoice(mapped_data, invoice_data, log_doc):
    """
    Create new ERPNext Purchase Invoice
    
    Args:
        mapped_data: Mapped invoice data
        invoice_data: Original external data
        log_doc: Sync log document
        
    Returns:
        dict: Creation result
    """
    try:
        # Create new Purchase Invoice
        doc = frappe.new_doc("Purchase Invoice")
        
        # Set mapped fields
        for field, value in mapped_data.items():
            if hasattr(doc, field) and value is not None:
                setattr(doc, field, value)
        
        # Set required fields with defaults if not provided
        if not doc.company:
            doc.company = frappe.defaults.get_user_default("company") or frappe.get_all("Company", limit=1)[0].name
        
        if not doc.posting_date:
            doc.posting_date = getdate()
        
        # Set external invoice ID
        doc.custom_external_invoice_id = invoice_data['id']
        
        # Set flags to avoid triggering sync back to external
        doc._sync_in_progress = True
        doc.flags.ignore_validate = True
        
        # Insert the document
        doc.insert(ignore_permissions=True)
        
        # Handle payment status
        payment_status = invoice_data.get('payment_status', '')
        if payment_status == 'paid' and doc.docstatus == 0:
            # Submit the invoice if it's paid
            doc.submit()
            
            # Create payment entry if needed
            create_payment_entry_for_invoice(doc, invoice_data)
        
        # Update sync log with ERPNext invoice ID
        log_doc.erpnext_invoice_id = doc.name
        log_doc.save(ignore_permissions=True)
        
        frappe.db.commit()
        
        return {
            'success': True,
            'message': f"Created ERPNext invoice {doc.name}",
            'invoice_name': doc.name,
            'target_data': {
                'invoice_id': doc.name,
                'operation': 'Create',
                'external_id': invoice_data['id']
            }
        }
        
    except Exception as e:
        error_msg = f"Failed to create ERPNext invoice: {str(e)}"
        frappe.logger().error(error_msg)
        return {
            'success': False,
            'message': error_msg
        }

def update_erpnext_invoice(existing_doc, mapped_data, invoice_data, log_doc):
    """
    Update existing ERPNext Purchase Invoice
    
    Args:
        existing_doc: Existing Purchase Invoice document
        mapped_data: Mapped invoice data
        invoice_data: Original external data
        log_doc: Sync log document
        
    Returns:
        dict: Update result
    """
    try:
        # Check if invoice can be updated (not submitted/cancelled)
        if existing_doc.docstatus != 0:
            # For submitted invoices, only update payment status
            return update_payment_status_only(existing_doc, invoice_data, log_doc)
        
        # Update fields for draft invoices
        updated_fields = []
        for field, value in mapped_data.items():
            if hasattr(existing_doc, field) and value is not None:
                current_value = getattr(existing_doc, field)
                if current_value != value:
                    setattr(existing_doc, field, value)
                    updated_fields.append(field)
        
        # Set external invoice ID if not set
        if not existing_doc.custom_external_invoice_id:
            existing_doc.custom_external_invoice_id = invoice_data['id']
            updated_fields.append('custom_external_invoice_id')
        
        if updated_fields:
            # Set flags to avoid triggering sync back to external
            existing_doc._sync_in_progress = True
            existing_doc.flags.ignore_validate = True
            
            # Save the document
            existing_doc.save(ignore_permissions=True)
            
            # Handle payment status
            payment_status = invoice_data.get('payment_status', '')
            if payment_status == 'paid' and existing_doc.docstatus == 0:
                existing_doc.submit()
                create_payment_entry_for_invoice(existing_doc, invoice_data)
            
            frappe.db.commit()
            
            return {
                'success': True,
                'message': f"Updated ERPNext invoice {existing_doc.name} (fields: {', '.join(updated_fields)})",
                'invoice_name': existing_doc.name,
                'target_data': {
                    'invoice_id': existing_doc.name,
                    'operation': 'Update',
                    'updated_fields': updated_fields
                }
            }
        else:
            return {
                'success': True,
                'message': f"No updates needed for ERPNext invoice {existing_doc.name}",
                'invoice_name': existing_doc.name
            }
            
    except Exception as e:
        error_msg = f"Failed to update ERPNext invoice: {str(e)}"
        frappe.logger().error(error_msg)
        return {
            'success': False,
            'message': error_msg
        }

def update_payment_status_only(existing_doc, invoice_data, log_doc):
    """
    Update only payment status for submitted invoices
    
    Args:
        existing_doc: Existing Purchase Invoice document
        invoice_data: External invoice data
        log_doc: Sync log document
        
    Returns:
        dict: Update result
    """
    try:
        payment_status = invoice_data.get('payment_status', '')
        current_status = existing_doc.status
        
        # Map external status to ERPNext status
        target_status = STATUS_MAPPING_PROCUREUAT_TO_ERPNEXT.get(payment_status)
        
        if target_status and target_status != current_status:
            if payment_status == 'paid' and current_status != 'Paid':
                # Create payment entry to mark as paid
                create_payment_entry_for_invoice(existing_doc, invoice_data)
                
                return {
                    'success': True,
                    'message': f"Created payment for invoice {existing_doc.name}",
                    'invoice_name': existing_doc.name,
                    'target_data': {
                        'invoice_id': existing_doc.name,
                        'operation': 'Payment Created',
                        'payment_status': payment_status
                    }
                }
        
        return {
            'success': True,
            'message': f"No payment status update needed for invoice {existing_doc.name}",
            'invoice_name': existing_doc.name
        }
        
    except Exception as e:
        error_msg = f"Failed to update payment status: {str(e)}"
        frappe.logger().error(error_msg)
        return {
            'success': False,
            'message': error_msg
        }

def create_payment_entry_for_invoice(invoice_doc, invoice_data):
    """
    Create payment entry for invoice
    
    Args:
        invoice_doc: Purchase Invoice document
        invoice_data: External invoice data
    """
    try:
        # Check if payment entry already exists
        existing_payment = frappe.get_all("Payment Entry",
                                        filters={
                                            "reference_name": invoice_doc.name,
                                            "reference_doctype": "Purchase Invoice",
                                            "docstatus": 1
                                        })
        
        if existing_payment:
            return  # Payment already exists
        
        # Create payment entry
        payment_entry = frappe.new_doc("Payment Entry")
        payment_entry.payment_type = "Pay"
        payment_entry.party_type = "Supplier"
        payment_entry.party = invoice_doc.supplier
        payment_entry.company = invoice_doc.company
        payment_entry.paid_amount = invoice_doc.grand_total
        payment_entry.received_amount = invoice_doc.grand_total
        payment_entry.reference_no = f"AUTO-PAY-{invoice_doc.name}"
        payment_entry.reference_date = getdate()
        
        # Add reference to invoice
        payment_entry.append("references", {
            "reference_doctype": "Purchase Invoice",
            "reference_name": invoice_doc.name,
            "allocated_amount": invoice_doc.outstanding_amount
        })
        
        # Set mode of payment (default)
        mode_of_payment = frappe.get_all("Mode of Payment", limit=1)
        if mode_of_payment:
            payment_entry.mode_of_payment = mode_of_payment[0].name
        
        payment_entry.insert(ignore_permissions=True)
        payment_entry.submit()
        
        frappe.logger().info(f"Created payment entry for invoice {invoice_doc.name}")
        
    except Exception as e:
        frappe.logger().error(f"Failed to create payment entry for {invoice_doc.name}: {str(e)}")

def mark_external_invoice_synced(external_id):
    """
    Mark external invoice as synced to avoid re-processing
    
    Args:
        external_id: External invoice ID
    """
    try:
        with get_external_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE invoices SET last_sync = %s WHERE id = %s",
                    (now_datetime(), external_id)
                )
                
    except Exception as e:
        frappe.logger().error(f"Failed to mark external invoice {external_id} as synced: {str(e)}")

# Utility functions for manual sync operations

def force_sync_external_invoice(external_id):
    """
    Force sync a specific external invoice
    
    Args:
        external_id: External invoice ID
        
    Returns:
        dict: Sync result
    """
    try:
        # Get external invoice data
        with get_external_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM invoices WHERE id = %s",
                    (external_id,)
                )
                invoice_data = cursor.fetchone()
        
        if not invoice_data:
            return {
                'status': 'error',
                'message': f'External invoice {external_id} not found'
            }
        
        # Process the invoice
        result = process_external_invoice(invoice_data)
        
        return {
            'status': result['status'],
            'message': result['message']
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Failed to sync external invoice {external_id}: {str(e)}'
        }