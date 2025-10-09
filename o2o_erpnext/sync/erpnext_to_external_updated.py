"""
Updated ERPNext to ProcureUAT Sync Module
Uses SQL-based field mappings and actual database structure
"""

import frappe
from frappe.utils import flt, getdate, now_datetime, add_days
from datetime import datetime
import json

# Import our updated modules
from o2o_erpnext.config.external_db_updated import get_external_db_connection
from o2o_erpnext.config.field_mappings_sql_based import (
    ERPNEXT_TO_PROCUREUAT_REQUISITIONS,
    ERPNEXT_TO_PROCUREUAT_ITEMS,
    get_vendor_id_from_supplier,
    get_entity_from_supplier,
    convert_erpnext_status_to_procureuat,
    convert_erpnext_docstatus_to_procureuat,
    calculate_totals_from_items,
    generate_procureuat_order_name
)

def sync_invoice_to_procureuat(invoice_name):
    """
    Sync a single ERPNext Purchase Invoice to ProcureUAT
    
    Args:
        invoice_name (str): Name of the Purchase Invoice to sync
        
    Returns:
        dict: Sync result with success status and details
    """
    try:
        # Get Purchase Invoice
        invoice = frappe.get_doc("Purchase Invoice", invoice_name)
        
        # Create sync log entry
        sync_log = create_sync_log(invoice_name, "ERPNext to ProcureUAT")
        
        # Check if already synced
        if invoice.get('custom_external_order_id'):
            return update_existing_procureuat_order(invoice, sync_log)
        else:
            return create_new_procureuat_order(invoice, sync_log)
            
    except Exception as e:
        frappe.logger().error(f"Error syncing invoice {invoice_name} to ProcureUAT: {str(e)}")
        return {
            'success': False,
            'message': f"Sync failed: {str(e)}",
            'invoice_name': invoice_name
        }

def create_new_procureuat_order(invoice, sync_log):
    """
    Create a new purchase requisition in ProcureUAT
    
    Args:
        invoice: ERPNext Purchase Invoice document
        sync_log: Invoice Sync Log document
        
    Returns:
        dict: Creation result
    """
    try:
        # Prepare purchase_requisitions data
        pr_data = prepare_purchase_requisition_data(invoice)
        
        # Prepare purchase_order_items data
        items_data = prepare_purchase_order_items_data(invoice)
        
        with get_external_db_connection() as conn:
            with conn.cursor() as cursor:
                # Begin transaction
                conn.begin()
                
                try:
                    # Insert purchase_requisitions record
                    pr_fields = ', '.join(pr_data.keys())
                    pr_placeholders = ', '.join(['%s'] * len(pr_data))
                    pr_query = f"INSERT INTO purchase_requisitions ({pr_fields}) VALUES ({pr_placeholders})"
                    
                    cursor.execute(pr_query, list(pr_data.values()))
                    purchase_order_id = cursor.lastrowid
                    
                    # Insert purchase_order_items records
                    for item_data in items_data:
                        item_data['purchase_order_id'] = purchase_order_id
                        
                        item_fields = ', '.join(item_data.keys())
                        item_placeholders = ', '.join(['%s'] * len(item_data))
                        item_query = f"INSERT INTO purchase_order_items ({item_fields}) VALUES ({item_placeholders})"
                        
                        cursor.execute(item_query, list(item_data.values()))
                    
                    # Commit transaction
                    conn.commit()
                    
                    # Update ERPNext invoice with external ID
                    invoice.custom_external_order_id = purchase_order_id
                    invoice.custom_last_sync = now_datetime()
                    invoice.custom_sync_status = "Synced"
                    invoice.save()
                    
                    # Update sync log
                    update_sync_log(sync_log, "Completed", 
                                   f"Created ProcureUAT order ID: {purchase_order_id}")
                    
                    return {
                        'success': True,
                        'message': f"Successfully created ProcureUAT order ID: {purchase_order_id}",
                        'invoice_name': invoice.name,
                        'external_order_id': purchase_order_id
                    }
                    
                except Exception as e:
                    # Rollback transaction
                    conn.rollback()
                    raise e
                    
    except Exception as e:
        update_sync_log(sync_log, "Failed", f"Error creating order: {str(e)}")
        raise e

def update_existing_procureuat_order(invoice, sync_log):
    """
    Update an existing purchase requisition in ProcureUAT
    
    Args:
        invoice: ERPNext Purchase Invoice document
        sync_log: Invoice Sync Log document
        
    Returns:
        dict: Update result
    """
    try:
        external_order_id = invoice.custom_external_order_id
        
        # Prepare updated data
        pr_data = prepare_purchase_requisition_data(invoice, is_update=True)
        items_data = prepare_purchase_order_items_data(invoice)
        
        with get_external_db_connection() as conn:
            with conn.cursor() as cursor:
                # Begin transaction
                conn.begin()
                
                try:
                    # Update purchase_requisitions record
                    pr_set_clause = ', '.join([f"{k} = %s" for k in pr_data.keys()])
                    pr_query = f"UPDATE purchase_requisitions SET {pr_set_clause} WHERE id = %s"
                    pr_values = list(pr_data.values()) + [external_order_id]
                    
                    cursor.execute(pr_query, pr_values)
                    
                    # Delete existing items
                    cursor.execute("DELETE FROM purchase_order_items WHERE purchase_order_id = %s", 
                                 (external_order_id,))
                    
                    # Insert updated items
                    for item_data in items_data:
                        item_data['purchase_order_id'] = external_order_id
                        
                        item_fields = ', '.join(item_data.keys())
                        item_placeholders = ', '.join(['%s'] * len(item_data))
                        item_query = f"INSERT INTO purchase_order_items ({item_fields}) VALUES ({item_placeholders})"
                        
                        cursor.execute(item_query, list(item_data.values()))
                    
                    # Commit transaction
                    conn.commit()
                    
                    # Update ERPNext invoice
                    invoice.custom_last_sync = now_datetime()
                    invoice.custom_sync_status = "Synced"
                    invoice.save()
                    
                    # Update sync log
                    update_sync_log(sync_log, "Completed", 
                                   f"Updated ProcureUAT order ID: {external_order_id}")
                    
                    return {
                        'success': True,
                        'message': f"Successfully updated ProcureUAT order ID: {external_order_id}",
                        'invoice_name': invoice.name,
                        'external_order_id': external_order_id
                    }
                    
                except Exception as e:
                    # Rollback transaction
                    conn.rollback()
                    raise e
                    
    except Exception as e:
        update_sync_log(sync_log, "Failed", f"Error updating order: {str(e)}")
        raise e

def prepare_purchase_requisition_data(invoice, is_update=False):
    """
    Prepare purchase_requisitions table data from ERPNext Purchase Invoice
    
    Args:
        invoice: ERPNext Purchase Invoice document
        is_update (bool): Whether this is an update operation
        
    Returns:
        dict: Data for purchase_requisitions table
    """
    data = {}
    
    # Basic mapping from ERPNext to ProcureUAT
    data['order_name'] = generate_procureuat_order_name(invoice.name)
    data['entity'] = get_entity_from_supplier(invoice.supplier)
    data['delivery_date'] = invoice.due_date.strftime('%Y-%m-%d %H:%M:%S') if invoice.due_date else None
    data['validity_date'] = add_days(invoice.due_date, 90).strftime('%Y-%m-%d %H:%M:%S') if invoice.due_date else None
    data['order_code'] = f"PO{invoice.name[-6:]}"  # Generate order code from invoice name
    data['address'] = invoice.supplier_address or ""
    data['remark'] = invoice.remarks or f"Synced from ERPNext Invoice {invoice.name}"
    data['order_status'] = convert_erpnext_status_to_procureuat(invoice.status)
    data['acknowledgement'] = convert_erpnext_docstatus_to_procureuat(invoice.docstatus)
    data['gst_percentage'] = str(invoice.get('custom_gst_percentage', 5))
    data['currency_id'] = 1  # Default currency
    data['category'] = 0  # Default category
    data['amend_no'] = ""
    data['reason'] = ""
    data['clone_id'] = 0
    data['is_delete'] = 0
    data['status'] = 'active'
    data['transportation_mode'] = ""
    data['vehicle_no'] = ""
    data['challan_number'] = ""
    data['freight_rate'] = ""
    data['freight_cost'] = ""
    data['invoice_series'] = 0
    data['invoice_generated'] = 1 if invoice.bill_no else 0
    data['is_visible_header'] = 1
    data['vendor_created'] = 0
    data['gst_percentage'] = str(invoice.get('custom_gst_percentage', 5))
    data['is_new_invoice'] = 0
    data['is_invoice_cancel'] = 1 if invoice.status == 'Cancelled' else 0
    data['credit_note_number'] = ""
    
    # Handle bill/invoice details
    if invoice.bill_no:
        data['invoice_number'] = invoice.bill_no
    if invoice.bill_date:
        data['invoice_generated_at'] = invoice.bill_date.strftime('%Y-%m-%d %H:%M:%S')
    
    # Set timestamps
    if not is_update:
        data['created_at'] = invoice.posting_date.strftime('%Y-%m-%d %H:%M:%S')
        data['created_by'] = 1  # Default user
        data['requisition_at'] = invoice.posting_date.strftime('%Y-%m-%d %H:%M:%S')
        data['requisition_by'] = 1
    
    data['updated_at'] = now_datetime().strftime('%Y-%m-%d %H:%M:%S')
    data['updated_by'] = 1
    
    return data

def prepare_purchase_order_items_data(invoice):
    """
    Prepare purchase_order_items table data from ERPNext Purchase Invoice items
    
    Args:
        invoice: ERPNext Purchase Invoice document
        
    Returns:
        list: List of data dictionaries for purchase_order_items table
    """
    items_data = []
    
    vendor_id = get_vendor_id_from_supplier(invoice.supplier)
    
    for item in invoice.items:
        item_data = {
            'category_id': item.get('custom_category_id', 0),
            'subcategory_id': item.get('custom_subcategory_id', 0),
            'product_id': item.get('custom_product_id', 0),
            'vendor_id': vendor_id or 0,
            'brand_id': 0,
            'image': "",
            'quantity': int(item.qty) if item.qty else 0,
            'unit_rate': str(item.rate) if item.rate else "0",
            'uom': item.uom or "",
            'unit': item.uom or "",
            'unit_type': item.uom or "",
            'product_type': 0,
            'gst_id': item.get('custom_gst_id', 0),
            'total_amt': float(item.amount + (item.get('custom_gst_amount', 0) or 0)),
            'gst_amt': float(item.get('custom_gst_amount', 0) or 0),
            'cost': float(item.amount),
            'status': 'active',
            'vendor_approve': 1,
            'created_at': invoice.posting_date.strftime('%Y-%m-%d %H:%M:%S'),
            'created_by': 1,
            'updated_at': now_datetime().strftime('%Y-%m-%d %H:%M:%S'),
            'updated_by': 1
        }
        
        items_data.append(item_data)
    
    return items_data

def create_sync_log(invoice_name, sync_direction):
    """
    Create a new Invoice Sync Log entry
    
    Args:
        invoice_name (str): Invoice name
        sync_direction (str): Direction of sync
        
    Returns:
        Invoice Sync Log document
    """
    sync_log = frappe.new_doc("Invoice Sync Log")
    sync_log.invoice_name = invoice_name
    sync_log.sync_direction = sync_direction
    sync_log.sync_status = "In Progress"
    sync_log.sync_datetime = now_datetime()
    sync_log.save()
    frappe.db.commit()
    
    return sync_log

def update_sync_log(sync_log, status, message):
    """
    Update sync log with status and message
    
    Args:
        sync_log: Invoice Sync Log document
        status (str): Sync status
        message (str): Sync message
    """
    sync_log.sync_status = status
    sync_log.sync_message = message
    sync_log.save()
    frappe.db.commit()

@frappe.whitelist()
def sync_multiple_invoices(invoice_names):
    """
    Sync multiple Purchase Invoices to ProcureUAT
    
    Args:
        invoice_names (str): JSON string of invoice names
        
    Returns:
        dict: Bulk sync results
    """
    try:
        if isinstance(invoice_names, str):
            invoice_names = json.loads(invoice_names)
        
        results = []
        success_count = 0
        failed_count = 0
        
        for invoice_name in invoice_names:
            try:
                result = sync_invoice_to_procureuat(invoice_name)
                results.append(result)
                
                if result['success']:
                    success_count += 1
                else:
                    failed_count += 1
                    
            except Exception as e:
                failed_count += 1
                results.append({
                    'success': False,
                    'message': f"Error: {str(e)}",
                    'invoice_name': invoice_name
                })
        
        return {
            'success': failed_count == 0,
            'total': len(invoice_names),
            'success_count': success_count,
            'failed_count': failed_count,
            'results': results
        }
        
    except Exception as e:
        frappe.logger().error(f"Error in bulk sync: {str(e)}")
        return {
            'success': False,
            'message': f"Bulk sync failed: {str(e)}"
        }