"""
Enhanced ERPNext to ProcureUAT Sync Module
Based on comprehensive field mapping documentation and verified schema
Implements push functionality for Purchase Invoice to Purchase Requisition table
"""

import frappe
from frappe.utils import flt, getdate, now_datetime, add_days, get_datetime
from datetime import datetime, time
import json
import re
from decimal import Decimal

# Import our database connection module
from o2o_erpnext.config.external_db_updated import get_external_db_connection

def auto_push_invoice_on_submit(doc, method=None):
    """
    Automatic push function called by ERPNext hooks on Purchase Invoice submission
    
    Args:
        doc: Purchase Invoice document being submitted
        method: Hook method name (on_submit)
    """
    # Only proceed if this is a submission (not draft or cancel)
    if doc.docstatus != 1:
        return
    
    # Check if sync should be skipped
    if getattr(doc, 'custom_skip_external_sync', 0):
        frappe.logger().info(f"Skipping external sync for invoice {doc.name} - sync disabled by user")
        return
    
    try:
        # Call the main push function
        result = push_invoice_to_procureuat(doc.name, force_update=False)
        
        if result['success']:
            frappe.logger().info(f"Successfully auto-pushed invoice {doc.name} to portal on submission")
        else:
            # Log the error but don't fail the submission
            frappe.logger().warning(f"Failed to auto-push invoice {doc.name} to portal: {result['message']}")
            
    except Exception as e:
        # Log the error but don't fail the submission
        frappe.logger().error(f"Error auto-pushing invoice {doc.name} to portal: {str(e)}")

@frappe.whitelist()
def push_invoice_to_procureuat(invoice_name, force_update=False):
    """
    Main entry point for pushing Purchase Invoice to ProcureUAT
    This function is called from the JavaScript button "Send to AGO2O-PHP"
    
    Args:
        invoice_name (str): Name of the Purchase Invoice to push
        force_update (bool): Whether to update if already exists
        
    Returns:
        dict: Push result with success status and details
    """
    try:
        # Get Purchase Invoice document
        invoice_doc = frappe.get_doc('Purchase Invoice', invoice_name)
        
        # Validate invoice for push
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
            match_info = f"Duplicate found by {existing_check['match_type']}: '{existing_check['match_value']}'"
            return {
                'success': False,
                'message': f'Invoice already exists in portal with ID {existing_check["portal_id"]}. {match_info}. Use force_update=True to override.',
                'invoice_name': invoice_name,
                'portal_record_id': existing_check['portal_id'],
                'duplicate_match': existing_check
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
            'portal_record_id': portal_id,
            'portal_status': 'active',
            'operation': operation,
            'notes': f'Successfully pushed to purchase_requisitions table'
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
    Validate if the invoice can be pushed to portal based on documentation requirements
    
    Args:
        invoice_doc: Purchase Invoice document
        
    Returns:
        dict: Validation result with valid boolean and message
    """
    try:
        errors = []
        
        # Check mandatory fields from documentation
        if not invoice_doc.get('supplier'):
            errors.append('Supplier is required (maps to entity)')
            
        if not invoice_doc.get('title'):
            errors.append('Title is required (maps to order_name)')
            
        if not invoice_doc.get('name'):
            errors.append('Invoice Number is required (maps to order_code)')
            
        # Check document status
        if invoice_doc.docstatus != 1:
            errors.append('Invoice must be submitted before pushing to portal')
        
        # Check for essential dates
        if not invoice_doc.get('posting_date'):
            errors.append('Posting Date is required (maps to requisition_at)')
            
        # Check if required custom fields exist (from documentation)
        if not invoice_doc.get('custom_sub_branch'):
            errors.append('Sub Branch is required (maps to subentity_id)')
            
        # Note: supplier_address is optional - if not provided, fallback address will be used
        if not invoice_doc.get('supplier_address'):
            frappe.logger().warning(f"Invoice {invoice_doc.get('name')}: No supplier_address found, will use fallback address")
            
        if errors:
            return {
                'valid': False,
                'message': '; '.join(errors)
            }
        
        return {
            'valid': True,
            'message': 'Invoice passed all validation checks'
        }
        
    except Exception as e:
        return {
            'valid': False,
            'message': f'Validation error: {str(e)}'
        }

def check_invoice_exists_in_portal(invoice_doc):
    """
    Check if invoice already exists in portal by multiple criteria:
    1. ERPNext Invoice Number (order_code field)
    2. Supplier Invoice Number (invoice_number field) - if provided
    
    Args:
        invoice_doc: Purchase Invoice document
        
    Returns:
        dict: Existence check result with exists boolean, portal_id, and match_type
    """
    try:
        erpnext_invoice_number = invoice_doc.get('name')  # ERPNext Invoice Number (e.g., CINV-24-00001)
        supplier_invoice_number = invoice_doc.get('bill_no')  # Supplier Invoice Number
        
        with get_external_db_connection() as conn:
            with conn.cursor() as cursor:
                # Check for ERPNext invoice number (order_code)
                cursor.execute(
                    "SELECT id, order_code, invoice_number FROM purchase_requisitions WHERE order_code = %s AND is_delete = 0",
                    (erpnext_invoice_number,)
                )
                erpnext_match = cursor.fetchone()
                
                if erpnext_match:
                    return {
                        'exists': True,
                        'portal_id': erpnext_match['id'],
                        'match_type': 'erpnext_invoice_number',
                        'match_value': erpnext_invoice_number,
                        'existing_record': erpnext_match
                    }
                
                # Check for supplier invoice number (invoice_number) if provided
                if supplier_invoice_number:
                    cursor.execute(
                        "SELECT id, order_code, invoice_number FROM purchase_requisitions WHERE invoice_number = %s AND is_delete = 0",
                        (supplier_invoice_number,)
                    )
                    supplier_match = cursor.fetchone()
                    
                    if supplier_match:
                        return {
                            'exists': True,
                            'portal_id': supplier_match['id'],
                            'match_type': 'supplier_invoice_number',
                            'match_value': supplier_invoice_number,
                            'existing_record': supplier_match
                        }
                
                # No duplicates found
                return {
                    'exists': False,
                    'portal_id': None,
                    'match_type': None,
                    'match_value': None
                }
                
    except Exception as e:
        frappe.logger().error(f"Error checking invoice existence: {str(e)}")
        return {
            'exists': False,
            'portal_id': None,
            'match_type': 'error',
            'error': str(e)
        }

def transform_invoice_to_portal_format(invoice_doc):
    """
    Transform ERPNext Purchase Invoice to ProcureUAT purchase_requisitions format
    Based on FINAL_VERIFIED_Field_Mapping_Frappe_to_PHP.csv documentation
    
    Args:
        invoice_doc: ERPNext Purchase Invoice document
        
    Returns:
        dict: Transformed data for purchase_requisitions table
    """
    # Basic required fields mapping
    # NOTE: Field Mapping Clarification:
    # - order_code: ERPNext Invoice Number (name) like "CINV-24-00001" - Required for portal
    # - invoice_number: Supplier Invoice Number (bill_no) - For reference only
    portal_data = {
        # Primary identification (MANDATORY)
        'entity': map_supplier_to_entity(invoice_doc.get('supplier')),
        'subentity_id': map_sub_branch_to_subentity(invoice_doc.get('custom_sub_branch')),
        'order_name': str(invoice_doc.get('title', ''))[:255],  # Truncate to 255 chars
        'order_code': str(invoice_doc.get('name', ''))[:255],  # ERPNext Invoice Number (e.g., CINV-24-00001)
        
        # Dates (converted to MySQL datetime format)
        'delivery_date': format_date_for_portal(invoice_doc.get('due_date')),
        'validity_date': calculate_validity_date(invoice_doc.get('due_date')),
        'requisition_at': combine_posting_datetime(invoice_doc.get('posting_date'), invoice_doc.get('posting_time')),
        'amendment_date': format_date_for_portal(invoice_doc.get('modified')) if invoice_doc.get('amended_from') else None,
        'created_at': format_date_for_portal(invoice_doc.get('creation')),
        'updated_at': format_date_for_portal(datetime.now()),
        
        # Address and logistics (MANDATORY fields)
        'address': get_supplier_address(invoice_doc.get('supplier_address')) or 'ERPNext Import - Address TBD',
        'transportation_mode': str(invoice_doc.get('mode_of_transport', 'Road'))[:100] or 'Road',
        'vehicle_no': str(invoice_doc.get('vehicle_no', 'TBD'))[:100] or 'TBD',
        'challan_number': str(invoice_doc.get('supplier_delivery_note', 'TBD'))[:100] or 'TBD',
        'awb_number': str(invoice_doc.get('lr_no', ''))[:250] or None,
        
        # Weight and freight calculations
        'weight': str(invoice_doc.get('total_net_weight', '')) or None,
        'total_wt': float(invoice_doc.get('total_net_weight', 0)) if invoice_doc.get('total_net_weight') else None,
        'freight_cost': str(invoice_doc.get('custom_freight_amount', '0.00')) or '0.00',
        'freight_rate': calculate_freight_rate(invoice_doc.get('custom_freight_amount'), invoice_doc.get('total_net_weight')) or '0.00',
        'weight_rate': calculate_freight_rate(invoice_doc.get('custom_freight_amount'), invoice_doc.get('total_net_weight')),
        
        # Status mappings
        'acknowledgement': map_docstatus_to_acknowledgement(invoice_doc.docstatus),
        'order_status': map_docstatus_to_order_status(invoice_doc.docstatus),
        'status': str(invoice_doc.get('status', 'Draft'))[:50],
        'finance_status': map_outstanding_to_finance_status(invoice_doc.get('outstanding_amount', 0)),
        
        # Invoice specific fields
        'invoice_number': str(invoice_doc.get('bill_no', ''))[:255],  # Supplier Invoice Number
        'invoice_series': extract_invoice_series(invoice_doc.get('naming_series', '')) or 0,
        'invoice_generated': 1 if invoice_doc.docstatus >= 1 else 0,
        'invoice_generated_at': combine_posting_datetime(invoice_doc.get('posting_date'), invoice_doc.get('posting_time')) if invoice_doc.docstatus >= 1 else None,
        'is_new_invoice': 1,  # Always 1 for imports from Frappe
        'is_invoice_cancel': 0,  # 0 = not cancelled (based on data analysis)
        'invoice_cancel_date': format_date_for_portal(invoice_doc.get('modified')) if invoice_doc.docstatus == 2 or invoice_doc.get('is_return') else None,
        'credit_note_number': str(invoice_doc.get('return_against', ''))[:100] if invoice_doc.get('is_return') else '',
        
        # User mappings
        'created_by': map_user_to_portal_id(invoice_doc.get('owner')),
        'updated_by': map_user_to_portal_id(invoice_doc.get('modified_by')),
        'requisition_by': map_user_to_portal_id(invoice_doc.get('owner')),
        'approved_by': map_user_to_portal_id(invoice_doc.get('modified_by')) if invoice_doc.docstatus == 1 else None,
        'approved_at': format_date_for_portal(invoice_doc.get('modified')) if invoice_doc.docstatus == 1 else None,
        
        # Required fields with defaults
        'remark': clean_html_content(invoice_doc.get('remarks', 'Purchase Invoice imported from ERPNext')) or 'Purchase Invoice imported from ERPNext',
        'reason': 'Purchase Invoice imported from ERPNext',
        'category': 0,  # Integer category (0 = most common category based on data analysis)
        'amend_no': extract_amendment_number(invoice_doc.get('amended_from')) or '',
        'gst_percentage': calculate_gst_percentage(invoice_doc) or '5',
        'currency_id': map_currency_to_id(invoice_doc.get('currency', 'INR')) or 1,
        
        # Status field (MANDATORY) 
        'status': str(invoice_doc.get('status', 'active'))[:50] or 'active',
        
        # Default/hardcoded values per documentation
        'gru_ack': 0,
        'gru_ack_remark': None,
        'clone_id': 0,
        'is_delete': 0,
        'dispatch_status': None,
        'challan_date': None,
        'import_files': None,
        'user_file_name': None,
        'rejected_at': None,
        'rejected_by': None,
        'invoice_view': None,
        'is_visible_header': 1,
        'vendor_created': 0,
        'reason_id': None,
        'adv_shipping_detatils': None
    }
    
    return portal_data
    
def insert_invoice_to_portal(portal_data):
    """
    Insert new invoice record to portal database
    
    Args:
        portal_data: Dictionary with transformed data for purchase_requisitions table
        
    Returns:
        int: Portal record ID
    """
    try:
        with get_external_db_connection() as conn:
            with conn.cursor() as cursor:
                # Build INSERT query
                fields = list(portal_data.keys())
                placeholders = ', '.join(['%s'] * len(fields))
                query = f"INSERT INTO purchase_requisitions ({', '.join(fields)}) VALUES ({placeholders})"
                
                # Execute insert
                cursor.execute(query, list(portal_data.values()))
                portal_id = cursor.lastrowid
                
                # Commit transaction
                conn.commit()
                
                frappe.logger().info(f"Inserted new portal record with ID: {portal_id}")
                return portal_id
                
    except Exception as e:
        frappe.logger().error(f"Error inserting to portal: {str(e)}")
        raise

def update_invoice_in_portal(portal_id, portal_data):
    """
    Update existing invoice record in portal database
    
    Args:
        portal_id: Portal record ID to update
        portal_data: Dictionary with updated data
        
    Returns:
        int: Portal record ID
    """
    try:
        with get_external_db_connection() as conn:
            with conn.cursor() as cursor:
                # Build UPDATE query
                set_clause = ', '.join([f"{field} = %s" for field in portal_data.keys()])
                query = f"UPDATE purchase_requisitions SET {set_clause} WHERE id = %s"
                values = list(portal_data.values()) + [portal_id]
                
                # Execute update
                cursor.execute(query, values)
                conn.commit()
                
                frappe.logger().info(f"Updated portal record ID: {portal_id}")
                return portal_id
                
    except Exception as e:
        frappe.logger().error(f"Error updating portal record: {str(e)}")
        raise

def update_invoice_sync_status(invoice_doc, portal_id, operation):
    """
    Update ERPNext invoice with portal sync information
    
    Args:
        invoice_doc: ERPNext Purchase Invoice document
        portal_id: Portal record ID
        operation: 'created' or 'updated'
    """
    try:
        # Create custom fields if they don't exist
        create_sync_custom_fields()
        
        # Update invoice document
        invoice_doc.custom_portal_sync_id = portal_id
        invoice_doc.custom_portal_sync_status = 'Synced'
        invoice_doc.custom_portal_sync_date = datetime.now()
        invoice_doc.custom_portal_sync_operation = operation
        
        # Save without validations to avoid triggering workflows
        invoice_doc.flags.ignore_validate = True
        invoice_doc.flags.ignore_permissions = True
        invoice_doc.save()
        
        frappe.db.commit()
        frappe.logger().info(f"Updated sync status for invoice {invoice_doc.name}")
        
    except Exception as e:
        frappe.logger().error(f"Error updating sync status: {str(e)}")
        # Don't raise error as portal sync was successful

def create_sync_custom_fields():
    """
    Create custom fields for tracking portal sync status
    """
    try:
        custom_fields = [
            {
                'doctype': 'Purchase Invoice',
                'fieldname': 'custom_portal_sync_id',
                'label': 'Portal Sync ID',
                'fieldtype': 'Int',
                'read_only': 1
            },
            {
                'doctype': 'Purchase Invoice', 
                'fieldname': 'custom_portal_sync_status',
                'label': 'Portal Sync Status',
                'fieldtype': 'Select',
                'options': '\nPending\nSynced\nError',
                'read_only': 1
            },
            {
                'doctype': 'Purchase Invoice',
                'fieldname': 'custom_portal_sync_date', 
                'label': 'Portal Sync Date',
                'fieldtype': 'Datetime',
                'read_only': 1
            },
            {
                'doctype': 'Purchase Invoice',
                'fieldname': 'custom_portal_sync_operation',
                'label': 'Portal Sync Operation', 
                'fieldtype': 'Data',
                'read_only': 1
            }
        ]
        
        for field_config in custom_fields:
            if not frappe.db.exists('Custom Field', 
                                  {'dt': field_config['doctype'], 
                                   'fieldname': field_config['fieldname']}):
                # Field doesn't exist, create it
                custom_field = frappe.new_doc('Custom Field')
                custom_field.update(field_config)
                custom_field.dt = field_config['doctype']
                custom_field.save()
                
    except Exception as e:
        frappe.logger().error(f"Error creating custom fields: {str(e)}")

# =============================================================================
# TRANSFORMATION HELPER FUNCTIONS
# Based on FINAL_VERIFIED_Field_Mapping_Frappe_to_PHP.csv
# =============================================================================

def map_supplier_to_entity(supplier_name):
    """
    Map Frappe supplier to PHP entity ID
    Per documentation: "Map supplier name → PHP entitys.id"
    """
    if not supplier_name:
        return 'UNKNOWN'
    
    # For now, return the supplier name directly
    # In production, this should lookup the actual entity ID from PHP entitys table
    return str(supplier_name)[:255]

def map_sub_branch_to_subentity(sub_branch):
    """
    Map custom_sub_branch to PHP subentity ID
    Per documentation: "Lookup subentity.id from sub_branch name"
    """
    if not sub_branch:
        return None
    
    # For now, return the sub_branch name directly
    # In production, this should lookup the actual subentity ID
    return str(sub_branch)[:255]

def get_supplier_address(supplier_address_name):
    """
    Get supplier address from ERPNext Address doctype
    
    Args:
        supplier_address_name: Name/ID of the address document
        
    Returns:
        str: Complete address string or default if not found
    """
    if not supplier_address_name:
        return None
    
    try:
        import frappe
        # Get the Address document
        address_doc = frappe.get_doc("Address", supplier_address_name)
        
        # Build complete address string
        address_parts = []
        
        # Add address lines
        if address_doc.get('address_line1'):
            address_parts.append(address_doc.address_line1)
        if address_doc.get('address_line2'):
            address_parts.append(address_doc.address_line2)
        
        # Add city, state, country
        if address_doc.get('city'):
            address_parts.append(address_doc.city)
        if address_doc.get('state'):
            address_parts.append(address_doc.state)
        if address_doc.get('country'):
            address_parts.append(address_doc.country)
        
        # Add pincode
        if address_doc.get('pincode'):
            address_parts.append(f"PIN: {address_doc.pincode}")
        
        # Join all parts with commas
        full_address = ', '.join(filter(None, address_parts))
        
        # Truncate to reasonable length for database field
        return full_address[:500] if full_address else None
        
    except Exception as e:
        frappe.logger().error(f"Error fetching supplier address {supplier_address_name}: {e}")
        return f"Address ID: {supplier_address_name}"

def get_address_from_sub_branch(sub_branch):
    """
    Get address from sub_branch table lookup
    Per documentation: "Multi-step lookup required"
    """
    if not sub_branch:
        return 'Address not available'
    
    # For now, return a default address
    # In production, this should do: custom_sub_branch → subentity.id → branch_address table → address field
    return f'Address for {sub_branch}'

def format_date_for_portal(date_value):
    """
    Convert Frappe date/datetime to MySQL datetime format
    Per documentation: "Convert to MySQL datetime format"
    """
    if not date_value:
        return None
    
    if isinstance(date_value, str):
        try:
            # Try parsing as datetime first
            date_value = datetime.strptime(date_value, '%Y-%m-%d %H:%M:%S')
        except:
            try:
                # Try parsing as date
                date_value = datetime.strptime(date_value, '%Y-%m-%d')
            except:
                return None
    
    if isinstance(date_value, datetime):
        return date_value.strftime('%Y-%m-%d %H:%M:%S')
    elif hasattr(date_value, 'strftime'):  # date object
        return date_value.strftime('%Y-%m-%d 00:00:00')
    
    return None

def calculate_validity_date(due_date):
    """
    Calculate validity date from due_date
    Per documentation: "Same as delivery_date or posting_date + 30 days"
    """
    if not due_date:
        return None
    
    # Use due_date if available, otherwise current date + 30 days
    if isinstance(due_date, str):
        try:
            due_date = datetime.strptime(due_date, '%Y-%m-%d')
        except:
            return None
    
    if hasattr(due_date, 'strftime'):
        return due_date.strftime('%Y-%m-%d 00:00:00')
    
    return None

def combine_posting_datetime(posting_date, posting_time):
    """
    Combine posting_date and posting_time fields
    Per documentation: "Python: datetime.combine(posting_date, posting_time)"
    """
    if not posting_date:
        return None
    
    try:
        if isinstance(posting_date, str):
            posting_date = datetime.strptime(posting_date, '%Y-%m-%d').date()
        
        if posting_time:
            if isinstance(posting_time, str):
                posting_time = datetime.strptime(posting_time, '%H:%M:%S').time()
            elif isinstance(posting_time, time):
                pass
            else:
                posting_time = time(0, 0, 0)  # Default to midnight
        else:
            posting_time = time(0, 0, 0)  # Default to midnight
        
        combined = datetime.combine(posting_date, posting_time)
        return combined.strftime('%Y-%m-%d %H:%M:%S')
        
    except Exception as e:
        frappe.logger().error(f"Error combining datetime: {str(e)}")
        return None

def calculate_freight_rate(freight_amount, total_weight):
    """
    Calculate freight rate per kg
    Per documentation: "freight_amount / total_net_weight"
    """
    try:
        if not freight_amount or not total_weight or float(total_weight) == 0:
            return '0.00'
        
        rate = float(freight_amount) / float(total_weight)
        return f"{rate:.2f}"
        
    except (ValueError, ZeroDivisionError):
        return '0.00'

def map_docstatus_to_acknowledgement(docstatus):
    """
    Map Frappe docstatus to PHP acknowledgement
    Per documentation: "Direct map: 0→0, 1→1, 2→2"
    """
    status_map = {0: 0, 1: 1, 2: 2}
    return status_map.get(docstatus, 0)

def map_docstatus_to_order_status(docstatus):
    """
    Map Frappe docstatus to PHP order_status
    Per documentation: "0→1, 1→2, 2→3"
    """
    status_map = {0: 1, 1: 2, 2: 3}
    return status_map.get(docstatus, 1)

def map_outstanding_to_finance_status(outstanding_amount):
    """
    Map outstanding amount to finance status
    Per documentation: 'If outstanding=0 then "Paid" else "Unpaid"'
    """
    try:
        return 0 if float(outstanding_amount or 0) == 0 else 1
    except (ValueError, TypeError):
        return 1

def extract_invoice_series(naming_series):
    """
    Extract invoice series number from naming_series
    Per documentation: "Extract from AGO2O/25-26/#### format"
    """
    if not naming_series:
        return 1
    
    try:
        # Extract the last numeric part from formats like "AGO2O/25-26/0001"
        parts = naming_series.split('/')
        if len(parts) >= 3:
            numeric_part = parts[-1]
            return int(numeric_part.lstrip('0')) if numeric_part.isdigit() else 1
        return 1
    except (ValueError, IndexError):
        return 1

def map_user_to_portal_id(frappe_user):
    """
    Map Frappe user to PHP user ID
    Per documentation: "Map Frappe user → PHP users.id"
    """
    if not frappe_user:
        return 1  # Default user ID
    
    # For now, return default user ID
    # In production, this should lookup the actual user ID from PHP users table
    return 1

def extract_amendment_number(amended_from):
    """
    Extract amendment number from amended_from field
    Per documentation: 'If amended_from exists, extract number or use "1", else "0"'
    """
    if not amended_from:
        return '0'
    
    # If there's an amended_from, it means this is an amendment
    return '1'

def calculate_gst_percentage(invoice_doc):
    """
    Calculate GST percentage from tax totals
    Per documentation: "((sgst+cgst+igst) / net_total) * 100"
    """
    try:
        sgst = float(invoice_doc.get('custom_total_sgst', 0) or 0)
        cgst = float(invoice_doc.get('custom_total_cgst', 0) or 0) 
        igst = float(invoice_doc.get('custom_total_igst', 0) or 0)
        net_total = float(invoice_doc.get('net_total', 0) or 0)
        
        if net_total > 0:
            gst_percentage = ((sgst + cgst + igst) / net_total) * 100
            return str(int(round(gst_percentage, 0)))
        
        return '5'  # Default GST percentage
        
    except (ValueError, ZeroDivisionError):
        return '5'

def map_currency_to_id(currency_code):
    """
    Map currency code to PHP currency ID
    Per documentation: 'Lookup: "INR" → currencies.id'
    """
    currency_map = {
        'INR': 1,
        'USD': 2, 
        'EUR': 3,
        'GBP': 4
    }
    return currency_map.get(currency_code, 1)  # Default to INR

def clean_html_content(html_content):
    """
    Strip HTML tags from content
    Per documentation: "Strip HTML, preserve line breaks"
    """
    if not html_content:
        return ''
    
    # Simple HTML tag removal
    import re
    clean_text = re.sub(r'<[^>]+>', '', str(html_content))
    return clean_text.strip()

# =============================================================================
# LEGACY SYNC FUNCTIONS (Keep for backward compatibility)
# =============================================================================

def sync_invoice_to_procureuat(invoice_name):
    """
    Legacy wrapper function - redirects to new push function
    """
    return push_invoice_to_procureuat(invoice_name)

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
                result = push_invoice_to_procureuat(invoice_name)
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