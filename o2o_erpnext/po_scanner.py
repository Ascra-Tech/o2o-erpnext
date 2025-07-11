# apps/o2o_erpnext/o2o_erpnext/po_scanner.py

import frappe
from frappe import _

@frappe.whitelist()
def get_partial_purchase_orders():
    """
    Get all Purchase Orders that are partially received
    Returns POs where some items are received and some are pending
    """
    try:
        # Get all POs that are not fully received
        pos = frappe.get_all(
            'Purchase Order',
            filters={
                'status': ['in', ['To Receive', 'To Receive and Bill']],
                'docstatus': 1
            },
            fields=['name', 'supplier', 'transaction_date', 'grand_total', 'status', 'company'],
            order_by='transaction_date desc'
        )
        
        partial_pos = []
        
        for po in pos:
            # Get PO items with received quantities
            items = frappe.get_all(
                'Purchase Order Item',
                filters={'parent': po.name},
                fields=['qty', 'received_qty', 'item_code', 'item_name', 'rate', 'amount']
            )
            
            has_received = False
            has_pending = False
            total_items = len(items)
            received_items = 0
            pending_items = 0
            
            for item in items:
                received_qty = item.received_qty or 0
                ordered_qty = item.qty or 0
                
                if received_qty > 0:
                    has_received = True
                    if received_qty >= ordered_qty:
                        received_items += 1
                
                if received_qty < ordered_qty:
                    has_pending = True
                    pending_items += 1
            
            # If it has both received and pending items, it's partial
            if has_received and has_pending:
                po_detail = po.copy()
                po_detail['total_items'] = total_items
                po_detail['received_items'] = received_items
                po_detail['pending_items'] = pending_items
                po_detail['completion_percentage'] = round((received_items / total_items) * 100, 2) if total_items > 0 else 0
                
                # Add pending item details
                po_detail['pending_item_details'] = []
                for item in items:
                    received_qty = item.received_qty or 0
                    ordered_qty = item.qty or 0
                    
                    if received_qty < ordered_qty:
                        po_detail['pending_item_details'].append({
                            'item_code': item.item_code,
                            'item_name': item.item_name,
                            'ordered_qty': ordered_qty,
                            'received_qty': received_qty,
                            'pending_qty': ordered_qty - received_qty,
                            'rate': item.rate,
                            'pending_amount': (ordered_qty - received_qty) * item.rate
                        })
                
                partial_pos.append(po_detail)
        
        return {
            'status': 'success',
            'data': partial_pos,
            'total_partial_pos': len(partial_pos),
            'message': f'Found {len(partial_pos)} partial Purchase Orders'
        }
        
    except Exception as e:
        frappe.log_error(f"Error in get_partial_purchase_orders: {str(e)}", "PO Scanner Error")
        return {
            'status': 'error',
            'message': f'Error scanning Purchase Orders: {str(e)}'
        }

@frappe.whitelist()
def get_po_item_status(po_name):
    """
    Get detailed item status for a specific Purchase Order
    """
    try:
        if not po_name:
            return {'status': 'error', 'message': 'Purchase Order name is required'}
        
        # Check if PO exists
        if not frappe.db.exists('Purchase Order', po_name):
            return {'status': 'error', 'message': 'Purchase Order not found'}
        
        # Get PO details
        po = frappe.get_doc('Purchase Order', po_name)
        
        items = frappe.get_all(
            'Purchase Order Item',
            filters={'parent': po_name},
            fields=['item_code', 'item_name', 'qty', 'received_qty', 'rate', 'amount', 'uom'],
            order_by='idx'
        )
        
        item_status = []
        total_ordered_amount = 0
        total_received_amount = 0
        
        for item in items:
            received_qty = item.received_qty or 0
            ordered_qty = item.qty or 0
            
            # Determine status
            if received_qty == 0:
                status = "Not Received"
                status_color = "red"
            elif received_qty >= ordered_qty:
                status = "Fully Received"
                status_color = "green"
            else:
                status = "Partially Received"
                status_color = "orange"
            
            received_amount = received_qty * item.rate
            pending_amount = (ordered_qty - received_qty) * item.rate
            
            total_ordered_amount += item.amount
            total_received_amount += received_amount
            
            item_status.append({
                'item_code': item.item_code,
                'item_name': item.item_name,
                'uom': item.uom,
                'ordered_qty': ordered_qty,
                'received_qty': received_qty,
                'pending_qty': ordered_qty - received_qty,
                'rate': item.rate,
                'ordered_amount': item.amount,
                'received_amount': received_amount,
                'pending_amount': pending_amount,
                'status': status,
                'status_color': status_color,
                'completion_percentage': round((received_qty / ordered_qty) * 100, 2) if ordered_qty > 0 else 0
            })
        
        return {
            'status': 'success',
            'data': {
                'po_name': po_name,
                'supplier': po.supplier,
                'transaction_date': po.transaction_date,
                'grand_total': po.grand_total,
                'po_status': po.status,
                'items': item_status,
                'summary': {
                    'total_items': len(items),
                    'total_ordered_amount': total_ordered_amount,
                    'total_received_amount': total_received_amount,
                    'total_pending_amount': total_ordered_amount - total_received_amount,
                    'overall_completion_percentage': round((total_received_amount / total_ordered_amount) * 100, 2) if total_ordered_amount > 0 else 0
                }
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Error in get_po_item_status: {str(e)}", "PO Scanner Error")
        return {
            'status': 'error',
            'message': f'Error getting PO item status: {str(e)}'
        }

@frappe.whitelist()
def get_po_statistics():
    """
    Get overall statistics for Purchase Orders
    """
    try:
        # Get all submitted POs
        all_pos = frappe.get_all(
            'Purchase Order',
            filters={'docstatus': 1},
            fields=['name', 'status']
        )
        
        # Count by status
        status_counts = {}
        for po in all_pos:
            status = po.status
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Get partial POs count
        partial_result = get_partial_purchase_orders()
        partial_count = partial_result.get('total_partial_pos', 0) if partial_result.get('status') == 'success' else 0
        
        return {
            'status': 'success',
            'data': {
                'total_pos': len(all_pos),
                'partial_pos': partial_count,
                'status_breakdown': status_counts,
                'partial_percentage': round((partial_count / len(all_pos)) * 100, 2) if len(all_pos) > 0 else 0
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Error in get_po_statistics: {str(e)}", "PO Scanner Error")
        return {
            'status': 'error',
            'message': f'Error getting PO statistics: {str(e)}'
        }