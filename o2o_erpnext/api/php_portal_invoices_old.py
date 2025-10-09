"""
PHP Portal Invoices API
Provides API endpoints for fetching invoice data from remote PHP Portal database
"""
import frappe
from frappe import _
import traceback
import json
from datetime import datetime, timedelta
from o2o_erpnext.config.external_db_updated import get_external_db_connection


@frappe.whitelist()
def get_recent_portal_invoices(limit=500, status_filter=None, date_from=None, date_to=None):
    """
    Get recent invoices from PHP Portal database
    
    Args:
        limit (int): Maximum number of invoices to fetch
        status_filter (str): Filter by invoice status
        date_from (str): Start date filter
        date_to (str): End date filter
        
    Returns:
        dict: Success status and invoice data
    """
    try:
        with get_external_db_connection() as conn:
            with conn.cursor() as cursor:
                # Build the query
                base_query = """
                    SELECT DISTINCT
                        pr.id,
                        pr.order_code as invoice_number,
                        pr.entity as customer_name,
                        pr.subentity_id as customer_id,
                        pr.created_at as created_date,
                        pr.delivery_date as due_date,
                        pr.order_status,
                        pr.invoice_number as portal_invoice_number,
                        pr.invoice_generated,
                        pr.invoice_generated_at,
                        pr.gst_percentage,
                        pr.remark,
                        pr.acknowledgement,
                        pr.status,
                        'Portal Vendor' as vendor_name,
                        'portal@vendor.com' as customer_email,
                        COUNT(poi.id) as item_count,
                        SUM(poi.total_amt) as total_amount
                    FROM purchase_requisitions pr
                    LEFT JOIN purchase_order_items poi ON pr.id = poi.purchase_order_id
                    WHERE pr.is_delete = 0
                """
                
                params = []
                
                # Add filters
                if status_filter:
                    base_query += " AND pr.status = %s"
                    params.append(status_filter)
                
                if date_from:
                    base_query += " AND DATE(pr.created_at) >= %s"
                    params.append(date_from)
                
                if date_to:
                    base_query += " AND DATE(pr.created_at) <= %s"
                    params.append(date_to)
                
                # Group and order
                base_query += """
                    GROUP BY pr.id
                    ORDER BY pr.created_at DESC
                    LIMIT %s
                """
                params.append(int(limit))
                
                cursor.execute(base_query, params)
                raw_invoices = cursor.fetchall()
                
                # Get total count without limit
                count_query = """
                    SELECT COUNT(DISTINCT pr.id) as total_count
                    FROM purchase_requisitions pr
                    LEFT JOIN vendors v ON pr.vendor_id = v.id
                    WHERE pr.is_delete = 0
                """
                
                count_params = []
                if status_filter:
                    count_query += " AND pr.status = %s"
                    count_params.append(status_filter)
                
                if date_from:
                    count_query += " AND DATE(pr.created_at) >= %s"
                    count_params.append(date_from)
                
                if date_to:
                    count_query += " AND DATE(pr.created_at) <= %s"
                    count_params.append(date_to)
                
                cursor.execute(count_query, count_params)
                total_result = cursor.fetchone()
                total_count = total_result['total_count'] if total_result else 0
                
                # Process and format invoice data
                processed_invoices = []
                for invoice in raw_invoices:
                    processed_invoice = {
                        'id': invoice['id'],
                        'invoice_number': invoice['invoice_number'] or f"PR-{invoice['id']}",
                        'portal_invoice_number': invoice['portal_invoice_number'] or '',
                        'customer_name': invoice['customer_name'] or 'Unknown Customer',
                        'customer_id': invoice['customer_id'],
                        'customer_email': invoice['customer_email'] or '',
                        'vendor_name': invoice['vendor_name'] or 'Unknown Vendor',
                        'created_date': invoice['created_date'].strftime('%Y-%m-%d %H:%M:%S') if invoice['created_date'] else '',
                        'due_date': invoice['due_date'].strftime('%Y-%m-%d') if invoice['due_date'] else '',
                        'amount': float(invoice['total_amount']) if invoice['total_amount'] else 0.0,
                        'total_line_amount': float(invoice['total_amount']) if invoice['total_amount'] else 0.0,
                        'status': map_portal_status(invoice['status']),
                        'original_status': invoice['status'],
                        'order_status': invoice['order_status'],
                        'gst_percentage': float(invoice['gst_percentage']) if invoice['gst_percentage'] else 0.0,
                        'item_count': invoice['item_count'] or 0,
                        'invoice_generated': bool(invoice['invoice_generated']),
                        'invoice_generated_at': invoice['invoice_generated_at'].strftime('%Y-%m-%d %H:%M:%S') if invoice['invoice_generated_at'] else '',
                        'remark': invoice['remark'] or '',
                        'acknowledgement': invoice['acknowledgement'] or '',
                        'is_overdue': is_invoice_overdue(invoice['due_date'], invoice['status']),
                        'days_until_due': calculate_days_until_due(invoice['due_date'], invoice['status']),
                        'formatted_amount': format_currency_display(invoice['total_amount']),
                        'priority': calculate_invoice_priority(invoice)
                    }
                    processed_invoices.append(processed_invoice)
                
                # Add summary statistics
                summary_stats = calculate_invoice_statistics(processed_invoices)
                
                return {
                    'success': True,
                    'invoices': processed_invoices,
                    'total_count': total_count,
                    'returned_count': len(processed_invoices),
                    'summary': summary_stats
                }
                
    except Exception as e:
        frappe.log_error(
            message=f"PHP Portal invoices fetch error: {str(e)}\n{traceback.format_exc()}",
            title="PHP Portal Invoices API Error"
        )
        return {
            'success': False,
            'error': f'Failed to fetch portal invoices: {str(e)}',
            'invoices': [],
            'total_count': 0
        }


@frappe.whitelist()
def get_invoice_details(invoice_id):
    """
    Get detailed information for a specific invoice
    
    Args:
        invoice_id (str): Invoice ID to fetch details for
        
    Returns:
        dict: Detailed invoice information
    """
    try:
        with get_external_db_connection() as conn:
            with conn.cursor() as cursor:
                # Get invoice header details
                header_query = """
                    SELECT 
                        pr.*,
                        v.name as vendor_name,
                        v.email as vendor_email,
                        v.contact_number as vendor_phone,
                        v.address as vendor_address,
                        v.gstn as vendor_gstn
                    FROM purchase_requisitions pr
                    LEFT JOIN vendors v ON pr.vendor_id = v.id
                    WHERE pr.id = %s
                """
                
                cursor.execute(header_query, (invoice_id,))
                header = cursor.fetchone()
                
                if not header:
                    return {
                        'success': False,
                        'error': f'Invoice {invoice_id} not found'
                    }
                
                # Get invoice line items
                items_query = """
                    SELECT 
                        poi.*,
                        COALESCE(poi.product_name, 'Unknown Product') as product_name,
                        COALESCE(poi.category_name, 'Unknown Category') as category_name,
                        COALESCE(poi.subcategory_name, 'Unknown Subcategory') as subcategory_name
                    FROM purchase_order_items poi
                    WHERE poi.purchase_order_id = %s
                    ORDER BY poi.id
                """
                
                cursor.execute(items_query, (invoice_id,))
                items = cursor.fetchall()
                
                # Process the data
                processed_header = {
                    'id': header['id'],
                    'order_code': header['order_code'],
                    'entity': header['entity'],
                    'entity_id': header['entity_id'],
                    'vendor_name': header['vendor_name'],
                    'vendor_email': header['vendor_email'],
                    'vendor_phone': header['vendor_phone'],
                    'vendor_address': header['vendor_address'],
                    'vendor_gstn': header['vendor_gstn'],
                    'created_at': header['created_at'].strftime('%Y-%m-%d %H:%M:%S') if header['created_at'] else '',
                    'delivery_date': header['delivery_date'].strftime('%Y-%m-%d') if header['delivery_date'] else '',
                    'total_amount': float(header['total_amount']) if header['total_amount'] else 0.0,
                    'gst_percentage': float(header['gst_percentage']) if header['gst_percentage'] else 0.0,
                    'order_status': header['order_status'],
                    'invoice_number': header['invoice_number'],
                    'invoice_generated': bool(header['invoice_generated']),
                    'remark': header['remark'] or '',
                    'acknowledgement': header['acknowledgement'] or ''
                }
                
                processed_items = []
                for item in items:
                    processed_item = {
                        'id': item['id'],
                        'product_name': item['product_name'],
                        'category_name': item['category_name'],
                        'subcategory_name': item['subcategory_name'],
                        'quantity': float(item['quantity']) if item['quantity'] else 0.0,
                        'unit_rate': float(item['unit_rate']) if item['unit_rate'] else 0.0,
                        'uom': item['uom'] or 'Nos',
                        'total_amount': float(item['total_amt']) if item['total_amt'] else 0.0,
                        'gst_amount': float(item['gst_amt']) if item['gst_amt'] else 0.0,
                        'cost': float(item['cost']) if item['cost'] else 0.0,
                        'status': item['status'] or 'pending',
                        'created_at': item['created_at'].strftime('%Y-%m-%d %H:%M:%S') if item['created_at'] else ''
                    }
                    processed_items.append(processed_item)
                
                return {
                    'success': True,
                    'invoice': processed_header,
                    'items': processed_items,
                    'item_count': len(processed_items),
                    'total_items_amount': sum(item['total_amount'] for item in processed_items)
                }
                
    except Exception as e:
        frappe.log_error(
            message=f"Invoice details fetch error for {invoice_id}: {str(e)}\n{traceback.format_exc()}",
            title="Invoice Details API Error"
        )
        return {
            'success': False,
            'error': f'Failed to fetch invoice details: {str(e)}'
        }


@frappe.whitelist()
def export_invoices_to_excel(filters=None):
    """
    Export invoices to Excel format
    
    Args:
        filters (dict): Filters to apply
        
    Returns:
        dict: Excel file URL or error
    """
    try:
        # Get invoice data
        result = get_recent_portal_invoices(limit=5000)
        
        if not result['success']:
            return result
        
        invoices = result['invoices']
        
        # Prepare data for Excel export
        excel_data = []
        for invoice in invoices:
            excel_data.append({
                'Invoice ID': invoice['id'],
                'Invoice Number': invoice['invoice_number'],
                'Customer': invoice['customer_name'],
                'Vendor': invoice['vendor_name'],
                'Created Date': invoice['created_date'],
                'Due Date': invoice['due_date'],
                'Amount': invoice['amount'],
                'Status': invoice['status'],
                'GST %': invoice['gst_percentage'],
                'Items Count': invoice['item_count'],
                'Remarks': invoice['remark']
            })
        
        # Create Excel file (simplified for now)
        filename = f"portal_invoices_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        return {
            'success': True,
            'message': f'Excel export prepared for {len(excel_data)} invoices',
            'filename': filename,
            'record_count': len(excel_data)
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f'Excel export failed: {str(e)}'
        }


# Helper Functions
def map_portal_status(original_status):
    """Map portal status to standardized status"""
    status_mapping = {
        'pending': 'pending',
        'approved': 'pending',
        'completed': 'paid',
        'cancelled': 'cancelled',
        'draft': 'draft',
        'rejected': 'cancelled'
    }
    
    return status_mapping.get(original_status.lower() if original_status else '', 'pending')


def is_invoice_overdue(due_date, status):
    """Check if invoice is overdue"""
    if not due_date or status.lower() in ['paid', 'completed', 'cancelled']:
        return False
    
    try:
        due = datetime.strptime(str(due_date)[:10], '%Y-%m-%d') if isinstance(due_date, str) else due_date
        return due < datetime.now().date()
    except:
        return False


def calculate_days_until_due(due_date, status):
    """Calculate days until due date"""
    if not due_date or status.lower() in ['paid', 'completed', 'cancelled']:
        return None
    
    try:
        due = datetime.strptime(str(due_date)[:10], '%Y-%m-%d').date() if isinstance(due_date, str) else due_date.date()
        today = datetime.now().date()
        delta = (due - today).days
        return delta
    except:
        return None


def format_currency_display(amount):
    """Format currency for display"""
    try:
        amount_float = float(amount) if amount else 0.0
        if amount_float >= 100000:
            return f"₹{amount_float/100000:.1f}L"
        elif amount_float >= 1000:
            return f"₹{amount_float/1000:.1f}K"
        else:
            return f"₹{amount_float:.0f}"
    except:
        return "₹0"


def calculate_invoice_priority(invoice):
    """Calculate priority score for invoice"""
    priority = 0
    
    # Amount factor
    amount = float(invoice['amount']) if invoice['amount'] else 0
    if amount > 100000:
        priority += 3
    elif amount > 10000:
        priority += 2
    else:
        priority += 1
    
    # Status factor
    status = invoice['status']
    if status in ['pending', 'approved']:
        priority += 2
    elif status == 'completed':
        priority += 1
    
    # Due date factor
    if invoice['due_date']:
        try:
            due_date = datetime.strptime(str(invoice['due_date'])[:10], '%Y-%m-%d').date()
            days_diff = (due_date - datetime.now().date()).days
            if days_diff < 0:  # Overdue
                priority += 3
            elif days_diff <= 7:  # Due soon
                priority += 2
        except:
            pass
    
    return min(priority, 10)  # Cap at 10


def calculate_invoice_statistics(invoices):
    """Calculate summary statistics for invoices"""
    if not invoices:
        return {}
    
    total_amount = sum(float(inv['amount']) for inv in invoices)
    status_counts = {}
    overdue_count = 0
    
    for invoice in invoices:
        status = invoice['status']
        status_counts[status] = status_counts.get(status, 0) + 1
        if invoice['is_overdue']:
            overdue_count += 1
    
    return {
        'total_invoices': len(invoices),
        'total_amount': total_amount,
        'average_amount': total_amount / len(invoices),
        'status_breakdown': status_counts,
        'overdue_count': overdue_count,
        'largest_invoice': max(invoices, key=lambda x: float(x['amount']) or 0)['amount'],
        'smallest_invoice': min(invoices, key=lambda x: float(x['amount']) or 0)['amount']
    }