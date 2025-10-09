import frappe
import pymysql
from frappe import _
from datetime import datetime
from o2o_erpnext.config.external_db_updated import get_external_db_connection

def safe_date_format(date_value, format_string='%Y-%m-%d %H:%M:%S'):
    """
    Safely format a date value that might be a string or datetime object
    
    Args:
        date_value: The date value to format (could be datetime, str, or None)
        format_string: The format string to use
        
    Returns:
        str: Formatted date string or empty string if invalid
    """
    if not date_value:
        return ''
    
    # If it's already a string, return it as is (assuming it's already formatted)
    if isinstance(date_value, str):
        return date_value
    
    # If it's a datetime object, format it
    if isinstance(date_value, datetime):
        return date_value.strftime(format_string)
    
    # Try to convert to datetime if it's some other type
    try:
        if hasattr(date_value, 'strftime'):
            return date_value.strftime(format_string)
        else:
            # Try to parse as string and then format
            dt = datetime.strptime(str(date_value), '%Y-%m-%d %H:%M:%S')
            return dt.strftime(format_string)
    except:
        return str(date_value) if date_value else ''

@frappe.whitelist()
def get_recent_portal_invoices(limit=500, status_filter=None, date_from=None, date_to=None):
    """
    Fetch recent portal invoices from the external database
    
    Args:
        limit (int): Number of invoices to fetch (default: 500)
        status_filter (str): Filter by status (optional)
        date_from (str): Start date filter (optional)
        date_to (str): End date filter (optional)
        
    Returns:
        dict: Success status and invoice data
    """
    try:
        with get_external_db_connection() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                # Simplified query to get purchase requisitions first
                query = """
                SELECT 
                    pr.id as requisition_id,
                    pr.order_name,
                    pr.entity,
                    pr.subentity_id,
                    pr.delivery_date,
                    pr.validity_date,
                    pr.order_code,
                    pr.address,
                    pr.remark,
                    pr.acknowledgement,
                    pr.order_status,
                    pr.status as requisition_status,
                    pr.created_at as requisition_date,
                    pr.created_by,
                    pr.invoice_number,
                    pr.invoice_generated,
                    pr.invoice_generated_at
                FROM purchase_requisitions pr
                WHERE pr.is_delete = 0 
                AND pr.status = 'active'
                """
                
                params = []
                
                # Add filters
                if status_filter and status_filter != 'active':
                    query += " AND pr.status = %s"
                    params.append(status_filter)
                
                if date_from:
                    query += " AND DATE(pr.created_at) >= %s"
                    params.append(date_from)
                
                if date_to:
                    query += " AND DATE(pr.created_at) <= %s"
                    params.append(date_to)
                
                query += """
                ORDER BY pr.created_at DESC
                LIMIT %s
                """
                params.append(int(limit))
                
                cursor.execute(query, params)
                requisitions = cursor.fetchall()
                
                # Get detailed items for each requisition
                invoices = []
                for req in requisitions:
                    # Get totals for this requisition
                    totals_query = """
                    SELECT 
                        COUNT(poi.id) as total_items,
                        SUM(poi.total_amt) as total_amount,
                        SUM(poi.gst_amt) as total_gst,
                        GROUP_CONCAT(DISTINCT v.name SEPARATOR ', ') as vendor_names,
                        GROUP_CONCAT(DISTINCT v.code SEPARATOR ', ') as vendor_codes
                    FROM purchase_order_items poi
                    LEFT JOIN vendors v ON poi.vendor_id = v.id
                    WHERE poi.purchase_order_id = %s
                    """
                    
                    cursor.execute(totals_query, (req['requisition_id'],))
                    totals = cursor.fetchone()
                    
                    # Get items for this requisition
                    items_query = """
                    SELECT 
                        poi.id as item_id,
                        poi.category_id,
                        poi.subcategory_id,
                        poi.product_id,
                        poi.vendor_id,
                        poi.brand_id,
                        poi.quantity,
                        poi.unit_rate,
                        poi.uom,
                        poi.total_amt,
                        poi.gst_amt,
                        poi.cost,
                        poi.status as item_status,
                        v.name as vendor_name,
                        v.code as vendor_code,
                        v.email as vendor_email,
                        v.gstn as vendor_gstn
                    FROM purchase_order_items poi
                    LEFT JOIN vendors v ON poi.vendor_id = v.id
                    WHERE poi.purchase_order_id = %s
                    ORDER BY poi.id
                    """
                    
                    cursor.execute(items_query, (req['requisition_id'],))
                    items = cursor.fetchall()
                    
                    # Process items
                    processed_items = []
                    for item in items:
                        processed_items.append({
                            'item_id': item['item_id'],
                            'category_id': item['category_id'],
                            'subcategory_id': item['subcategory_id'],
                            'product_id': item['product_id'],
                            'vendor_id': item['vendor_id'],
                            'brand_id': item['brand_id'],
                            'quantity': float(item['quantity']) if item['quantity'] else 0.0,
                            'unit_rate': float(item['unit_rate']) if item['unit_rate'] else 0.0,
                            'uom': item['uom'] or 'Nos',
                            'total_amount': float(item['total_amt']) if item['total_amt'] else 0.0,
                            'gst_amount': float(item['gst_amt']) if item['gst_amt'] else 0.0,
                            'cost': float(item['cost']) if item['cost'] else 0.0,
                            'status': item['item_status'],
                            'vendor_name': item['vendor_name'] or 'Unknown Vendor',
                            'vendor_code': item['vendor_code'] or '',
                            'vendor_email': item['vendor_email'] or '',
                            'vendor_gstn': item['vendor_gstn'] or ''
                        })
                    
                    # Create invoice object
                    invoice = {
                        'invoice_id': req['requisition_id'],
                        'invoice_number': req['order_code'],
                        'order_name': req['order_name'],
                        'customer_name': req['entity'],
                        'customer_id': req['subentity_id'],
                        'created_date': safe_date_format(req['requisition_date']),
                        'due_date': safe_date_format(req['delivery_date'], '%Y-%m-%d'),
                        'validity_date': safe_date_format(req['validity_date'], '%Y-%m-%d'),
                        'address': req['address'] or '',
                        'remark': req['remark'] or '',
                        'acknowledgement': req['acknowledgement'],
                        'order_status': req['order_status'],
                        'status': req['requisition_status'],
                        'created_by': req['created_by'],
                        'portal_invoice_number': req['invoice_number'] or '',
                        'invoice_generated': bool(req['invoice_generated']),
                        'invoice_generated_at': safe_date_format(req['invoice_generated_at']),
                        'total_items': totals['total_items'] or 0,
                        'total_amount': float(totals['total_amount']) if totals['total_amount'] else 0.0,
                        'total_gst': float(totals['total_gst']) if totals['total_gst'] else 0.0,
                        'grand_total': float(totals['total_amount'] or 0) + float(totals['total_gst'] or 0),
                        'vendor_names': totals['vendor_names'] or 'No Vendors',
                        'vendor_codes': totals['vendor_codes'] or '',
                        'items': processed_items
                    }
                    
                    invoices.append(invoice)
                
                # Get statistics
                stats_query = """
                SELECT 
                    COUNT(DISTINCT pr.id) as total_invoices,
                    COUNT(DISTINCT poi.vendor_id) as total_vendors,
                    SUM(poi.total_amt) as total_value,
                    SUM(poi.gst_amt) as total_gst_value,
                    AVG(poi.total_amt) as avg_invoice_value,
                    MIN(pr.created_at) as oldest_invoice,
                    MAX(pr.created_at) as newest_invoice
                FROM purchase_requisitions pr
                LEFT JOIN purchase_order_items poi ON pr.id = poi.purchase_order_id
                WHERE pr.is_delete = 0 AND pr.status = 'active'
                """
                
                cursor.execute(stats_query)
                stats = cursor.fetchone()
                
                statistics = {
                    'total_invoices': stats['total_invoices'] or 0,
                    'total_vendors': stats['total_vendors'] or 0,
                    'total_value': float(stats['total_value']) if stats['total_value'] else 0.0,
                    'total_gst_value': float(stats['total_gst_value']) if stats['total_gst_value'] else 0.0,
                    'avg_invoice_value': float(stats['avg_invoice_value']) if stats['avg_invoice_value'] else 0.0,
                    'oldest_invoice': safe_date_format(stats['oldest_invoice'], '%Y-%m-%d'),
                    'newest_invoice': safe_date_format(stats['newest_invoice'], '%Y-%m-%d'),
                    'fetched_count': len(invoices)
                }
                
                return {
                    'success': True,
                    'message': f'Successfully fetched {len(invoices)} portal invoices',
                    'invoices': invoices,
                    'statistics': statistics,
                    'total_fetched': len(invoices)
                }
                
    except Exception as e:
        frappe.log_error(f"Error fetching portal invoices: {str(e)}")
        return {
            'success': False,
            'message': f'Error fetching portal invoices: {str(e)}',
            'invoices': [],
            'statistics': {},
            'total_fetched': 0
        }

@frappe.whitelist()
def get_portal_invoice_detail(invoice_id):
    """
    Get detailed information for a specific portal invoice
    
    Args:
        invoice_id (int): The invoice ID to fetch details for
        
    Returns:
        dict: Invoice details with all items
    """
    try:
        with get_external_db_connection() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                # Get invoice header
                header_query = """
                SELECT 
                    pr.*,
                    COUNT(poi.id) as total_items,
                    SUM(poi.total_amt) as total_amount,
                    SUM(poi.gst_amt) as total_gst
                FROM purchase_requisitions pr
                LEFT JOIN purchase_order_items poi ON pr.id = poi.purchase_order_id
                WHERE pr.id = %s AND pr.is_delete = 0
                GROUP BY pr.id
                """
                
                cursor.execute(header_query, (invoice_id,))
                header = cursor.fetchone()
                
                if not header:
                    return {
                        'success': False,
                        'message': 'Invoice not found',
                        'invoice': None
                    }
                
                # Get all items for this invoice
                items_query = """
                SELECT 
                    poi.*,
                    v.name as vendor_name,
                    v.code as vendor_code,
                    v.email as vendor_email,
                    v.gstn as vendor_gstn
                FROM purchase_order_items poi
                LEFT JOIN vendors v ON poi.vendor_id = v.id
                WHERE poi.purchase_order_id = %s
                ORDER BY poi.id
                """
                
                cursor.execute(items_query, (invoice_id,))
                items = cursor.fetchall()
                
                # Format the response
                invoice_detail = {
                    'header': dict(header),
                    'items': [dict(item) for item in items],
                    'summary': {
                        'total_items': header['total_items'],
                        'total_amount': float(header['total_amount']) if header['total_amount'] else 0.0,
                        'total_gst': float(header['total_gst']) if header['total_gst'] else 0.0,
                        'grand_total': float(header['total_amount'] or 0) + float(header['total_gst'] or 0)
                    }
                }
                
                return {
                    'success': True,
                    'message': 'Invoice details fetched successfully',
                    'invoice': invoice_detail
                }
                
    except Exception as e:
        frappe.log_error(f"Error fetching invoice detail: {str(e)}")
        return {
            'success': False,
            'message': f'Error fetching invoice detail: {str(e)}',
            'invoice': None
        }

@frappe.whitelist()
def test_portal_connection():
    """
    Test the portal database connection
    
    Returns:
        dict: Connection test results
    """
    try:
        with get_external_db_connection() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                # Test basic queries
                cursor.execute("SELECT COUNT(*) as total FROM purchase_requisitions WHERE is_delete = 0")
                req_count = cursor.fetchone()['total']
                
                cursor.execute("SELECT COUNT(*) as total FROM purchase_order_items")
                item_count = cursor.fetchone()['total']
                
                cursor.execute("SELECT COUNT(*) as total FROM vendors WHERE status = 'active'")
                vendor_count = cursor.fetchone()['total']
                
                return {
                    'success': True,
                    'message': 'Portal database connection successful',
                    'statistics': {
                        'purchase_requisitions': req_count,
                        'purchase_order_items': item_count,
                        'active_vendors': vendor_count
                    }
                }
                
    except Exception as e:
        return {
            'success': False,
            'message': f'Portal database connection failed: {str(e)}',
            'statistics': {}
        }

@frappe.whitelist()
def batch_import_invoices(batch_size=50, total_limit=500, date_from=None, date_to=None, skip_duplicates=1, update_existing=0):
    """
    Batch import invoices from portal to Purchase Invoice doctype
    
    Args:
        batch_size (int): Number of invoices per batch
        total_limit (int): Maximum total invoices to import
        date_from (str): Start date filter
        date_to (str): End date filter
        skip_duplicates (bool): Skip existing invoices
        update_existing (bool): Update existing invoices
        
    Returns:
        dict: Import results
    """
    try:
        # Get portal invoices
        portal_data = get_recent_portal_invoices(
            limit=total_limit,
            date_from=date_from,
            date_to=date_to
        )
        
        if not portal_data['success']:
            return portal_data
        
        invoices = portal_data['invoices']
        imported_count = 0
        skipped_count = 0
        error_count = 0
        
        for invoice in invoices:
            try:
                # Check if invoice already exists
                existing = frappe.get_all('Purchase Invoice', 
                                        filters={'title': invoice['invoice_number']},
                                        limit=1)
                
                if existing:
                    if skip_duplicates and not update_existing:
                        skipped_count += 1
                        continue
                    elif update_existing:
                        # Update existing invoice
                        doc = frappe.get_doc('Purchase Invoice', existing[0]['name'])
                        update_purchase_invoice_from_portal(doc, invoice)
                        doc.save()
                        imported_count += 1
                    else:
                        skipped_count += 1
                        continue
                else:
                    # Create new invoice
                    doc = create_purchase_invoice_from_portal(invoice)
                    if doc:
                        imported_count += 1
                    else:
                        error_count += 1
                        
            except Exception as e:
                frappe.log_error(f"Error importing invoice {invoice['invoice_number']}: {str(e)}")
                error_count += 1
                continue
        
        frappe.db.commit()
        
        return {
            'success': True,
            'message': f'Import completed. Imported: {imported_count}, Skipped: {skipped_count}, Errors: {error_count}',
            'imported_count': imported_count,
            'skipped_count': skipped_count,
            'error_count': error_count
        }
        
    except Exception as e:
        frappe.log_error(f"Batch import error: {str(e)}")
        return {
            'success': False,
            'message': f'Batch import failed: {str(e)}',
            'imported_count': 0,
            'skipped_count': 0,
            'error_count': 0
        }

@frappe.whitelist()
def fetch_single_invoice(invoice_number, create_if_not_exists=1, update_if_exists=0):
    """
    Fetch a single invoice by number from portal
    
    Args:
        invoice_number (str): Invoice number to fetch
        create_if_not_exists (bool): Create if not found locally
        update_if_exists (bool): Update if found locally
        
    Returns:
        dict: Operation result
    """
    try:
        # Search for the invoice in portal
        with get_external_db_connection() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                query = """
                SELECT pr.*, 
                       COUNT(poi.id) as total_items,
                       SUM(poi.total_amt) as total_amount,
                       SUM(poi.gst_amt) as total_gst,
                       GROUP_CONCAT(DISTINCT v.name SEPARATOR ', ') as vendor_names
                FROM purchase_requisitions pr
                LEFT JOIN purchase_order_items poi ON pr.id = poi.purchase_order_id
                LEFT JOIN vendors v ON poi.vendor_id = v.id
                WHERE pr.order_code = %s AND pr.is_delete = 0
                GROUP BY pr.id
                """
                
                cursor.execute(query, (invoice_number,))
                portal_invoice = cursor.fetchone()
                
                if not portal_invoice:
                    return {
                        'success': False,
                        'message': f'Invoice {invoice_number} not found in portal',
                        'invoice_name': None
                    }
                
                # Check if invoice exists locally
                existing = frappe.get_all('Purchase Invoice', 
                                        filters={'title': invoice_number},
                                        limit=1)
                
                if existing:
                    if update_if_exists:
                        # Update existing
                        doc = frappe.get_doc('Purchase Invoice', existing[0]['name'])
                        
                        # Format portal data
                        formatted_invoice = format_portal_invoice_data(portal_invoice)
                        update_purchase_invoice_from_portal(doc, formatted_invoice)
                        doc.save()
                        
                        return {
                            'success': True,
                            'message': f'Invoice {invoice_number} updated successfully',
                            'invoice_name': doc.name
                        }
                    else:
                        return {
                            'success': True,
                            'message': f'Invoice {invoice_number} already exists',
                            'invoice_name': existing[0]['name']
                        }
                else:
                    if create_if_not_exists:
                        # Create new
                        formatted_invoice = format_portal_invoice_data(portal_invoice)
                        doc = create_purchase_invoice_from_portal(formatted_invoice)
                        
                        if doc:
                            return {
                                'success': True,
                                'message': f'Invoice {invoice_number} created successfully',
                                'invoice_name': doc.name
                            }
                        else:
                            return {
                                'success': False,
                                'message': f'Failed to create invoice {invoice_number}',
                                'invoice_name': None
                            }
                    else:
                        return {
                            'success': False,
                            'message': f'Invoice {invoice_number} not found locally and creation disabled',
                            'invoice_name': None
                        }
                        
    except Exception as e:
        frappe.log_error(f"Error fetching single invoice: {str(e)}")
        return {
            'success': False,
            'message': f'Error: {str(e)}',
            'invoice_name': None
        }

@frappe.whitelist()
def import_multiple_invoices(invoice_ids):
    """
    Import multiple invoices by their portal IDs
    
    Args:
        invoice_ids (list): List of portal invoice IDs
        
    Returns:
        dict: Import results
    """
    try:
        if isinstance(invoice_ids, str):
            invoice_ids = frappe.parse_json(invoice_ids)
        
        imported_count = 0
        error_count = 0
        
        for invoice_id in invoice_ids:
            try:
                # Get invoice detail from portal
                detail_result = get_portal_invoice_detail(invoice_id)
                if detail_result['success']:
                    invoice_data = detail_result['invoice']['header']
                    
                    # Format and create invoice
                    formatted_invoice = format_portal_invoice_data(invoice_data)
                    doc = create_purchase_invoice_from_portal(formatted_invoice)
                    
                    if doc:
                        imported_count += 1
                    else:
                        error_count += 1
                else:
                    error_count += 1
                    
            except Exception as e:
                frappe.log_error(f"Error importing invoice ID {invoice_id}: {str(e)}")
                error_count += 1
                continue
        
        frappe.db.commit()
        
        return {
            'success': True,
            'message': f'Imported {imported_count} invoices, {error_count} errors',
            'imported_count': imported_count,
            'error_count': error_count
        }
        
    except Exception as e:
        frappe.log_error(f"Multiple import error: {str(e)}")
        return {
            'success': False,
            'message': f'Import failed: {str(e)}',
            'imported_count': 0,
            'error_count': len(invoice_ids) if invoice_ids else 0
        }

def format_portal_invoice_data(portal_invoice):
    """Format portal invoice data for Purchase Invoice creation"""
    return {
        'invoice_id': portal_invoice['id'],
        'invoice_number': portal_invoice['order_code'],
        'order_name': portal_invoice['order_name'],
        'customer_name': portal_invoice['entity'],
        'customer_id': portal_invoice['subentity_id'],
        'created_date': safe_date_format(portal_invoice['created_at']),
        'due_date': safe_date_format(portal_invoice['delivery_date'], '%Y-%m-%d'),
        'validity_date': safe_date_format(portal_invoice['validity_date'], '%Y-%m-%d'),
        'address': portal_invoice['address'] or '',
        'remark': portal_invoice['remark'] or '',
        'total_items': portal_invoice.get('total_items', 0),
        'total_amount': float(portal_invoice.get('total_amount', 0)),
        'total_gst': float(portal_invoice.get('total_gst', 0)),
        'vendor_names': portal_invoice.get('vendor_names', 'No Vendors')
    }

def create_purchase_invoice_from_portal(invoice_data):
    """Create a new Purchase Invoice from portal data"""
    try:
        doc = frappe.new_doc('Purchase Invoice')
        
        # Set basic fields
        doc.title = invoice_data['invoice_number']
        doc.supplier = get_or_create_supplier(invoice_data['vendor_names'])
        doc.posting_date = frappe.utils.today()
        doc.due_date = invoice_data.get('due_date') or frappe.utils.add_days(frappe.utils.today(), 30)
        
        # Add custom fields for portal reference
        if hasattr(doc, 'custom_portal_invoice_id'):
            doc.custom_portal_invoice_id = invoice_data['invoice_id']
        if hasattr(doc, 'custom_portal_order_name'):
            doc.custom_portal_order_name = invoice_data['order_name']
        if hasattr(doc, 'custom_customer_name'):
            doc.custom_customer_name = invoice_data['customer_name']
        
        # Add a basic item (you may need to customize this based on your item structure)
        doc.append('items', {
            'item_code': get_or_create_item('Portal Import Item'),
            'qty': invoice_data.get('total_items', 1),
            'rate': invoice_data.get('total_amount', 0),
            'amount': invoice_data.get('total_amount', 0)
        })
        
        doc.save()
        doc.submit()
        
        return doc
        
    except Exception as e:
        frappe.log_error(f"Error creating Purchase Invoice: {str(e)}")
        return None

def update_purchase_invoice_from_portal(doc, invoice_data):
    """Update existing Purchase Invoice with portal data"""
    try:
        # Update fields that can be updated
        if hasattr(doc, 'custom_portal_order_name'):
            doc.custom_portal_order_name = invoice_data['order_name']
        if hasattr(doc, 'custom_customer_name'):
            doc.custom_customer_name = invoice_data['customer_name']
        
        # Add remarks
        if invoice_data.get('remark'):
            doc.remarks = invoice_data['remark']
            
    except Exception as e:
        frappe.log_error(f"Error updating Purchase Invoice: {str(e)}")

def get_or_create_supplier(vendor_names):
    """Get or create supplier from vendor names"""
    try:
        # Use first vendor name or create a generic one
        supplier_name = vendor_names.split(',')[0].strip() if vendor_names and vendor_names != 'No Vendors' else 'Portal Vendor'
        
        # Check if supplier exists
        if frappe.db.exists('Supplier', supplier_name):
            return supplier_name
        
        # Create new supplier
        supplier = frappe.new_doc('Supplier')
        supplier.supplier_name = supplier_name
        supplier.supplier_group = 'All Supplier Groups'
        supplier.save()
        
        return supplier.name
        
    except Exception as e:
        frappe.log_error(f"Error creating supplier: {str(e)}")
        return 'Portal Vendor'

def get_or_create_item(item_name='Portal Import Item'):
    """Get or create a default item for portal imports"""
    try:
        if frappe.db.exists('Item', item_name):
            return item_name
        
        item = frappe.new_doc('Item')
        item.item_code = item_name
        item.item_name = item_name
        item.item_group = 'All Item Groups'
        item.stock_uom = 'Nos'
        item.is_purchase_item = 1
        item.save()
        
        return item.name
        
    except Exception as e:
        frappe.log_error(f"Error creating item: {str(e)}")
        return 'Portal Import Item'

@frappe.whitelist()
def get_recent_portal_invoices_with_progress(limit=500, chunk_size=100, status_filter=None, date_from=None, date_to=None):
    """
    Fetch recent portal invoices with progress tracking
    Process data in chunks to provide better progress feedback
    
    Args:
        limit (int): Number of invoices to fetch (default: 500)
        chunk_size (int): Size of each processing chunk (default: 100)
        status_filter (str): Filter by status (optional)
        date_from (str): Start date filter (optional)
        date_to (str): End date filter (optional)
        
    Returns:
        dict: Success status and invoice data with progress info
    """
    try:
        with get_external_db_connection() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                # First, get the count for progress calculation
                count_query = """
                SELECT COUNT(*) as total_count
                FROM purchase_requisitions pr
                WHERE pr.is_delete = 0 
                AND pr.status = 'active'
                """
                
                count_params = []
                if status_filter and status_filter != 'active':
                    count_query += " AND pr.status = %s"
                    count_params.append(status_filter)
                
                if date_from:
                    count_query += " AND DATE(pr.created_at) >= %s"
                    count_params.append(date_from)
                
                if date_to:
                    count_query += " AND DATE(pr.created_at) <= %s"
                    count_params.append(date_to)
                
                cursor.execute(count_query, count_params)
                total_count = cursor.fetchone()['total_count']
                
                # Adjust limit if needed
                actual_limit = min(int(limit), total_count)
                
                # Main query to get requisitions in chunks
                main_query = """
                SELECT 
                    pr.id as requisition_id,
                    pr.order_name,
                    pr.entity,
                    pr.subentity_id,
                    pr.delivery_date,
                    pr.validity_date,
                    pr.order_code,
                    pr.address,
                    pr.remark,
                    pr.acknowledgement,
                    pr.order_status,
                    pr.status as requisition_status,
                    pr.created_at as requisition_date,
                    pr.created_by,
                    pr.invoice_number,
                    pr.invoice_generated,
                    pr.invoice_generated_at
                FROM purchase_requisitions pr
                WHERE pr.is_delete = 0 
                AND pr.status = 'active'
                """
                
                params = []
                
                # Add filters
                if status_filter and status_filter != 'active':
                    main_query += " AND pr.status = %s"
                    params.append(status_filter)
                
                if date_from:
                    main_query += " AND DATE(pr.created_at) >= %s"
                    params.append(date_from)
                
                if date_to:
                    main_query += " AND DATE(pr.created_at) <= %s"
                    params.append(date_to)
                
                main_query += """
                ORDER BY pr.created_at DESC
                LIMIT %s
                """
                params.append(actual_limit)
                
                cursor.execute(main_query, params)
                requisitions = cursor.fetchall()
                
                # Process invoices in chunks for better progress tracking
                invoices = []
                chunk_size = int(chunk_size)
                total_requisitions = len(requisitions)
                
                for i in range(0, total_requisitions, chunk_size):
                    chunk = requisitions[i:i + chunk_size]
                    
                    # Process each chunk
                    for req in chunk:
                        # Get totals for this requisition
                        totals_query = """
                        SELECT 
                            COUNT(poi.id) as total_items,
                            SUM(poi.total_amt) as total_amount,
                            SUM(poi.gst_amt) as total_gst,
                            GROUP_CONCAT(DISTINCT v.name SEPARATOR ', ') as vendor_names,
                            GROUP_CONCAT(DISTINCT v.code SEPARATOR ', ') as vendor_codes
                        FROM purchase_order_items poi
                        LEFT JOIN vendors v ON poi.vendor_id = v.id
                        WHERE poi.purchase_order_id = %s
                        """
                        
                        cursor.execute(totals_query, (req['requisition_id'],))
                        totals = cursor.fetchone()
                        
                        # Create invoice object
                        invoice = {
                            'invoice_id': req['requisition_id'],
                            'invoice_number': req['order_code'],
                            'order_name': req['order_name'],
                            'customer_name': req['entity'],
                            'customer_id': req['subentity_id'],
                            'created_date': safe_date_format(req['requisition_date']),
                            'due_date': safe_date_format(req['delivery_date'], '%Y-%m-%d'),
                            'validity_date': safe_date_format(req['validity_date'], '%Y-%m-%d'),
                            'address': req['address'] or '',
                            'remark': req['remark'] or '',
                            'acknowledgement': req['acknowledgement'],
                            'order_status': req['order_status'],
                            'status': req['requisition_status'],
                            'created_by': req['created_by'],
                            'portal_invoice_number': req['invoice_number'] or '',
                            'invoice_generated': bool(req['invoice_generated']),
                            'invoice_generated_at': safe_date_format(req['invoice_generated_at']),
                            'total_items': totals['total_items'] or 0,
                            'total_amount': float(totals['total_amount']) if totals['total_amount'] else 0.0,
                            'total_gst': float(totals['total_gst']) if totals['total_gst'] else 0.0,
                            'grand_total': float(totals['total_amount'] or 0) + float(totals['total_gst'] or 0),
                            'vendor_names': totals['vendor_names'] or 'No Vendors',
                            'vendor_codes': totals['vendor_codes'] or ''
                        }
                        
                        invoices.append(invoice)
                    
                    # Add a small delay for very large datasets to prevent timeouts
                    if len(chunk) == chunk_size and i + chunk_size < total_requisitions:
                        import time
                        time.sleep(0.01)  # 10ms delay between chunks
                
                # Get comprehensive statistics
                stats_query = """
                SELECT 
                    COUNT(DISTINCT pr.id) as total_invoices,
                    COUNT(DISTINCT poi.vendor_id) as total_vendors,
                    SUM(poi.total_amt) as total_value,
                    SUM(poi.gst_amt) as total_gst_value,
                    AVG(poi.total_amt) as avg_invoice_value,
                    MIN(pr.created_at) as oldest_invoice,
                    MAX(pr.created_at) as newest_invoice
                FROM purchase_requisitions pr
                LEFT JOIN purchase_order_items poi ON pr.id = poi.purchase_order_id
                WHERE pr.is_delete = 0 AND pr.status = 'active'
                """
                
                cursor.execute(stats_query)
                stats = cursor.fetchone()
                
                statistics = {
                    'total_invoices': stats['total_invoices'] or 0,
                    'total_vendors': stats['total_vendors'] or 0,
                    'total_value': float(stats['total_value']) if stats['total_value'] else 0.0,
                    'total_gst_value': float(stats['total_gst_value']) if stats['total_gst_value'] else 0.0,
                    'avg_invoice_value': float(stats['avg_invoice_value']) if stats['avg_invoice_value'] else 0.0,
                    'oldest_invoice': safe_date_format(stats['oldest_invoice'], '%Y-%m-%d'),
                    'newest_invoice': safe_date_format(stats['newest_invoice'], '%Y-%m-%d'),
                    'fetched_count': len(invoices),
                    'processing_info': {
                        'total_processed': len(invoices),
                        'chunk_size': chunk_size,
                        'chunks_processed': (len(invoices) + chunk_size - 1) // chunk_size
                    }
                }
                
                return {
                    'success': True,
                    'message': f'Successfully fetched {len(invoices)} portal invoices with progress tracking',
                    'invoices': invoices,
                    'statistics': statistics,
                    'total_fetched': len(invoices),
                    'progress_info': {
                        'total_available': total_count,
                        'requested_limit': limit,
                        'actual_fetched': len(invoices),
                        'processing_time': 'Optimized with chunked processing'
                    }
                }
                
    except Exception as e:
        frappe.log_error(f"Error fetching portal invoices with progress: {str(e)}")
        return {
            'success': False,
            'message': f'Error fetching portal invoices: {str(e)}',
            'invoices': [],
            'statistics': {},
            'total_fetched': 0,
            'progress_info': {
                'error': str(e)
            }
        }