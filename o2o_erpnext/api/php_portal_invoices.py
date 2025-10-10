import frappe
import pymysql
from frappe import _
from datetime import datetime
import pymysql.cursors
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

def validate_invoice_prerequisites(invoice_data):
    """
    Comprehensive validation for invoice import prerequisites
    Checks if customer, supplier, branch, sub-branch exist in ERPNext
    
    Args:
        invoice_data (dict): Invoice data from portal
        
    Returns:
        dict: Validation results with missing entities and suggestions
    """
    validation_result = {
        'success': True,
        'errors': [],
        'warnings': [],
        'missing_entities': {
            'customers': [],
            'suppliers': [],
            'branches': [],
            'sub_branches': []
        },
        'suggestions': []
    }
    
    # 1. Check Customer (from vendors table in portal = customers in ERPNext)
    customer_name = invoice_data.get('customer_name')
    customer_email = invoice_data.get('customer_email')
    customer_gstn = invoice_data.get('customer_gstn')
    
    if customer_name:
        # Check if customer exists in ERPNext
        existing_customer = frappe.get_all('Customer', 
                                         filters={'customer_name': customer_name},
                                         limit=1)
        if not existing_customer:
            validation_result['missing_entities']['customers'].append({
                'name': customer_name,
                'email': customer_email,
                'gstn': customer_gstn,
                'address': invoice_data.get('customer_address')
            })
            validation_result['suggestions'].append(
                f"Create Customer: '{customer_name}' with email '{customer_email}' and GSTN '{customer_gstn}'"
            )
    else:
        validation_result['errors'].append("Customer name is missing from invoice data")
    
    # 2. Check Supplier (entity = supplier in this context)
    entity_code = invoice_data.get('entity_code')
    branch_name = invoice_data.get('branch_name')
    
    if entity_code or branch_name:
        supplier_name = branch_name or entity_code
        existing_supplier = frappe.get_all('Supplier', 
                                         filters={'supplier_name': supplier_name},
                                         limit=1)
        if not existing_supplier:
            validation_result['missing_entities']['suppliers'].append({
                'name': supplier_name,
                'code': entity_code
            })
            validation_result['suggestions'].append(
                f"Create Supplier: '{supplier_name}' (Entity Code: {entity_code})"
            )
    else:
        validation_result['errors'].append("Entity/Branch information is missing")
    
    # 3. Check Branch (Company in ERPNext)
    if branch_name:
        existing_company = frappe.get_all('Company', 
                                        filters={'company_name': branch_name},
                                        limit=1)
        if not existing_company:
            validation_result['missing_entities']['branches'].append({
                'name': branch_name,
                'code': entity_code
            })
            validation_result['suggestions'].append(
                f"Create Company/Branch: '{branch_name}'"
            )
    
    # 4. Check Sub-branch (Cost Center or Department in ERPNext)
    subentity_code = invoice_data.get('subentity_code')
    sub_branch_name = invoice_data.get('sub_branch_name')
    
    if subentity_code and sub_branch_name:
        # Check Cost Center first
        existing_cost_center = frappe.get_all('Cost Center', 
                                            filters={'cost_center_name': sub_branch_name},
                                            limit=1)
        if not existing_cost_center:
            # Check Department as alternative
            existing_department = frappe.get_all('Department', 
                                               filters={'department_name': sub_branch_name},
                                               limit=1)
            if not existing_department:
                validation_result['missing_entities']['sub_branches'].append({
                    'name': sub_branch_name,
                    'code': subentity_code
                })
                validation_result['suggestions'].append(
                    f"Create Cost Center/Department: '{sub_branch_name}' (Code: {subentity_code})"
                )
    
    # 5. Check Invoice Number Format for AGO2O
    invoice_number = invoice_data.get('invoice_number', '')
    if invoice_number.startswith('AGO2O'):
        # Check if this invoice already exists
        existing_invoice = frappe.get_all('Purchase Invoice', 
                                        filters={'title': invoice_number},
                                        limit=1)
        if existing_invoice:
            validation_result['warnings'].append(
                f"Invoice '{invoice_number}' already exists in ERPNext. Consider skipping or updating."
            )
    
    # 6. Check Invoice Amount
    total_amount = invoice_data.get('amount', 0)
    try:
        amount = float(total_amount)
        if amount <= 0:
            validation_result['warnings'].append(
                f"Invoice amount is zero or negative ({amount}). "
                "Please verify the invoice amount before importing."
            )
    except (ValueError, TypeError):
        validation_result['errors'].append(
            f"Invalid invoice amount: {total_amount}. Amount must be a valid number."
        )
    
    # Set overall success status
    if validation_result['errors'] or validation_result['missing_entities']['customers'] or validation_result['missing_entities']['suppliers']:
        validation_result['success'] = False
    
    return validation_result

@frappe.whitelist()
def validate_and_suggest_entities(invoice_data):
    """
    Validate invoice data and provide suggestions for missing entities
    
    Args:
        invoice_data (dict): Invoice data to validate
        
    Returns:
        dict: Validation results with suggestions
    """
    if isinstance(invoice_data, str):
        import json
        invoice_data = json.loads(invoice_data)
    
    validation_result = validate_invoice_prerequisites(invoice_data)
    
    # Add creation suggestions with detailed steps
    if validation_result['missing_entities']['customers']:
        validation_result['creation_steps'] = validation_result.get('creation_steps', [])
        validation_result['creation_steps'].append({
            'type': 'customer',
            'title': 'Create Missing Customers',
            'steps': [
                '1. Go to Selling > Customer > New Customer',
                '2. Fill Customer Name, Email, and GSTN',
                '3. Add billing address details',
                '4. Save the customer record'
            ],
            'data': validation_result['missing_entities']['customers']
        })
    
    if validation_result['missing_entities']['suppliers']:
        validation_result['creation_steps'] = validation_result.get('creation_steps', [])
        validation_result['creation_steps'].append({
            'type': 'supplier',
            'title': 'Create Missing Suppliers',
            'steps': [
                '1. Go to Buying > Supplier > New Supplier',
                '2. Fill Supplier Name and details',
                '3. Add contact information',
                '4. Save the supplier record'
            ],
            'data': validation_result['missing_entities']['suppliers']
        })
    
    return validation_result
    """
    Validate that all required entities exist before creating invoice
    
    Args:
        invoice_data (dict): Portal invoice data
        
    Returns:
        dict: Validation result with success status and error messages
    """
    validation_result = {
        'success': True,
        'errors': [],
        'warnings': []
    }
    
    # 1. Check Supplier/Vendor
    vendor_names = invoice_data.get('vendor_names', '').strip()
    if not vendor_names or vendor_names in ['', 'No Vendors', 'None']:
        validation_result['errors'].append(
            f"Supplier/Vendor information is missing for invoice {invoice_data.get('invoice_number', 'Unknown')}. "
            "Invoice cannot be imported without valid supplier information."
        )
    else:
        # Check if any valid supplier exists in the system
        vendor_list = [v.strip() for v in vendor_names.split(',') if v.strip()]
        existing_suppliers = []
        for vendor in vendor_list:
            if frappe.db.exists('Supplier', vendor):
                existing_suppliers.append(vendor)
        
        @frappe.whitelist()
        def get_recent_portal_invoices(limit=500):
            """Get recent portal invoices from ProcureUAT database"""
            try:
                # Convert limit to integer
                limit = int(limit)

                # SQL to fetch recent portal invoices
                query = """
                SELECT DISTINCT
                    pr.id,
                    pr.order_code AS invoice_number,
                    pr.invoice_series,
                    pr.amount,
                    pr.created_at,
                    pr.updated_at,
                    pr.status,
                    v.name AS vendor_name,
                    v.email AS vendor_email,
                    v.address AS vendor_address,
                    pr.customer_name,
                    pr.branch_name,
                    pr.sub_branch_name,
                    pr.description,
                    pr.invoice_date,
                    pr.due_date
                FROM purchase_requisitions pr
                LEFT JOIN vendors v ON pr.vendor_created = v.id
                WHERE pr.order_code IS NOT NULL
                  AND pr.order_code != ''
                  AND pr.amount > 0
                ORDER BY pr.created_at DESC, pr.id DESC
                LIMIT %s
                """

                # Execute SQL with external DB connection
                with get_external_db_connection() as conn:
                    with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                        cursor.execute(query, (limit,))
                        invoices = cursor.fetchall()

                # Build statistics
                statistics = {
                    'total_invoices': len(invoices),
                    'total_amount': sum(float(inv.get('amount') or 0) for inv in invoices),
                    'ago2o_invoices': sum(1 for inv in invoices if inv.get('invoice_number', '').startswith('AGO2O')),
                    'current_fy_invoices': sum(1 for inv in invoices if '25-26' in inv.get('invoice_number', '')),
                    'latest_date': max((inv.get('created_at') for inv in invoices if inv.get('created_at')), default=None)
                }

                return {
                    'success': True,
                    'invoices': invoices,
                    'statistics': statistics,
                    'message': f'Successfully loaded {len(invoices)} portal invoices'
                }
            except Exception as e:
                frappe.log_error(f"Error in get_recent_portal_invoices: {str(e)}", "Portal Invoices Error")
                return {
                    'success': False,
                    'message': f'Failed to fetch portal invoices: {str(e)}',
                    'invoices': [],
                    'statistics': {}
                }
    
    # 6. Check Invoice Amount
    total_amount = invoice_data.get('total_amount', 0)
    try:
        amount = float(total_amount)
        if amount <= 0:
            validation_result['warnings'].append(
                f"Invoice amount is zero or negative ({amount}). "
                "Please verify the invoice amount before importing."
            )
    except (ValueError, TypeError):
        validation_result['errors'].append(
            f"Invalid invoice amount: {total_amount}. Amount must be a valid number."
        )
    
    # Set overall success status
    if validation_result['errors']:
        validation_result['success'] = False
    
    return validation_result

@frappe.whitelist()
def check_database_structure_and_data():
    """
    Check the remote database structure and recent data to understand invoice numbering
    """
    try:
        with get_external_db_connection() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                
                result = {
                    'success': True,
                    'database_info': {},
                    'recent_data': {},
                    'invoice_patterns': []
                }
                
                # 1. Check purchase_requisitions table structure
                cursor.execute('DESCRIBE purchase_requisitions')
                fields = cursor.fetchall()
                result['database_info']['purchase_requisitions_fields'] = [
                    {'field': f['Field'], 'type': f['Type'], 'null': f['Null'], 'key': f['Key']} 
                    for f in fields
                ]
                
                # 2. Get recent purchase requisitions data
                cursor.execute('''
                    SELECT id, order_name, order_code, invoice_number, invoice_series, 
                           entity, subentity_id, delivery_date, created_at, 
                           invoice_generated, invoice_generated_at, status
                    FROM purchase_requisitions 
                    WHERE is_delete = 0 
                    ORDER BY id DESC 
                    LIMIT 20
                ''')
                recent_requisitions = cursor.fetchall()
                result['recent_data']['purchase_requisitions'] = [
                    {
                        'id': r['id'],
                        'order_name': r['order_name'],
                        'order_code': r['order_code'],
                        'invoice_number': r['invoice_number'],
                        'invoice_series': r['invoice_series'],
                        'entity': r['entity'],
                        'created_at': safe_date_format(r['created_at']),
                        'status': r['status']
                    } for r in recent_requisitions
                ]
                
                # 3. Check if there are other tables that might contain invoice data
                cursor.execute('SHOW TABLES LIKE "%invoice%"')
                invoice_tables = cursor.fetchall()
                result['database_info']['invoice_related_tables'] = [t[list(t.keys())[0]] for t in invoice_tables]
                
                # 4. Check for AGO20 pattern invoices specifically
                cursor.execute('''
                    SELECT id, order_name, order_code, invoice_number, invoice_series,
                           entity, created_at, status
                    FROM purchase_requisitions 
                    WHERE (order_code LIKE '%AGO20%' OR invoice_number LIKE '%AGO20%' 
                           OR order_name LIKE '%AGO20%')
                    AND is_delete = 0 
                    ORDER BY id DESC 
                    LIMIT 10
                ''')
                ago20_invoices = cursor.fetchall()
                result['recent_data']['ago20_pattern_invoices'] = [
                    {
                        'id': r['id'],
                        'order_name': r['order_name'],
                        'order_code': r['order_code'],
                        'invoice_number': r['invoice_number'],
                        'invoice_series': r['invoice_series'],
                        'created_at': safe_date_format(r['created_at'])
                    } for r in ago20_invoices
                ]
                
                # 5. Check different invoice number patterns
                cursor.execute('''
                    SELECT DISTINCT 
                        SUBSTRING(order_code, 1, 10) as order_code_pattern,
                        SUBSTRING(invoice_number, 1, 10) as invoice_number_pattern,
                        COUNT(*) as count
                    FROM purchase_requisitions 
                    WHERE is_delete = 0 
                    AND (order_code IS NOT NULL OR invoice_number IS NOT NULL)
                    GROUP BY order_code_pattern, invoice_number_pattern
                    ORDER BY count DESC
                    LIMIT 20
                ''')
                patterns = cursor.fetchall()
                result['invoice_patterns'] = [
                    {
                        'order_code_pattern': p['order_code_pattern'],
                        'invoice_number_pattern': p['invoice_number_pattern'],
                        'count': p['count']
                    } for p in patterns
                ]
                
                # 6. Check entities table for customer mapping
                cursor.execute('SELECT id, name, address, created_at FROM entitys ORDER BY id DESC LIMIT 10')
                entities = cursor.fetchall()
                result['recent_data']['entities'] = [
                    {
                        'id': e['id'],
                        'name': e['name'],
                        'address': e['address'][:100] if e['address'] else '',
                        'created_at': safe_date_format(e['created_at'])
                    } for e in entities
                ]
                
                # 7. Check vendors table
                cursor.execute('SELECT id, name, address, email, created_at FROM vendors ORDER BY id DESC LIMIT 10')
                vendors = cursor.fetchall()
                result['recent_data']['vendors'] = [
                    {
                        'id': v['id'],
                        'name': v['name'],
                        'address': v['address'][:100] if v['address'] else '',
                        'email': v['email'],
                        'created_at': safe_date_format(v['created_at'])
                    } for v in vendors
                ]
                
                return result
                
    except Exception as e:
        frappe.log_error(
            message=f"Error checking database structure: {str(e)}",
            title="Database Structure Check Error"
        )
        return {
            'success': False,
            'message': f'Failed to check database structure: {str(e)}',
            'error': str(e)
        }

@frappe.whitelist()
def search_specific_invoice_numbers(invoice_numbers):
    """
    Search for specific invoice numbers in the remote database
    
    Args:
        invoice_numbers (list): List of invoice numbers to search for
    """
    try:
        if isinstance(invoice_numbers, str):
            import json
            invoice_numbers = json.loads(invoice_numbers)
        
        with get_external_db_connection() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                
                result = {
                    'success': True,
                    'found_invoices': [],
                    'not_found': [],
                    'search_patterns': []
                }
                
                for invoice_num in invoice_numbers:
                    # Search in multiple fields
                    cursor.execute('''
                        SELECT id, order_name, order_code, invoice_number, invoice_series,
                               entity, subentity_id, delivery_date, created_at, status,
                               remark, address
                        FROM purchase_requisitions 
                        WHERE (order_code = %s OR invoice_number = %s 
                               OR order_name = %s OR order_code LIKE %s
                               OR invoice_number LIKE %s OR order_name LIKE %s)
                        AND is_delete = 0 
                        ORDER BY id DESC
                    ''', (invoice_num, invoice_num, invoice_num, 
                          f'%{invoice_num}%', f'%{invoice_num}%', f'%{invoice_num}%'))
                    
                    found = cursor.fetchall()
                    
                    if found:
                        result['found_invoices'].extend([
                            {
                                'search_term': invoice_num,
                                'id': r['id'],
                                'order_name': r['order_name'],
                                'order_code': r['order_code'],
                                'invoice_number': r['invoice_number'],
                                'invoice_series': r['invoice_series'],
                                'entity': r['entity'],
                                'created_at': safe_date_format(r['created_at']),
                                'status': r['status'],
                                'remark': r['remark'][:100] if r['remark'] else ''
                            } for r in found
                        ])
                    else:
                        result['not_found'].append(invoice_num)
                
                return result
                
    except Exception as e:
        frappe.log_error(
            message=f"Error searching invoice numbers: {str(e)}",
            title="Invoice Search Error"
        )
        return {
            'success': False,
            'message': f'Failed to search invoice numbers: {str(e)}',
            'error': str(e)
        }

@frappe.whitelist()
def get_recent_purchase_requisitions(limit=500, offset=0):
    """Get recent purchase requisitions from ProcureUAT database with entity and subentity names"""
    try:
        # Import the updated function that includes JOINs
        from o2o_erpnext.config.external_db_updated import get_procureuat_purchase_requisitions
        
        # Convert parameters to integers
        limit = int(limit)
        offset = int(offset)

        # Use the updated function that includes entity and subentity names
        requisitions = get_procureuat_purchase_requisitions(limit=limit, offset=offset)

        # Get total count for pagination
        with get_external_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) as total FROM purchase_requisitions WHERE is_delete = 0")
                total_result = cursor.fetchone()
                total_records = total_result['total'] if total_result else 0

        # Calculate pagination info
        current_offset = offset
        fetched_count = len(requisitions)
        has_more = (current_offset + fetched_count) < total_records

        frappe.logger().info(f"Purchase Requisitions API - Fetched: {fetched_count}, Offset: {current_offset}, Total: {total_records}")

        return {
            'status': 'success',
            'data': requisitions,
            'pagination': {
                'total_records': total_records,
                'current_offset': current_offset,
                'fetched_count': fetched_count,
                'has_more': has_more,
                'limit': limit
            }
        }

    except Exception as e:
        frappe.log_error(f"Error in get_recent_purchase_requisitions: {str(e)}", "Purchase Requisitions Error")
        return {
            'success': False,
            'message': f'Failed to fetch purchase requisitions: {str(e)}',
            'data': [],
            'pagination': {
                'total_records': 0,
                'current_offset': 0,
                'fetched_count': 0,
                'has_more': False,
                'limit': limit
            }
        }

# Alias for backward compatibility
@frappe.whitelist()
def get_recent_portal_invoices(limit=500):
    """Alias for get_recent_purchase_requisitions"""
    return get_recent_purchase_requisitions(limit)

@frappe.whitelist()
def test_purchase_requisitions_connection():
    """Test function to verify purchase_requisitions data structure"""
    try:
        query = """
        SELECT 
            id,
            invoice_number,
            invoice_series,
            order_code,
            order_name,
            entity,
            subentity_id,
            status,
            created_at,
            invoice_generated
        FROM purchase_requisitions 
        ORDER BY created_at DESC 
        LIMIT 5
        """
        
        with get_external_db_connection() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(query)
                sample_data = cursor.fetchall()
        
        # Format the data for better display
        formatted_data = []
        for row in sample_data:
            formatted_data.append({
                'id': row['id'],
                'invoice_number': row['invoice_number'] or 'NULL',
                'invoice_series': row['invoice_series'] or 'NULL',
                'order_code': row['order_code'] or 'NULL',
                'order_name': row['order_name'] or 'NULL',
                'entity': row['entity'] or 'NULL',
                'subentity_id': row['subentity_id'] or 'NULL',
                'status': row['status'] or 'NULL',
                'created_at': safe_date_format(row['created_at']),
                'invoice_generated': row['invoice_generated']
            })
        
        return {
            'success': True,
            'message': f'Successfully fetched {len(sample_data)} sample records',
            'sample_data': formatted_data,
            'field_info': {
                'invoice_number_usage': 'Primary identifier - can be NULL',
                'order_code_usage': 'Order code - alternative identifier',
                'entity': 'Customer entity ID',
                'subentity_id': 'Delivery location ID'
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Error in test_purchase_requisitions_connection: {str(e)}", "Test PR Connection Error")
        return {
            'success': False,
            'message': f'Failed to test connection: {str(e)}',
            'error': str(e)
        }

@frappe.whitelist()
def check_invoice_discrepancy():
    """
    Check the discrepancy between remote database and ERPNext for invoice numbers
    """
    try:
        result = {
            'success': True,
            'remote_invoices': [],
            'erpnext_invoices': [],
            'discrepancy_analysis': {}
        }
        
        # 1. Get recent invoices from remote database
        with get_external_db_connection() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute('''
                    SELECT id, order_name, order_code, invoice_number, invoice_series,
                           entity, created_at, status
                    FROM purchase_requisitions 
                    WHERE invoice_number IS NOT NULL 
                    AND is_delete = 0 
                    ORDER BY id DESC 
                    LIMIT 20
                ''')
                remote_invoices = cursor.fetchall()
                result['remote_invoices'] = [
                    {
                        'id': r['id'],
                        'order_name': r['order_name'],
                        'order_code': r['order_code'],
                        'invoice_number': r['invoice_number'],
                        'invoice_series': r['invoice_series'],
                        'created_at': safe_date_format(r['created_at'])
                    } for r in remote_invoices
                ]
        
        # 2. Get Purchase Invoices from ERPNext
        erpnext_invoices = frappe.db.sql('''
            SELECT name, title, supplier, posting_date, grand_total, creation
            FROM `tabPurchase Invoice` 
            WHERE title LIKE '%AGO%' 
            ORDER BY creation DESC 
            LIMIT 20
        ''', as_dict=True)
        
        result['erpnext_invoices'] = [
            {
                'name': inv['name'],
                'title': inv['title'],
                'supplier': inv['supplier'],
                'posting_date': str(inv['posting_date']) if inv['posting_date'] else '',
                'grand_total': inv['grand_total'],
                'creation': str(inv['creation']) if inv['creation'] else ''
            } for inv in erpnext_invoices
        ]
        
        # 3. Check for specific invoice patterns
        screenshot_invoices = [
            'AGO20/25-26/2428', 'AGO20/25-26/2427', 'AGO20/25-26/2426', 
            'AGO20/25-26/2425', 'AGO20/25-26/2424', 'AGO20/25-26/2423', 
            'AGO20/25-26/2421', 'AGO20/25-26/2420', 'AGO20/25-26/2419'
        ]
        
        found_in_erpnext = []
        not_found_in_erpnext = []
        
        for inv_num in screenshot_invoices:
            exists = frappe.db.exists('Purchase Invoice', {'title': inv_num})
            if exists:
                found_in_erpnext.append(inv_num)
            else:
                not_found_in_erpnext.append(inv_num)
        
        result['discrepancy_analysis'] = {
            'screenshot_invoice_numbers': screenshot_invoices,
            'found_in_erpnext': found_in_erpnext,
            'not_found_in_erpnext': not_found_in_erpnext,
            'remote_pattern_analysis': {
                'current_remote_pattern': 'AGO2O/25-26/XX (with 2O)',
                'expected_pattern': 'AGO20/25-26/XXXX (with 20)',
                'series_difference': 'Remote has low series (1,2,7) vs Expected high series (2400+)'
            }
        }
        
        return result
        
    except Exception as e:
        frappe.log_error(
            message=f"Error checking invoice discrepancy: {str(e)}",
            title="Invoice Discrepancy Check Error"
        )
        return {
            'success': False,
            'message': f'Failed to check invoice discrepancy: {str(e)}',
            'error': str(e)
        }

@frappe.whitelist()
def find_ago2o_invoices():
    """
    Search for AGO2O pattern invoices in both remote database and ERPNext
    """
    try:
        result = {
            'success': True,
            'remote_ago2o_invoices': [],
            'erpnext_ago2o_invoices': [],
            'matching_invoices': [],
            'missing_in_erpnext': [],
            'extra_in_erpnext': []
        }
        
        # 1. Get all AGO2O invoices from remote database
        with get_external_db_connection() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute('''
                    SELECT id, order_name, order_code, invoice_number, invoice_series,
                           entity, created_at, status, remark
                    FROM purchase_requisitions 
                    WHERE invoice_number LIKE '%AGO2O%'
                    AND is_delete = 0 
                    ORDER BY invoice_series ASC, id ASC
                ''')
                remote_invoices = cursor.fetchall()
                result['remote_ago2o_invoices'] = [
                    {
                        'id': r['id'],
                        'order_name': r['order_name'],
                        'order_code': r['order_code'],
                        'invoice_number': r['invoice_number'],
                        'invoice_series': r['invoice_series'],
                        'entity': r['entity'],
                        'created_at': safe_date_format(r['created_at']),
                        'remark': r['remark'][:100] if r['remark'] else ''
                    } for r in remote_invoices
                ]
        
        # 2. Get all AGO2O invoices from ERPNext
        erpnext_invoices = frappe.db.sql('''
            SELECT name, title, supplier, posting_date, grand_total, creation, docstatus
            FROM `tabPurchase Invoice` 
            WHERE title LIKE '%AGO2O%' 
            ORDER BY title ASC
        ''', as_dict=True)
        
        result['erpnext_ago2o_invoices'] = [
            {
                'name': inv['name'],
                'title': inv['title'],
                'supplier': inv['supplier'],
                'posting_date': str(inv['posting_date']) if inv['posting_date'] else '',
                'grand_total': float(inv['grand_total']) if inv['grand_total'] else 0,
                'creation': str(inv['creation']) if inv['creation'] else '',
                'docstatus': inv['docstatus']
            } for inv in erpnext_invoices
        ]
        
        # 3. Find matching invoices
        remote_invoice_numbers = set([inv['invoice_number'] for inv in result['remote_ago2o_invoices']])
        erpnext_invoice_numbers = set([inv['title'] for inv in result['erpnext_ago2o_invoices']])
        
        matching = remote_invoice_numbers.intersection(erpnext_invoice_numbers)
        missing_in_erpnext = remote_invoice_numbers - erpnext_invoice_numbers
        extra_in_erpnext = erpnext_invoice_numbers - remote_invoice_numbers
        
        result['matching_invoices'] = list(matching)
        result['missing_in_erpnext'] = list(missing_in_erpnext)
        result['extra_in_erpnext'] = list(extra_in_erpnext)
        
        # 4. Summary statistics
        result['summary'] = {
            'total_remote_invoices': len(result['remote_ago2o_invoices']),
            'total_erpnext_invoices': len(result['erpnext_ago2o_invoices']),
            'matching_count': len(matching),
            'missing_in_erpnext_count': len(missing_in_erpnext),
            'extra_in_erpnext_count': len(extra_in_erpnext),
            'sync_percentage': round((len(matching) / len(remote_invoice_numbers) * 100), 2) if remote_invoice_numbers else 0
        }
        
        return result
        
    except Exception as e:
        frappe.log_error(
            message=f"Error finding AGO2O invoices: {str(e)}",
            title="AGO2O Invoice Search Error"
        )
        return {
            'success': False,
            'message': f'Failed to find AGO2O invoices: {str(e)}',
            'error': str(e)
        }
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
    # End of test_portal_connection

@frappe.whitelist()
def test_procureuat_connection():
    """Alias for ProcureUAT connection test"""
    return test_portal_connection()

@frappe.whitelist()
def sync_to_procureuat():
    """Alias for ProcureUAT sync (uses portal connection test as placeholder)"""
    # TODO: Implement actual sync to Procure UAT if needed
    return test_portal_connection()

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
        detailed_errors = []
        warnings = []
        
        for invoice in invoices:
            try:
                # Validate invoice data first
                if not invoice.get('invoice_number'):
                    error_count += 1
                    detailed_errors.append(f"Invoice without number skipped")
                    continue
                    
                invoice_number = invoice['invoice_number']
                
                # Check if invoice already exists
                existing = frappe.get_all('Purchase Invoice', 
                                        filters={'title': invoice_number},
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
                    # Create new invoice with comprehensive validation
                    result = create_purchase_invoice_from_portal(invoice)
                    
                    if isinstance(result, dict):
                        if result.get('success'):
                            imported_count += 1
                            if result.get('warnings'):
                                warnings.extend([f"{invoice_number}: {w}" for w in result['warnings']])
                        else:
                            error_count += 1
                            # Collect specific error messages
                            if result.get('errors'):
                                detailed_errors.extend([f"{invoice_number}: {e}" for e in result['errors']])
                            elif result.get('message'):
                                detailed_errors.append(f"{invoice_number}: {result['message']}")
                            else:
                                detailed_errors.append(f"{invoice_number}: Unknown error occurred")
                    else:
                        # Old format - assume success if doc returned
                        if result:
                            imported_count += 1
                        else:
                            error_count += 1
                            detailed_errors.append(f"{invoice_number}: Failed to create invoice")
                        
            except Exception as e:
                # Create concise error message to avoid title truncation
                invoice_ref = invoice.get('invoice_number', 'Unknown')[:20]
                error_msg = str(e)[:80] + "..." if len(str(e)) > 80 else str(e)
                detailed_errors.append(f"{invoice_ref}: {error_msg}")
                
                frappe.log_error(
                    message=f"Error importing invoice {invoice_ref}: {error_msg}",
                    title=f"Import Error - {invoice_ref}"
                )
                error_count += 1
                continue
        
        frappe.db.commit()
        
        # Prepare result message
        result_message = f'Import completed. Imported: {imported_count}, Skipped: {skipped_count}, Errors: {error_count}'
        
        if detailed_errors:
            result_message += f"\n\nError Details:\n" + "\n".join(detailed_errors[:10])  # Limit to first 10 errors
            if len(detailed_errors) > 10:
                result_message += f"\n... and {len(detailed_errors) - 10} more errors (check error logs)"
        
        if warnings:
            result_message += f"\n\nWarnings:\n" + "\n".join(warnings[:5])  # Limit to first 5 warnings
            if len(warnings) > 5:
                result_message += f"\n... and {len(warnings) - 5} more warnings"
        
        return {
            'success': True,
            'message': result_message,
            'imported_count': imported_count,
            'skipped_count': skipped_count,
            'error_count': error_count,
            'detailed_errors': detailed_errors,
            'warnings': warnings
        }
        
    except Exception as e:
        # Create concise error message to avoid title truncation
        error_msg = str(e)[:100] + "..." if len(str(e)) > 100 else str(e)
        frappe.log_error(
            message=f"Batch import error: {error_msg}",
            title="Batch Import Failed"
        )
        return {
            'success': False,
            'message': f'Batch import failed: {error_msg}',
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
        # Enhanced logging for debugging
        frappe.logger().info(f"🔍 Starting fetch_single_invoice for: '{invoice_number}' (create_if_not_exists: {create_if_not_exists}, update_if_exists: {update_if_exists})")
        
        # Search for the invoice in portal by invoice_number field
        with get_external_db_connection() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                query = """
                SELECT pr.*, 
                       e.name as entity_name,
                       se.name as subentity_name,
                       COUNT(poi.id) as total_items,
                       SUM(poi.total_amt) as total_amount,
                       SUM(poi.gst_amt) as total_gst,
                       GROUP_CONCAT(DISTINCT v.name SEPARATOR ', ') as vendor_names
                FROM purchase_requisitions pr
                LEFT JOIN entitys e ON pr.entity = e.id
                LEFT JOIN subentitys se ON pr.subentity_id = se.id
                LEFT JOIN purchase_order_items poi ON pr.id = poi.purchase_order_id
                LEFT JOIN vendors v ON poi.vendor_id = v.id
                WHERE pr.invoice_number = %s AND pr.is_delete = 0
                GROUP BY pr.id
                """
                
                cursor.execute(query, (invoice_number,))
                portal_invoice = cursor.fetchone()
                
                # If not found by invoice_number, try order_code as fallback
                if not portal_invoice:
                    cursor.execute("""
                        SELECT pr.*, 
                               e.name as entity_name,
                               se.name as subentity_name,
                               COUNT(poi.id) as total_items,
                               SUM(poi.total_amt) as total_amount,
                               SUM(poi.gst_amt) as total_gst,
                               GROUP_CONCAT(DISTINCT v.name SEPARATOR ', ') as vendor_names
                        FROM purchase_requisitions pr
                        LEFT JOIN entitys e ON pr.entity = e.id
                        LEFT JOIN subentitys se ON pr.subentity_id = se.id
                        LEFT JOIN purchase_order_items poi ON pr.id = poi.purchase_order_id
                        LEFT JOIN vendors v ON poi.vendor_id = v.id
                        WHERE pr.order_code = %s AND pr.is_delete = 0
                        GROUP BY pr.id
                    """, (invoice_number,))
                    portal_invoice = cursor.fetchone()
                
                if not portal_invoice:
                    # Enhanced search - try partial matching for invoice numbers
                    cursor.execute("""
                        SELECT pr.*, 
                               e.name as entity_name,
                               se.name as subentity_name,
                               COUNT(poi.id) as total_items,
                               SUM(poi.total_amt) as total_amount,
                               SUM(poi.gst_amt) as total_gst,
                               GROUP_CONCAT(DISTINCT v.name SEPARATOR ', ') as vendor_names
                        FROM purchase_requisitions pr
                        LEFT JOIN entitys e ON pr.entity = e.id
                        LEFT JOIN subentitys se ON pr.subentity_id = se.id
                        LEFT JOIN purchase_order_items poi ON pr.id = poi.purchase_order_id
                        LEFT JOIN vendors v ON poi.vendor_id = v.id
                        WHERE (pr.invoice_number LIKE %s OR pr.order_code LIKE %s) 
                        AND pr.is_delete = 0
                        GROUP BY pr.id
                        LIMIT 5
                    """, (f'%{invoice_number}%', f'%{invoice_number}%'))
                    
                    similar_invoices = cursor.fetchall()
                    
                    if similar_invoices:
                        similar_list = [f"{inv.get('invoice_number', inv.get('order_code', 'Unknown'))}" for inv in similar_invoices]
                        return {
                            'success': False,
                            'message': f'Invoice {invoice_number} not found in portal. Did you mean: {", ".join(similar_list)}?',
                            'invoice_name': None,
                            'suggestions': similar_list
                        }
                    else:
                        return {
                            'success': False,
                            'message': f'Invoice {invoice_number} not found in portal ❌ \n\nSearched in:\n• invoice_number field\n• order_code field\n• Similar patterns\n\nPlease verify the invoice number exists in the portal system.',
                            'invoice_name': None
                        }
                
                # Log successful discovery for debugging
                frappe.logger().info(f"Found invoice {invoice_number} in portal: ID {portal_invoice.get('id')}, Invoice Number: {portal_invoice.get('invoice_number')}")
                
                # Check if invoice exists locally 
                # Search by:
                # 1. Title (should match invoice_number from portal)
                # 2. ERPNext invoice name (should match order_code from portal) 
                # 3. Supplier invoice number (should match invoice_number from portal)
                existing = None
                
                # First try exact title match
                existing = frappe.get_all('Purchase Invoice', 
                                        filters={'title': invoice_number},
                                        limit=1)
                
                # If not found by title, try by ERPNext invoice name (order_code mapping)
                if not existing and portal_invoice.get('order_code'):
                    existing = frappe.get_all('Purchase Invoice', 
                                            filters={'name': portal_invoice.get('order_code')},
                                            limit=1)
                
                # If not found by name, try by supplier invoice number (bill_no mapping)  
                if not existing and portal_invoice.get('invoice_number'):
                    existing = frappe.get_all('Purchase Invoice', 
                                            filters={'bill_no': portal_invoice.get('invoice_number')},
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

@frappe.whitelist()
def import_multiple_portal_invoices(invoice_ids):
    """
    Enhanced import function with detailed progress and failure tracking
    
    Args:
        invoice_ids (list): List of portal invoice IDs
        
    Returns:
        dict: Detailed import results with success/failure tracking
    """
    try:
        if isinstance(invoice_ids, str):
            invoice_ids = frappe.parse_json(invoice_ids)
        
        imported_count = 0
        skipped_count = 0
        failed_count = 0
        failures = []
        
        for invoice_id in invoice_ids:
            try:
                # Check if already imported
                existing = frappe.db.exists("Purchase Invoice", {"custom_portal_invoice_id": invoice_id})
                if existing:
                    skipped_count += 1
                    continue
                
                # Get invoice detail from portal
                detail_result = get_portal_invoice_detail(invoice_id)
                if detail_result.get('success'):
                    invoice_data = detail_result['invoice']['header']
                    
                    # Format and create invoice
                    formatted_invoice = format_portal_invoice_data(invoice_data)
                    doc = create_purchase_invoice_from_portal(formatted_invoice)
                    
                    if doc:
                        imported_count += 1
                    else:
                        failed_count += 1
                        failures.append(f"Invoice ID {invoice_id}: Failed to create document")
                else:
                    failed_count += 1
                    failures.append(f"Invoice ID {invoice_id}: {detail_result.get('message', 'Unknown error')}")
                    
            except Exception as e:
                failed_count += 1
                error_msg = str(e)
                failures.append(f"Invoice ID {invoice_id}: {error_msg}")
                frappe.log_error(f"Error importing invoice ID {invoice_id}: {error_msg}")
                continue
        
        frappe.db.commit()
        
        return {
            'success': True,
            'imported_count': imported_count,
            'skipped_count': skipped_count,
            'failed_count': failed_count,
            'failures': failures,
            'message': f'Import completed: {imported_count} imported, {skipped_count} skipped, {failed_count} failed'
        }
        
    except Exception as e:
        frappe.log_error(f"Multiple portal import error: {str(e)}")
        return {
            'success': False,
            'imported_count': 0,
            'skipped_count': 0,
            'failed_count': len(invoice_ids) if invoice_ids else 0,
            'failures': [f"System error: {str(e)}"],
            'message': f'Import failed: {str(e)}'
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
    """Create a new Purchase Invoice from portal data with comprehensive validation"""
    try:
        # First, validate all prerequisites
        validation = validate_invoice_prerequisites(invoice_data)
        
        if not validation['success']:
            # Return detailed error information
            error_details = {
                'success': False,
                'message': 'Invoice validation failed',
                'errors': validation['errors'],
                'warnings': validation['warnings'],
                'invoice_number': invoice_data.get('invoice_number', 'Unknown')
            }
            
            # Log the validation errors
            frappe.log_error(
                message=f"Invoice validation failed for {invoice_data.get('invoice_number', 'Unknown')}: " + 
                        "; ".join(validation['errors']),
                title="Invoice Validation Failed"
            )
            
            return error_details
        
        # Log warnings if any
        if validation['warnings']:
            frappe.log_error(
                message=f"Invoice validation warnings for {invoice_data.get('invoice_number', 'Unknown')}: " + 
                        "; ".join(validation['warnings']),
                title="Invoice Import Warnings"
            )
        
        # Proceed with invoice creation
        doc = frappe.new_doc('Purchase Invoice')
        
        # Set basic fields with validation
        invoice_number = invoice_data.get('invoice_number', '')
        if len(invoice_number) > 140:
            invoice_number = invoice_number[:137] + "..."
        
        doc.title = invoice_number
        
        # Get or create supplier (this should work now since we validated)
        supplier_result = get_or_create_supplier(invoice_data.get('vendor_names', 'Portal Vendor'))
        if isinstance(supplier_result, dict) and not supplier_result.get('success'):
            return supplier_result  # Return error details
        
        doc.supplier = supplier_result if isinstance(supplier_result, str) else supplier_result.get('supplier_name')
        doc.posting_date = frappe.utils.today()
        doc.due_date = invoice_data.get('due_date') or frappe.utils.add_days(frappe.utils.today(), 30)
        
        # Add custom fields for portal reference (with error handling)
        try:
            if hasattr(doc, 'custom_portal_invoice_id'):
                doc.custom_portal_invoice_id = invoice_data.get('invoice_id', '')
            if hasattr(doc, 'custom_portal_order_name'):
                order_name = invoice_data.get('order_name', '')[:140] if invoice_data.get('order_name') else ''
                doc.custom_portal_order_name = order_name
            if hasattr(doc, 'custom_customer_name'):
                customer_name = invoice_data.get('customer_name', '')[:140] if invoice_data.get('customer_name') else ''
                doc.custom_customer_name = customer_name
            if hasattr(doc, 'custom_branch'):
                branch = invoice_data.get('branch', '')[:140] if invoice_data.get('branch') else ''
                doc.custom_branch = branch
            if hasattr(doc, 'custom_sub_branch'):
                sub_branch = invoice_data.get('sub_branch', '')[:140] if invoice_data.get('sub_branch') else ''
                doc.custom_sub_branch = sub_branch
        except Exception as e:
            # If custom fields fail, log but continue
            frappe.log_error(
                message=f"Custom field setting failed for invoice {invoice_number}: {str(e)}",
                title="Custom Field Error"
            )
        
        # Add a basic item (you may need to customize this based on your item structure)
        item_result = get_or_create_item('Portal Import Item')
        if isinstance(item_result, dict) and not item_result.get('success'):
            return item_result  # Return error details
        
        item_code = item_result if isinstance(item_result, str) else item_result.get('item_code')
        
        doc.append('items', {
            'item_code': item_code,
            'qty': max(1, invoice_data.get('total_items', 1)),
            'rate': max(0, invoice_data.get('total_amount', 0)),
            'amount': max(0, invoice_data.get('total_amount', 0))
        })
        
        # Set remarks if available
        if invoice_data.get('remark'):
            remarks = str(invoice_data['remark'])[:140] if len(str(invoice_data['remark'])) > 140 else str(invoice_data['remark'])
            doc.remarks = remarks
        
        doc.save()
        
        # Only submit if save was successful and no validation errors
        if doc.docstatus == 0:  # Draft status
            try:
                doc.submit()
                return {
                    'success': True,
                    'message': f'Purchase Invoice {invoice_number} created and submitted successfully',
                    'invoice_name': doc.name,
                    'warnings': validation['warnings']
                }
            except Exception as submit_error:
                # If submission fails, keep as draft
                frappe.log_error(
                    message=f"Failed to submit invoice {invoice_number}: {str(submit_error)}",
                    title="Invoice Submission Failed"
                )
                return {
                    'success': True,
                    'message': f'Purchase Invoice {invoice_number} created as draft (submission failed)',
                    'invoice_name': doc.name,
                    'warnings': validation['warnings'] + [f"Submission failed: {str(submit_error)}"]
                }
        
        return {
            'success': True,
            'message': f'Purchase Invoice {invoice_number} created successfully',
            'invoice_name': doc.name,
            'warnings': validation['warnings']
        }
        
    except Exception as e:
        # Create detailed error message
        invoice_ref = invoice_data.get('invoice_number', 'Unknown')[:20]
        error_msg = str(e)
        
        frappe.log_error(
            message=f"Error creating Purchase Invoice for {invoice_ref}: {error_msg}",
            title=f"PI Creation Error - {invoice_ref}"
        )
        
        return {
            'success': False,
            'message': f'Failed to create Purchase Invoice for {invoice_ref}',
            'error': error_msg,
            'invoice_number': invoice_data.get('invoice_number', 'Unknown')
        }

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
        # Create concise error message to avoid title truncation
        error_msg = str(e)[:100] + "..." if len(str(e)) > 100 else str(e)
        frappe.log_error(
            message=f"Error updating Purchase Invoice: {error_msg}",
            title="Purchase Invoice Update Error"
        )

def get_or_create_supplier(vendor_names):
    """Get or create supplier from vendor names with detailed validation"""
    try:
        # Validate input
        if not vendor_names or vendor_names.strip() in ['', 'No Vendors', 'None']:
            return {
                'success': False,
                'message': 'Supplier/Vendor information is missing. Cannot create Purchase Invoice without valid supplier.',
                'error_type': 'missing_supplier'
            }
        
        # Use first vendor name or create a generic one
        supplier_name = vendor_names.split(',')[0].strip() if vendor_names and vendor_names != 'No Vendors' else 'Portal Vendor'
        
        # Truncate supplier name if too long
        if len(supplier_name) > 140:
            supplier_name = supplier_name[:137] + "..."
        
        # Check if supplier exists
        if frappe.db.exists('Supplier', supplier_name):
            return supplier_name
        
        # Create new supplier with minimal required fields only
        supplier = frappe.new_doc('Supplier')
        supplier.supplier_name = supplier_name
        
        # Check if supplier group exists
        supplier_groups = frappe.get_all('Supplier Group', limit=1)
        if supplier_groups:
            supplier.supplier_group = supplier_groups[0].name
        else:
            # Create default supplier group if none exists
            try:
                default_group = frappe.new_doc('Supplier Group')
                default_group.supplier_group_name = 'All Supplier Groups'
                default_group.save()
                supplier.supplier_group = default_group.name
            except Exception:
                return {
                    'success': False,
                    'message': 'No Supplier Group found in system. Please create at least one Supplier Group first.',
                    'error_type': 'missing_supplier_group'
                }
        
        # Only set custom fields if they exist and are manageable
        try:
            # Check if custom fields exist before setting them
            supplier_meta = frappe.get_meta('Supplier')
            custom_fields = [f.fieldname for f in supplier_meta.fields if f.fieldname.startswith('custom_')]
            
            # Set default values for custom fields if they exist
            for field in custom_fields:
                if hasattr(supplier, field):
                    field_meta = next((f for f in supplier_meta.fields if f.fieldname == field), None)
                    if field_meta:
                        if field_meta.fieldtype in ['Data', 'Small Text']:
                            setattr(supplier, field, '')  # Empty string for text fields
                        elif field_meta.fieldtype in ['Date', 'Datetime']:
                            setattr(supplier, field, None)  # None for date fields
                        elif field_meta.fieldtype in ['Currency', 'Float', 'Int']:
                            setattr(supplier, field, 0)  # 0 for numeric fields
                        elif field_meta.fieldtype == 'Check':
                            setattr(supplier, field, 0)  # 0 for checkbox fields
        except Exception as custom_error:
            # If custom field setting fails, log but continue
            frappe.log_error(
                message=f"Custom field setting failed for supplier '{supplier_name}': {str(custom_error)}",
                title="Supplier Custom Field Error"
            )
        
        try:
            supplier.save()
            return supplier.name
        except Exception as save_error:
            return {
                'success': False,
                'message': f'Failed to create supplier "{supplier_name}": {str(save_error)}',
                'error_type': 'supplier_creation_failed',
                'details': str(save_error)
            }
        
    except Exception as e:
        # Create detailed error message
        error_msg = str(e)
        frappe.log_error(
            message=f"Error in get_or_create_supplier for '{vendor_names}': {error_msg}",
            title="Supplier Processing Error"
        )
        
        # Try to return an existing fallback supplier
        try:
            fallback_suppliers = frappe.get_all('Supplier', limit=1)
            if fallback_suppliers:
                frappe.log_error(
                    message=f"Using fallback supplier: {fallback_suppliers[0]['name']}",
                    title="Fallback Supplier Used"
                )
                return fallback_suppliers[0]['name']
        except Exception:
            pass
            
        return {
            'success': False,
            'message': f'Failed to process supplier information: {error_msg}',
            'error_type': 'supplier_processing_error',
            'details': error_msg
        }

def get_or_create_item(item_name='Portal Import Item'):
    """Get or create a default item for portal imports with detailed validation"""
    try:
        # Truncate item name if too long
        if len(item_name) > 140:
            item_name = item_name[:137] + "..."
            
        if frappe.db.exists('Item', item_name):
            return item_name
        
        item = frappe.new_doc('Item')
        item.item_code = item_name
        item.item_name = item_name
        
        # Check if item group exists
        item_groups = frappe.get_all('Item Group', limit=1)
        if item_groups:
            item.item_group = item_groups[0].name
        else:
            return {
                'success': False,
                'message': 'No Item Group found in system. Please create at least one Item Group first.',
                'error_type': 'missing_item_group'
            }
        
        item.stock_uom = 'Nos'
        item.is_purchase_item = 1
        item.is_sales_item = 0
        item.is_stock_item = 0  # Non-stock item for services
        
        try:
            item.save()
            return item.name
        except Exception as save_error:
            return {
                'success': False,
                'message': f'Failed to create item "{item_name}": {str(save_error)}',
                'error_type': 'item_creation_failed',
                'details': str(save_error)
            }
        
    except Exception as e:
        error_msg = str(e)
        frappe.log_error(
            message=f"Error creating item '{item_name}': {error_msg}",
            title="Item Creation Error"
        )
        
        # Try to return an existing fallback item
        try:
            fallback_items = frappe.get_all('Item', 
                                          filters={'is_purchase_item': 1}, 
                                          limit=1)
            if fallback_items:
                return fallback_items[0]['name']
        except Exception:
            pass
            
        return {
            'success': False,
            'message': f'Failed to process item: {error_msg}',
            'error_type': 'item_processing_error',
            'details': error_msg
        }

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

@frappe.whitelist()
def batch_import_ago2o_invoices(latest_only=False):
    """
    Import AGO2O pattern invoices from remote database to ERPNext
    
    Args:
        latest_only: If True, import only AGO2O/25-26 series. If False, import all AGO2O invoices
    """
    try:
        result = {
            'success': True,
            'total_processed': 0,
            'successful_imports': 0,
            'failed_imports': 0,
            'validation_errors': [],
            'import_errors': [],
            'imported_invoices': [],
            'skipped_invoices': []
        }
        
        # 1. Get AGO2O invoices from remote database
        with get_external_db_connection() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                if latest_only:
                    # Only get AGO2O/25-26 series (current financial year invoices)
                    cursor.execute('''
                        SELECT pr.*, v.name as vendor_name, v.email as vendor_email, v.address as vendor_address
                        FROM purchase_requisitions pr
                        LEFT JOIN vendors v ON pr.vendor_created = v.id
                        WHERE pr.invoice_number LIKE '%AGO2O/25-26%'
                        AND pr.is_delete = 0 
                        ORDER BY pr.invoice_series ASC, pr.id ASC
                    ''')
                else:
                    # Get all AGO2O invoices
                    cursor.execute('''
                        SELECT pr.*, v.name as vendor_name, v.email as vendor_email, v.address as vendor_address
                        FROM purchase_requisitions pr
                        LEFT JOIN vendors v ON pr.vendor_created = v.id
                        WHERE pr.invoice_number LIKE '%AGO2O%'
                        AND pr.is_delete = 0 
                        ORDER BY pr.invoice_series ASC, pr.id ASC
                    ''')
                
                remote_invoices = cursor.fetchall()
        
        # 2. Group invoices by invoice_number to handle duplicates
        invoices_grouped = {}
        for invoice in remote_invoices:
            inv_num = invoice['invoice_number']
            if inv_num not in invoices_grouped:
                invoices_grouped[inv_num] = invoice
        
        # 3. Process each grouped invoice
        for invoice_number, invoice_data in invoices_grouped.items():
            result['total_processed'] += 1
            header = invoice_data
            
            try:
                # Check if invoice already exists in ERPNext
                existing = frappe.db.get_value("Purchase Invoice", {"title": invoice_number})
                if existing:
                    result['skipped_invoices'].append({
                        'invoice_number': invoice_number,
                        'reason': 'Already exists in ERPNext',
                        'erpnext_name': existing
                    })
                    continue
                
                # Validate prerequisites with comprehensive checking
                # Map the invoice data to the expected format for validation
                validation_data = {
                    'customer_name': header.get('vendor_name'),  # vendor is customer in this context
                    'customer_email': header.get('vendor_email'),
                    'customer_gstn': header.get('vendor_gstn'),
                    'customer_address': header.get('vendor_address'),
                    'entity_code': header.get('entity'),
                    'branch_name': header.get('entity'),  # entity is branch
                    'subentity_code': header.get('subentity_id'),
                    'sub_branch_name': header.get('subentity_id'),
                    'invoice_number': invoice_number,
                    'amount': header.get('total_amount', 0)
                }
                
                validation_result = validate_invoice_prerequisites(validation_data)
                
                if not validation_result['success']:
                    # Collect detailed validation errors
                    error_details = {
                        'invoice_number': invoice_number,
                        'errors': validation_result['errors'],
                        'missing_entities': validation_result['missing_entities'],
                        'suggestions': validation_result['suggestions']
                    }
                    result['validation_errors'].append(error_details)
                    result['failed_imports'] += 1
                    continue
                
                # Create Purchase Invoice in ERPNext
                doc = frappe.new_doc("Purchase Invoice")
                
                # Map basic fields
                doc.supplier = validation_result['supplier_name']
                doc.title = invoice_number
                doc.bill_no = header['order_code']
                doc.bill_date = safe_date_format(header['created_at'], '%Y-%m-%d')
                doc.posting_date = doc.bill_date
                doc.due_date = doc.bill_date
                doc.company = "Ascra Technologies Pvt. Ltd."
                doc.currency = "INR"
                doc.is_return = 0
                doc.update_stock = 0
                
                # Add custom fields if they exist
                if frappe.db.has_column("Purchase Invoice", "custom_branch"):
                    doc.custom_branch = validation_result.get('branch_name', '')
                if frappe.db.has_column("Purchase Invoice", "custom_sub_branch"):
                    doc.custom_sub_branch = validation_result.get('sub_branch_name', '')
                if frappe.db.has_column("Purchase Invoice", "custom_portal_id"):
                    doc.custom_portal_id = str(header['id'])
                if frappe.db.has_column("Purchase Invoice", "custom_entity_id"):
                    doc.custom_entity_id = str(header['entity'])
                
                # Add a standard item for AGO2O invoices
                default_amount = 10000  # Default amount for AGO2O invoices
                doc.append("items", {
                    "item_code": "General Item",
                    "item_name": f"AGO2O Invoice {invoice_number}",
                    "description": f"Imported AGO2O invoice {invoice_number} from {header.get('vendor_name', 'Unknown Vendor')}",
                    "qty": 1,
                    "rate": default_amount,
                    "amount": default_amount,
                    "uom": "Nos"
                })
                
                # Add remarks
                doc.remarks = (header.get('remark', '') or f'Imported AGO2O invoice {invoice_number} - FY {invoice_number.split("/")[1] if "/" in invoice_number else ""}')[:140]
                
                # Insert and submit
                doc.insert(ignore_permissions=True)
                frappe.db.commit()
                
                result['successful_imports'] += 1
                result['imported_invoices'].append({
                    'invoice_number': invoice_number,
                    'erpnext_name': doc.name,
                    'supplier': doc.supplier,
                    'total_amount': default_amount,
                    'financial_year': invoice_number.split("/")[1] if "/" in invoice_number else "Unknown",
                    'series_number': header.get('invoice_series', 0)
                })
                
            except Exception as e:
                result['failed_imports'] += 1
                result['import_errors'].append({
                    'invoice_number': invoice_number,
                    'error': str(e)[:500]  # Truncate long errors
                })
                frappe.log_error(f"Error importing AGO2O invoice {invoice_number}: {str(e)}")
        
        # 4. Prepare final result
        result['message'] = f"AGO2O Import completed. Processed: {result['total_processed']}, " \
                           f"Successful: {result['successful_imports']}, " \
                           f"Failed: {result['failed_imports']}, " \
                           f"Skipped: {len(result['skipped_invoices'])}"
        
        return result
        
    except Exception as e:
        frappe.log_error(f"Error in batch_import_ago2o_invoices: {str(e)}")
        return {
            'success': False,
            'message': f'Error during AGO2O import: {str(e)}',
            'total_processed': 0,
            'successful_imports': 0,
            'failed_imports': 0,
            'errors': [str(e)]
        }