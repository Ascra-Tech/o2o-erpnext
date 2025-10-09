"""
Updated ProcureUAT to ERPNext Sync Module
Uses SQL-based field mappings and actual database structure
"""

import frappe
from frappe.utils import flt, getdate, now_datetime, get_datetime
from datetime import datetime
import json

# Import our updated modules
from o2o_erpnext.config.external_db_updated import (
    get_external_db_connection,
    get_procureuat_purchase_requisitions,
    get_procureuat_purchase_order_items
)
from o2o_erpnext.config.field_mappings_sql_based import (
    PROCUREUAT_TO_ERPNEXT_REQUISITIONS,
    PROCUREUAT_TO_ERPNEXT_ITEMS,
    get_supplier_from_vendor_id,
    convert_procureuat_status_to_erpnext,
    convert_procureuat_acknowledgement_to_erpnext,
    generate_erpnext_invoice_name
)

def sync_order_from_procureuat(external_order_id):
    """
    Sync a single ProcureUAT purchase requisition to ERPNext
    
    Args:
        external_order_id (int): ProcureUAT purchase requisition ID
        
    Returns:
        dict: Sync result with success status and details
    """
    try:
        # Get order data from ProcureUAT
        order_data = get_procureuat_order_data(external_order_id)
        if not order_data:
            return {
                'success': False,
                'message': f"Order {external_order_id} not found in ProcureUAT",
                'external_order_id': external_order_id
            }
        
        # Create sync log entry
        sync_log = create_sync_log(f"EXT-{external_order_id}", "ProcureUAT to ERPNext")
        
        # Check if already synced
        existing_invoice = frappe.db.get_value("Purchase Invoice", 
                                              {"custom_external_order_id": external_order_id}, 
                                              "name")
        
        if existing_invoice:
            return update_existing_erpnext_invoice(existing_invoice, order_data, sync_log)
        else:
            return create_new_erpnext_invoice(order_data, sync_log)
            
    except Exception as e:
        frappe.logger().error(f"Error syncing order {external_order_id} from ProcureUAT: {str(e)}")
        return {
            'success': False,
            'message': f"Sync failed: {str(e)}",
            'external_order_id': external_order_id
        }

def create_new_erpnext_invoice(order_data, sync_log):
    """
    Create a new Purchase Invoice in ERPNext from ProcureUAT data
    
    Args:
        order_data (dict): ProcureUAT order data
        sync_log: Invoice Sync Log document
        
    Returns:
        dict: Creation result
    """
    try:
        requisition = order_data['requisition']
        items = order_data['items']
        
        # Create Purchase Invoice document
        invoice = frappe.new_doc("Purchase Invoice")
        
        # Map basic fields
        invoice.supplier = get_supplier_from_vendor_id(get_vendor_id_from_items(items))
        if not invoice.supplier:
            raise frappe.ValidationError("Could not determine supplier from ProcureUAT data")
        
        invoice.posting_date = getdate(requisition['created_at']) if requisition['created_at'] else getdate()
        invoice.due_date = getdate(requisition['delivery_date']) if requisition['delivery_date'] else None
        invoice.bill_no = requisition.get('invoice_number')
        invoice.bill_date = getdate(requisition['invoice_generated_at']) if requisition.get('invoice_generated_at') else None
        invoice.remarks = requisition.get('remark', f"Synced from ProcureUAT Order {requisition['id']}")
        invoice.status = convert_procureuat_status_to_erpnext(requisition.get('order_status', 1))
        invoice.docstatus = convert_procureuat_acknowledgement_to_erpnext(requisition.get('acknowledgement', 0))
        
        # Set custom fields
        invoice.custom_external_order_id = requisition['id']
        invoice.custom_gst_percentage = float(requisition.get('gst_percentage', 5))
        invoice.custom_order_code = requisition.get('order_code', '')
        invoice.custom_entity_id = requisition.get('entity', '')
        invoice.custom_last_sync = now_datetime()
        invoice.custom_sync_status = "Synced"
        
        # Add items
        total_before_tax = 0
        total_tax = 0
        
        for item_data in items:
            item = invoice.append("items")
            
            # Map item fields
            item.item_code = get_item_code_from_product_id(item_data.get('product_id'))
            if not item.item_code:
                # Create a placeholder item if not found
                item.item_code = f"ITEM-{item_data.get('product_id', 'UNKNOWN')}"
                item.item_name = f"Product {item_data.get('product_id', 'Unknown')}"
            
            item.qty = flt(item_data.get('quantity', 1))
            item.rate = flt(item_data.get('unit_rate', 0))
            item.amount = flt(item_data.get('cost', 0))
            item.uom = item_data.get('uom', 'Nos')
            
            # Set custom fields
            item.custom_gst_amount = flt(item_data.get('gst_amt', 0))
            item.custom_vendor_id = item_data.get('vendor_id')
            item.custom_category_id = item_data.get('category_id')
            item.custom_subcategory_id = item_data.get('subcategory_id')
            item.custom_external_item_id = item_data.get('id')
            
            total_before_tax += item.amount
            total_tax += item.custom_gst_amount
        
        # Set totals
        invoice.net_total = total_before_tax
        invoice.total_taxes_and_charges = total_tax
        invoice.grand_total = total_before_tax + total_tax
        
        # Generate appropriate name
        suggested_name = generate_erpnext_invoice_name(requisition['order_name'])
        
        # Save the invoice
        invoice.save()
        
        # Submit if the order is approved in ProcureUAT
        if requisition.get('acknowledgement') == 1:
            invoice.submit()
        
        # Update sync log
        update_sync_log(sync_log, "Completed", 
                       f"Created ERPNext Invoice: {invoice.name}")
        
        return {
            'success': True,
            'message': f"Successfully created ERPNext Invoice: {invoice.name}",
            'invoice_name': invoice.name,
            'external_order_id': requisition['id']
        }
        
    except Exception as e:
        update_sync_log(sync_log, "Failed", f"Error creating invoice: {str(e)}")
        raise e

def update_existing_erpnext_invoice(invoice_name, order_data, sync_log):
    """
    Update an existing Purchase Invoice in ERPNext with ProcureUAT data
    
    Args:
        invoice_name (str): Name of existing Purchase Invoice
        order_data (dict): ProcureUAT order data
        sync_log: Invoice Sync Log document
        
    Returns:
        dict: Update result
    """
    try:
        requisition = order_data['requisition']
        items = order_data['items']
        
        # Get existing invoice
        invoice = frappe.get_doc("Purchase Invoice", invoice_name)
        
        # Only update if not submitted or if we have permission
        if invoice.docstatus == 1:
            # For submitted invoices, we can only update certain fields
            invoice.custom_last_sync = now_datetime()
            invoice.custom_sync_status = "Synced"
            
            # Update bill details if changed
            if requisition.get('invoice_number') and requisition['invoice_number'] != invoice.bill_no:
                invoice.bill_no = requisition['invoice_number']
            
            if requisition.get('invoice_generated_at'):
                new_bill_date = getdate(requisition['invoice_generated_at'])
                if new_bill_date != invoice.bill_date:
                    invoice.bill_date = new_bill_date
        
        else:
            # For draft invoices, we can update more fields
            invoice.due_date = getdate(requisition['delivery_date']) if requisition['delivery_date'] else invoice.due_date
            invoice.bill_no = requisition.get('invoice_number', invoice.bill_no)
            invoice.bill_date = getdate(requisition['invoice_generated_at']) if requisition.get('invoice_generated_at') else invoice.bill_date
            invoice.remarks = requisition.get('remark', invoice.remarks)
            invoice.custom_gst_percentage = float(requisition.get('gst_percentage', invoice.custom_gst_percentage or 5))
            invoice.custom_last_sync = now_datetime()
            invoice.custom_sync_status = "Synced"
            
            # Update item quantities and rates if changed
            for invoice_item in invoice.items:
                external_item_id = invoice_item.get('custom_external_item_id')
                if external_item_id:
                    # Find corresponding item in ProcureUAT data
                    matching_item = next((item for item in items if item['id'] == external_item_id), None)
                    if matching_item:
                        invoice_item.qty = flt(matching_item.get('quantity', invoice_item.qty))
                        invoice_item.rate = flt(matching_item.get('unit_rate', invoice_item.rate))
                        invoice_item.amount = flt(matching_item.get('cost', invoice_item.amount))
                        invoice_item.custom_gst_amount = flt(matching_item.get('gst_amt', invoice_item.custom_gst_amount))
        
        # Save the invoice
        invoice.save()
        
        # Update sync log
        update_sync_log(sync_log, "Completed", 
                       f"Updated ERPNext Invoice: {invoice.name}")
        
        return {
            'success': True,
            'message': f"Successfully updated ERPNext Invoice: {invoice.name}",
            'invoice_name': invoice.name,
            'external_order_id': requisition['id']
        }
        
    except Exception as e:
        update_sync_log(sync_log, "Failed", f"Error updating invoice: {str(e)}")
        raise e

def get_procureuat_order_data(external_order_id):
    """
    Get complete order data from ProcureUAT including requisition and items
    
    Args:
        external_order_id (int): ProcureUAT purchase requisition ID
        
    Returns:
        dict: Complete order data or None if not found
    """
    try:
        with get_external_db_connection() as conn:
            with conn.cursor() as cursor:
                # Get purchase requisition
                cursor.execute("""
                    SELECT * FROM purchase_requisitions 
                    WHERE id = %s
                """, (external_order_id,))
                
                requisition = cursor.fetchone()
                if not requisition:
                    return None
                
                # Get purchase order items
                cursor.execute("""
                    SELECT * FROM purchase_order_items 
                    WHERE purchase_order_id = %s
                    ORDER BY id
                """, (external_order_id,))
                
                items = cursor.fetchall()
                
                return {
                    'requisition': requisition,
                    'items': items
                }
                
    except Exception as e:
        frappe.logger().error(f"Error fetching ProcureUAT order data: {str(e)}")
        return None

def get_vendor_id_from_items(items):
    """
    Get vendor ID from the first item that has one
    
    Args:
        items (list): List of item dictionaries
        
    Returns:
        int: Vendor ID or None
    """
    for item in items:
        if item.get('vendor_id'):
            return item['vendor_id']
    return None

def get_item_code_from_product_id(product_id):
    """
    Get ERPNext item code from ProcureUAT product ID
    This would typically involve a lookup table or API
    For now, return a generated item code
    
    Args:
        product_id (int): ProcureUAT product ID
        
    Returns:
        str: ERPNext item code
    """
    if not product_id:
        return None
    
    # Check if we have a mapping in custom fields
    items = frappe.get_all("Item", 
                          filters={"custom_external_product_id": product_id},
                          fields=["item_code"])
    if items:
        return items[0].item_code
    
    # Return generated item code
    return f"PROC-{product_id}"

def create_sync_log(reference_name, sync_direction):
    """
    Create a new Invoice Sync Log entry
    
    Args:
        reference_name (str): Reference name (invoice or external ID)
        sync_direction (str): Direction of sync
        
    Returns:
        Invoice Sync Log document
    """
    sync_log = frappe.new_doc("Invoice Sync Log")
    sync_log.invoice_name = reference_name
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
def sync_orders_from_procureuat(limit=10, filters=None):
    """
    Sync multiple purchase requisitions from ProcureUAT to ERPNext
    
    Args:
        limit (int): Number of orders to sync
        filters (dict): Filters for ProcureUAT orders
        
    Returns:
        dict: Bulk sync results
    """
    try:
        if isinstance(filters, str):
            filters = json.loads(filters) if filters else {}
        
        # Get orders from ProcureUAT
        orders = get_procureuat_purchase_requisitions(limit=limit, filters=filters)
        
        results = []
        success_count = 0
        failed_count = 0
        
        for order in orders:
            try:
                result = sync_order_from_procureuat(order['id'])
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
                    'external_order_id': order['id']
                })
        
        return {
            'success': failed_count == 0,
            'total': len(orders),
            'success_count': success_count,
            'failed_count': failed_count,
            'results': results
        }
        
    except Exception as e:
        frappe.logger().error(f"Error in bulk sync from ProcureUAT: {str(e)}")
        return {
            'success': False,
            'message': f"Bulk sync failed: {str(e)}"
        }