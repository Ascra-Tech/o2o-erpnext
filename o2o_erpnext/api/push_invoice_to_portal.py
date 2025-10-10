import frappe
import pymysql
from frappe import _
from datetime import datetime
import pymysql.cursors
from o2o_erpnext.config.external_db_updated import get_external_db_connection

@frappe.whitelist()
def push_purchase_invoice_to_portal(invoice_name, force_update=False):
    """
    Push a Purchase Invoice from ERPNext to the remote Purchase Requisition table
    
    Args:
        invoice_name (str): Name of the Purchase Invoice to push
        force_update (bool): Whether to update if already exists
        
    Returns:
        dict: Operation result with success status and details
    """
    try:
        # Get the Purchase Invoice document
        invoice_doc = frappe.get_doc('Purchase Invoice', invoice_name)
        
        # Validate the invoice
        validation_result = validate_invoice_for_push(invoice_doc)
        if not validation_result['valid']:
            return {
                'success': False,
                'message': f'Validation failed: {validation_result["message"]}',
                'invoice_name': invoice_name
            }
        
        # Check if already exists in portal
        existing_check = check_invoice_exists_in_portal(invoice_doc)
        if existing_check['exists'] and not force_update:
            return {
                'success': False,
                'message': f'Invoice already exists in portal with ID {existing_check["portal_id"]}. Use force_update=True to override.',
                'invoice_name': invoice_name,
                'portal_id': existing_check['portal_id']
            }
        
        # Transform ERPNext data to portal format
        portal_data = transform_invoice_to_portal_format(invoice_doc)
        
        # Push to portal database
        if existing_check['exists'] and force_update:
            portal_id = update_invoice_in_portal(existing_check['portal_id'], portal_data)
            operation = 'updated'
        else:
            portal_id = insert_invoice_to_portal(portal_data)
            operation = 'created'
        
        # Update ERPNext with portal sync info
        update_invoice_sync_status(invoice_doc, portal_id, operation)
        
        return {
            'success': True,
            'message': f'Invoice {operation} successfully in portal with ID {portal_id}',
            'invoice_name': invoice_name,
            'portal_id': portal_id,
            'operation': operation
        }
        
    except Exception as e:
        frappe.logger().error(f"Failed to push invoice {invoice_name}: {str(e)}")
        return {
            'success': False,
            'message': f'Error pushing invoice: {str(e)}',
            'invoice_name': invoice_name
        }

def validate_invoice_for_push(invoice_doc):
    """
    Validate if the invoice can be pushed to portal
    
    Args:
        invoice_doc: Purchase Invoice document
        
    Returns:
        dict: Validation result
    """
    try:
        errors = []
        
        # Check required fields
        if not invoice_doc.get('entity'):
            errors.append('Entity is required')
            
        if not invoice_doc.get('subentity_id'):
            errors.append('Subentity ID is required')
            
        if not invoice_doc.get('title') and not invoice_doc.get('portal_invoice_number'):
            errors.append('Invoice title or portal invoice number is required')
            
        if invoice_doc.docstatus != 1:
            errors.append('Invoice must be submitted before pushing to portal')
        
        # Check entity/subentity exist in portal
        entity_check = validate_entity_subentity_in_portal(
            invoice_doc.get('entity'), 
            invoice_doc.get('subentity_id')
        )
        if not entity_check['valid']:
            errors.append(f'Entity/Subentity validation failed: {entity_check["message"]}')
        
        return {
            'valid': len(errors) == 0,
            'message': '; '.join(errors) if errors else 'Validation passed',
            'errors': errors
        }
        
    except Exception as e:
        return {
            'valid': False,
            'message': f'Validation error: {str(e)}',
            'errors': [str(e)]
        }

def validate_entity_subentity_in_portal(entity_id, subentity_id):
    """
    Validate entity and subentity exist in portal
    
    Args:
        entity_id: Entity ID
        subentity_id: Subentity ID
        
    Returns:
        dict: Validation result
    """
    try:
        with get_external_db_connection() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                # Check entity exists
                cursor.execute("SELECT id, name FROM entitys WHERE id = %s", (entity_id,))
                entity = cursor.fetchone()
                
                if not entity:
                    return {
                        'valid': False,
                        'message': f'Entity ID {entity_id} not found in portal'
                    }
                
                # Check subentity exists and belongs to entity
                cursor.execute(
                    "SELECT id, name FROM subentitys WHERE id = %s AND entity_id = %s", 
                    (subentity_id, entity_id)
                )
                subentity = cursor.fetchone()
                
                if not subentity:
                    return {
                        'valid': False,
                        'message': f'Subentity ID {subentity_id} not found for entity {entity_id}'
                    }
                
                return {
                    'valid': True,
                    'message': f'Entity: {entity["name"]}, Subentity: {subentity["name"]}',
                    'entity': entity,
                    'subentity': subentity
                }
                
    except Exception as e:
        return {
            'valid': False,
            'message': f'Database validation error: {str(e)}'
        }

def check_invoice_exists_in_portal(invoice_doc):
    """
    Check if invoice already exists in portal
    
    Args:
        invoice_doc: Purchase Invoice document
        
    Returns:
        dict: Existence check result
    """
    try:
        invoice_number = invoice_doc.get('portal_invoice_number') or invoice_doc.get('title')
        
        with get_external_db_connection() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(
                    "SELECT id FROM purchase_requisitions WHERE invoice_number = %s AND is_delete = 0",
                    (invoice_number,)
                )
                existing = cursor.fetchone()
                
                return {
                    'exists': bool(existing),
                    'portal_id': existing['id'] if existing else None
                }
                
    except Exception as e:
        frappe.logger().error(f"Error checking invoice existence: {str(e)}")
        return {
            'exists': False,
            'portal_id': None
        }

def transform_invoice_to_portal_format(invoice_doc):
    """
    Transform ERPNext Purchase Invoice to portal purchase_requisitions format
    
    Args:
        invoice_doc: Purchase Invoice document
        
    Returns:
        dict: Portal-formatted data
    """
    try:
        # Get invoice number (prefer portal_invoice_number)
        invoice_number = invoice_doc.get('portal_invoice_number') or invoice_doc.get('title')
        
        # Map status from ERPNext to portal
        status_mapping = {
            'Draft': 1,        # Awaiting Approval
            'Submitted': 2,    # Approved 
            'Paid': 4,         # Requisition Approved
            'Cancelled': 3,    # Rejected
            'Return': 5        # Requisition Rejected
        }
        
        order_status = status_mapping.get(invoice_doc.status, 1)
        
        # Prepare portal data
        portal_data = {
            # Core identification
            'entity': str(invoice_doc.get('entity') or '1'),
            'subentity_id': str(invoice_doc.get('subentity_id') or '1'),
            'order_name': invoice_doc.name,  # ERPNext document name
            'order_code': invoice_doc.get('order_code') or invoice_doc.get('po_no') or '',
            'invoice_number': invoice_number,
            
            # Dates
            'delivery_date': format_date_for_portal(invoice_doc.get('due_date')),
            'validity_date': format_date_for_portal(invoice_doc.get('due_date')),  # Use due_date as validity
            'requisition_at': format_date_for_portal(invoice_doc.get('posting_date') or datetime.now()),
            'created_at': format_date_for_portal(invoice_doc.get('creation') or datetime.now()),
            'updated_at': format_date_for_portal(invoice_doc.get('modified') or datetime.now()),
            
            # Content
            'address': invoice_doc.get('shipping_address_display') or invoice_doc.get('supplier_address') or '',
            'remark': invoice_doc.get('remarks') or '',
            
            # Status and flags
            'order_status': order_status,
            'status': 'active' if invoice_doc.docstatus == 1 else 'inactive',
            'is_delete': 1 if invoice_doc.docstatus == 2 else 0,  # Cancelled = deleted
            
            # Invoice specific
            'invoice_generated': 1,  # This IS an invoice
            'invoice_generated_at': format_date_for_portal(datetime.now()),
            'is_new_invoice': 1,
            'is_invoice_cancel': 1 if invoice_doc.docstatus == 2 else 0,
            'invoice_cancel_date': format_date_for_portal(datetime.now()) if invoice_doc.docstatus == 2 else None,
            
            # Defaults
            'acknowledgement': 0,
            'gru_ack': 0,
            'gru_ack_remark': None,
            'currency_id': get_currency_id(invoice_doc.get('currency', 'INR')),
            'category': 1,  # Default category
            'amend_no': '',
            'amendment_date': None,
            'finance_status': 0,
            'reason_id': None,
            'reason': '',
            'clone_id': 0,
            'dispatch_status': None,
            'transportation_mode': '',
            'vehicle_no': '',
            'challan_number': '',
            'challan_date': None,
            'awb_number': None,
            'weight': None,
            'weight_rate': None,
            'freight_rate': '',
            'freight_cost': '',
            'total_wt': None,
            'adv_shipping_detatils': None,
            'import_files': None,
            'user_file_name': None,
            'approved_at': None,
            'approved_by': None,
            'rejected_at': None,
            'rejected_by': None,
            'invoice_view': None,
            'invoice_series': int(invoice_doc.get('invoice_series') or 1),
            'is_visible_header': 1,
            'created_by': get_portal_user_id(invoice_doc.get('owner')),
            'vendor_created': 0,
            'updated_by': get_portal_user_id(invoice_doc.get('modified_by')),
            'gst_percentage': '18',  # Default GST
            'credit_note_number': ''
        }
        
        return portal_data
        
    except Exception as e:
        frappe.logger().error(f"Error transforming invoice data: {str(e)}")
        raise

def format_date_for_portal(date_value):
    """
    Format date for portal database
    
    Args:
        date_value: Date value (datetime, string, or None)
        
    Returns:
        str: Formatted date string or None
    """
    if not date_value:
        return None
        
    if isinstance(date_value, str):
        try:
            date_value = datetime.strptime(date_value, '%Y-%m-%d')
        except:
            try:
                date_value = datetime.strptime(date_value, '%Y-%m-%d %H:%M:%S')
            except:
                return None
    
    if isinstance(date_value, datetime):
        return date_value.strftime('%Y-%m-%d %H:%M:%S')
    
    return None

def get_currency_id(currency_code):
    """
    Map ERPNext currency to portal currency ID
    
    Args:
        currency_code: Currency code (INR, USD, etc.)
        
    Returns:
        int: Portal currency ID
    """
    currency_mapping = {
        'INR': 1,
        'USD': 2,
        'EUR': 3,
        'GBP': 4
    }
    
    return currency_mapping.get(currency_code, 1)  # Default to INR

def get_portal_user_id(user_email):
    """
    Map ERPNext user to portal user ID
    
    Args:
        user_email: ERPNext user email
        
    Returns:
        int: Portal user ID
    """
    # For now, return default system user ID
    # TODO: Implement proper user mapping
    return 83  # Default system user in portal

def insert_invoice_to_portal(portal_data):
    """
    Insert new invoice record to portal
    
    Args:
        portal_data: Portal-formatted data
        
    Returns:
        int: Inserted record ID
    """
    try:
        with get_external_db_connection() as conn:
            with conn.cursor() as cursor:
                # Prepare INSERT query
                fields = list(portal_data.keys())
                placeholders = ['%s'] * len(fields)
                values = [portal_data[field] for field in fields]
                
                query = f"""
                INSERT INTO purchase_requisitions ({', '.join(fields)})
                VALUES ({', '.join(placeholders)})
                """
                
                cursor.execute(query, values)
                conn.commit()
                
                # Get the inserted ID
                portal_id = cursor.lastrowid
                
                frappe.logger().info(f"Inserted invoice to portal with ID: {portal_id}")
                return portal_id
                
    except Exception as e:
        frappe.logger().error(f"Error inserting to portal: {str(e)}")
        raise

def update_invoice_in_portal(portal_id, portal_data):
    """
    Update existing invoice record in portal
    
    Args:
        portal_id: Portal record ID
        portal_data: Portal-formatted data
        
    Returns:
        int: Updated record ID
    """
    try:
        with get_external_db_connection() as conn:
            with conn.cursor() as cursor:
                # Prepare UPDATE query
                set_clauses = [f"{field} = %s" for field in portal_data.keys()]
                values = list(portal_data.values())
                values.append(portal_id)  # For WHERE clause
                
                query = f"""
                UPDATE purchase_requisitions 
                SET {', '.join(set_clauses)}, updated_at = NOW()
                WHERE id = %s
                """
                
                cursor.execute(query, values)
                conn.commit()
                
                frappe.logger().info(f"Updated portal invoice ID: {portal_id}")
                return portal_id
                
    except Exception as e:
        frappe.logger().error(f"Error updating portal: {str(e)}")
        raise

def update_invoice_sync_status(invoice_doc, portal_id, operation):
    """
    Update ERPNext invoice with portal sync information
    
    Args:
        invoice_doc: Purchase Invoice document
        portal_id: Portal record ID
        operation: Operation performed (created/updated)
    """
    try:
        # Add custom fields if they don't exist
        if not frappe.db.exists('Custom Field', {'dt': 'Purchase Invoice', 'fieldname': 'portal_sync_id'}):
            create_portal_sync_custom_fields()
        
        # Update the document
        frappe.db.set_value('Purchase Invoice', invoice_doc.name, {
            'portal_sync_id': portal_id,
            'portal_sync_status': 'Synced',
            'portal_sync_date': datetime.now(),
            'portal_sync_operation': operation
        })
        
        frappe.db.commit()
        
    except Exception as e:
        frappe.logger().error(f"Error updating sync status: {str(e)}")

def create_portal_sync_custom_fields():
    """
    Create custom fields for portal sync tracking
    """
    custom_fields = [
        {
            'dt': 'Purchase Invoice',
            'fieldname': 'portal_sync_id',
            'label': 'Portal Sync ID',
            'fieldtype': 'Int',
            'read_only': 1,
            'description': 'ID of the record in portal database'
        },
        {
            'dt': 'Purchase Invoice',
            'fieldname': 'portal_sync_status',
            'label': 'Portal Sync Status',
            'fieldtype': 'Select',
            'options': 'Not Synced\nSynced\nFailed\nPending',
            'default': 'Not Synced',
            'read_only': 1
        },
        {
            'dt': 'Purchase Invoice',
            'fieldname': 'portal_sync_date',
            'label': 'Portal Sync Date',
            'fieldtype': 'Datetime',
            'read_only': 1
        },
        {
            'dt': 'Purchase Invoice',
            'fieldname': 'portal_sync_operation',
            'label': 'Portal Sync Operation',
            'fieldtype': 'Data',
            'read_only': 1
        }
    ]
    
    for field_data in custom_fields:
        if not frappe.db.exists('Custom Field', {'dt': field_data['dt'], 'fieldname': field_data['fieldname']}):
            custom_field = frappe.get_doc({
                'doctype': 'Custom Field',
                **field_data
            })
            custom_field.insert()

@frappe.whitelist()
def push_multiple_invoices(invoice_names, force_update=False):
    """
    Push multiple Purchase Invoices to portal
    
    Args:
        invoice_names: List of invoice names or comma-separated string
        force_update: Whether to update existing records
        
    Returns:
        dict: Batch operation results
    """
    try:
        if isinstance(invoice_names, str):
            invoice_names = [name.strip() for name in invoice_names.split(',')]
        
        results = []
        success_count = 0
        failed_count = 0
        
        for invoice_name in invoice_names:
            result = push_purchase_invoice_to_portal(invoice_name, force_update)
            results.append(result)
            
            if result['success']:
                success_count += 1
            else:
                failed_count += 1
        
        return {
            'success': True,
            'message': f'Batch operation completed: {success_count} succeeded, {failed_count} failed',
            'total_processed': len(invoice_names),
            'success_count': success_count,
            'failed_count': failed_count,
            'results': results
        }
        
    except Exception as e:
        return {
            'success': False,
            'message': f'Batch operation failed: {str(e)}',
            'results': []
        }