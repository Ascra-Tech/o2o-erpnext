import frappe
from frappe import _
import json
import os
import tempfile
from datetime import datetime
import csv
import io

try:
    import xlsxwriter
    HAS_XLSXWRITER = True
except ImportError:
    HAS_XLSXWRITER = False

@frappe.whitelist()
def get_po_fields():
    """
    Get Purchase Order field metadata for export selection
    """
    try:
        # Get Purchase Order doctype meta
        meta = frappe.get_meta("Purchase Order")
        
        mandatory_fields = []
        optional_fields = []
        
        # Define core mandatory fields
        core_mandatory = ['name', 'supplier', 'transaction_date', 'grand_total', 'status']
        
        for field in meta.fields:
            # Skip certain field types that are not useful for export
            skip_fieldtypes = ['Section Break', 'Column Break', 'HTML', 'Button', 'Heading', 'Tab Break']
            if field.fieldtype in skip_fieldtypes:
                continue
            
            # Skip system fields
            if field.fieldname.startswith('_'):
                continue
                
            field_info = {
                'fieldname': field.fieldname,
                'label': field.label or field.fieldname.replace('_', ' ').title(),
                'fieldtype': field.fieldtype,
                'mandatory': field.reqd or field.fieldname in core_mandatory,
                'is_custom': field.fieldname.startswith('custom_')
            }
            
            if field_info['mandatory'] or field.fieldname in core_mandatory:
                mandatory_fields.append(field_info)
            else:
                optional_fields.append(field_info)
        
        # Sort fields alphabetically
        mandatory_fields.sort(key=lambda x: x['label'])
        optional_fields.sort(key=lambda x: x['label'])
        
        return {
            'mandatory_fields': mandatory_fields,
            'optional_fields': optional_fields
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting PO fields: {str(e)}", "PO Export Error")
        frappe.throw(_("Error fetching field information"))

@frappe.whitelist()
def export_pos_to_excel(po_ids):
    """
    Export selected Purchase Orders to Excel with predefined fields
    """
    try:
        # Parse JSON inputs
        po_list = json.loads(po_ids) if isinstance(po_ids, str) else po_ids
        
        if not po_list:
            frappe.throw(_("No Purchase Orders selected"))
        
        # Extract PO names from the list (they come as objects with 'name' key)
        po_names = [po.get('name') if isinstance(po, dict) else po for po in po_list]
        
        # Create temporary file
        temp_dir = tempfile.gettempdir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Use predefined fields as requested by user (using workflow_state for correct status)
        predefined_fields = [
            'name', 'supplier', 'custom_branch', 'custom_sub_branch',
            'custom__approver_name_and_email', 'transaction_date', 'grand_total',
            'workflow_state', 'custom__approved_at', 'custom_created_user', 'custom_purchase_receipt'
        ]
        
        if HAS_XLSXWRITER:
            return export_to_excel_with_items(po_names, temp_dir, timestamp)
        else:
            return export_to_csv_with_items(po_names, temp_dir, timestamp)
        
    except Exception as e:
        frappe.log_error(f"Error exporting POs: {str(e)}", "PO Export Error")
        return {
            'status': 'error',
            'message': str(e)
        }

def export_to_excel_with_items(po_names, temp_dir, timestamp):
    """Export to Excel format with Purchase Order Items using xlsxwriter"""
    filename = f"purchase_orders_export_{timestamp}.xlsx"
    filepath = os.path.join(temp_dir, filename)
    
    # Create Excel workbook
    workbook = xlsxwriter.Workbook(filepath)
    worksheet = workbook.add_worksheet('Purchase Orders')
    
    # Define formats
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#D7E4BC',
        'border': 1,
        'align': 'center',
        'valign': 'vcenter'
    })
    
    cell_format = workbook.add_format({
        'border': 1,
        'align': 'left',
        'valign': 'top',
        'text_wrap': True
    })
    
    # Define the updated headers as per user requirement
    headers = [
        'Entity', 'Order Number', 'Branch Name', 'Sub Branch', 'Approver Name', 'Product Category',
        'Product name', 'Quantity', 'Gross Amount', 'CGST', 'SGST', 'IGST', 'Total',
        'Order Code', 'Dispatch Status', 'Order status', 'Purchase Receipt', 'Vendor status', 'Vendor Name',
        'Created At', 'Approved At'
    ]
    
    # Write headers
    for col, header in enumerate(headers):
        worksheet.write(0, col, header, header_format)
        worksheet.set_column(col, col, 15)
    
    # Fetch and write Purchase Order data
    row = 1
    
    for po_name in po_names:
        try:
            po_doc = frappe.get_doc("Purchase Order", po_name)
            
            # Get supplier name for Entity
            supplier_name = po_doc.supplier or ''
            
            # If PO has items, write one row per item
            if po_doc.items:
                for item in po_doc.items:
                    # Read exact tax amounts from Purchase Order - no calculations
                    cgst_amount = 0
                    sgst_amount = 0
                    igst_amount = 0
                    
                    # Get exact tax amounts from Purchase Order taxes
                    if hasattr(po_doc, 'taxes') and po_doc.taxes:
                        for tax in po_doc.taxes:
                            if tax.tax_amount:
                                if 'cgst' in (tax.account_head or '').lower():
                                    cgst_amount = tax.tax_amount or 0
                                elif 'sgst' in (tax.account_head or '').lower():
                                    sgst_amount = tax.tax_amount or 0
                                elif 'igst' in (tax.account_head or '').lower():
                                    igst_amount = tax.tax_amount or 0
                    
                    # Use exact total from Purchase Order
                    total_amount = po_doc.grand_total or 0
                    
                    # Format dates - fix the date formatting
                    try:
                        created_at = frappe.utils.formatdate(po_doc.creation, "dd/mm/yy") if po_doc.creation else ''
                        if po_doc.creation:
                            created_at += " " + frappe.utils.format_time(po_doc.creation)
                    except:
                        created_at = str(po_doc.creation) if po_doc.creation else ''
                    
                    try:
                        approved_at = ''
                        if hasattr(po_doc, 'custom__approved_at') and po_doc.custom__approved_at:
                            approved_at = frappe.utils.formatdate(po_doc.custom__approved_at, "dd/mm/yy")
                            approved_at += " " + frappe.utils.format_time(po_doc.custom__approved_at)
                    except:
                        approved_at = ''
                    
                    vendor_approved_at = ''  # Add logic if you have vendor approval date field
                    
                    # Write row data
                    row_data = [
                        supplier_name,  # Entity
                        po_doc.name,  # Order Number
                        getattr(po_doc, 'custom_branch', '') or '',  # Branch Name
                        getattr(po_doc, 'custom_sub_branch', '') or '',  # Sub Branch
                        getattr(po_doc, 'custom__approver_name_and_email', '') or '',  # Approver Name
                        item.item_group or '',  # Product Category
                        item.item_name or '',  # Product name
                        item.qty or 0,  # Quantity
                        round(item.amount or 0, 2),  # Gross Amount
                        round(cgst_amount, 2),  # CGST
                        round(sgst_amount, 2),  # SGST
                        round(igst_amount, 2),  # IGST
                        round(total_amount, 2),  # Total
                        getattr(po_doc, 'custom_order_code', '') or '',  # Order Code
                        '',  # Dispatch Status
                        po_doc.workflow_state or po_doc.status or '',  # Order status
                        getattr(po_doc, 'custom_purchase_receipt', '') or '-',  # Purchase Receipt
                        '',  # Vendor status
                        getattr(po_doc, 'custom_vendor', '') or '',  # Vendor Name
                        created_at,  # Created At
                        approved_at,  # Approved At
                    ]
                    
                    for col, value in enumerate(row_data):
                        worksheet.write(row, col, value, cell_format)
                    
                    row += 1
            else:
                # Write PO without items
                try:
                    created_at = frappe.utils.formatdate(po_doc.creation, "dd/mm/yy") if po_doc.creation else ''
                    if po_doc.creation:
                        created_at += " " + frappe.utils.format_time(po_doc.creation)
                except:
                    created_at = str(po_doc.creation) if po_doc.creation else ''
                
                try:
                    approved_at = ''
                    if hasattr(po_doc, 'custom__approved_at') and po_doc.custom__approved_at:
                        approved_at = frappe.utils.formatdate(po_doc.custom__approved_at, "dd/mm/yy")
                        approved_at += " " + frappe.utils.format_time(po_doc.custom__approved_at)
                except:
                    approved_at = ''
                
                row_data = [
                    supplier_name,  # Entity
                    po_doc.name,  # Order Number
                    getattr(po_doc, 'custom_branch', '') or '',  # Branch Name
                    getattr(po_doc, 'custom_sub_branch', '') or '',  # Sub Branch
                    getattr(po_doc, 'custom__approver_name_and_email', '') or '',  # Approver Name
                    '',  # Product Category
                    '',  # Product name
                    0,  # Quantity
                    0,  # Gross Amount
                    0,  # CGST
                    0,  # SGST
                    0,  # IGST
                    0,  # Total
                    getattr(po_doc, 'custom_order_code', '') or '',  # Order Code
                    '',  # Dispatch Status
                    po_doc.workflow_state or po_doc.status or '',  # Order status
                    getattr(po_doc, 'custom_purchase_receipt', '') or '-',  # Purchase Receipt
                    '',  # Vendor status
                    getattr(po_doc, 'custom_vendor', '') or '',  # Vendor Name
                    created_at,  # Created At
                    approved_at,  # Approved At
                ]
                
                for col, value in enumerate(row_data):
                    worksheet.write(row, col, value, cell_format)
                
                row += 1
            
        except Exception as e:
            frappe.log_error(f"Error processing PO {po_name}: {str(e)}", "PO Export Error")
            continue
    
    workbook.close()
    
    return {
        'status': 'success',
        'filename': filename,
        'message': _('Purchase Orders exported successfully')
    }

def export_to_csv_with_items(po_names, temp_dir, timestamp):
    """Export to CSV format with Purchase Order Items as fallback"""
    filename = f"purchase_orders_export_{timestamp}.csv"
    filepath = os.path.join(temp_dir, filename)
    
    with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        # Define the updated headers as per user requirement
        headers = [
            'Entity', 'Order Number', 'Branch Name', 'Sub Branch', 'Approver Name', 'Product Category',
            'Product name', 'Quantity', 'Gross Amount', 'CGST', 'SGST', 'IGST', 'Total',
            'Order Code', 'Dispatch Status', 'Order status', 'Purchase Receipt', 'Vendor status', 'Vendor Name',
            'Created At', 'Approved At'
        ]
        writer.writerow(headers)
        
        # Fetch and write Purchase Order data
        for po_name in po_names:
            try:
                po_doc = frappe.get_doc("Purchase Order", po_name)
                
                # Get supplier name for Entity
                supplier_name = po_doc.supplier or ''
                
                # If PO has items, write one row per item
                if po_doc.items:
                    for item in po_doc.items:
                        # Read exact tax amounts from Purchase Order - no calculations
                        cgst_amount = 0
                        sgst_amount = 0
                        igst_amount = 0
                        
                        # Get exact tax amounts from Purchase Order taxes
                        if hasattr(po_doc, 'taxes') and po_doc.taxes:
                            for tax in po_doc.taxes:
                                if tax.tax_amount:
                                    if 'cgst' in (tax.account_head or '').lower():
                                        cgst_amount = tax.tax_amount or 0
                                    elif 'sgst' in (tax.account_head or '').lower():
                                        sgst_amount = tax.tax_amount or 0
                                    elif 'igst' in (tax.account_head or '').lower():
                                        igst_amount = tax.tax_amount or 0
                        
                        # Use exact total from Purchase Order
                        total_amount = po_doc.grand_total or 0
                        
                        # Format dates - fix the date formatting
                        try:
                            created_at = frappe.utils.formatdate(po_doc.creation, "dd/mm/yy") if po_doc.creation else ''
                            if po_doc.creation:
                                created_at += " " + frappe.utils.format_time(po_doc.creation)
                        except:
                            created_at = str(po_doc.creation) if po_doc.creation else ''
                        
                        try:
                            approved_at = ''
                            if hasattr(po_doc, 'custom__approved_at') and po_doc.custom__approved_at:
                                approved_at = frappe.utils.formatdate(po_doc.custom__approved_at, "dd/mm/yy")
                                approved_at += " " + frappe.utils.format_time(po_doc.custom__approved_at)
                        except:
                            approved_at = ''
                        
                        vendor_approved_at = ''  # Add logic if you have vendor approval date field
                        
                        # Write row data
                        row_data = [
                            supplier_name,  # Entity
                            po_doc.name,  # Order Number
                            getattr(po_doc, 'custom_branch', '') or '',  # Branch Name
                            getattr(po_doc, 'custom_sub_branch', '') or '',  # Sub Branch
                            getattr(po_doc, 'custom__approver_name_and_email', '') or '',  # Approver Name
                            item.item_group or '',  # Product Category
                            item.item_name or '',  # Product name
                            item.qty or 0,  # Quantity
                            round(item.amount or 0, 2),  # Gross Amount
                            round(cgst_amount, 2),  # CGST
                            round(sgst_amount, 2),  # SGST
                            round(igst_amount, 2),  # IGST
                            round(total_amount, 2),  # Total
                            getattr(po_doc, 'custom_order_code', '') or '',  # Order Code
                            '',  # Dispatch Status
                            po_doc.workflow_state or po_doc.status or '',  # Order status
                            getattr(po_doc, 'custom_purchase_receipt', '') or '-',  # Purchase Receipt
                            '',  # Vendor status
                            getattr(po_doc, 'custom_vendor', '') or '',  # Vendor Name
                            created_at,  # Created At
                            approved_at,  # Approved At
                        ]
                        
                        writer.writerow(row_data)
                else:
                    # Write PO without items
                    try:
                        created_at = frappe.utils.formatdate(po_doc.creation, "dd/mm/yy") if po_doc.creation else ''
                        if po_doc.creation:
                            created_at += " " + frappe.utils.format_time(po_doc.creation)
                    except:
                        created_at = str(po_doc.creation) if po_doc.creation else ''
                    
                    try:
                        approved_at = ''
                        if hasattr(po_doc, 'custom__approved_at') and po_doc.custom__approved_at:
                            approved_at = frappe.utils.formatdate(po_doc.custom__approved_at, "dd/mm/yy")
                            approved_at += " " + frappe.utils.format_time(po_doc.custom__approved_at)
                    except:
                        approved_at = ''
                    
                    row_data = [
                        supplier_name,  # Entity
                        po_doc.name,  # Order Number
                        getattr(po_doc, 'custom_branch', '') or '',  # Branch Name
                        getattr(po_doc, 'custom_sub_branch', '') or '',  # Sub Branch
                        getattr(po_doc, 'custom__approver_name_and_email', '') or '',  # Approver Name
                        '',  # Product Category
                        '',  # Product name
                        0,  # Quantity
                        0,  # Gross Amount
                        0,  # CGST
                        0,  # SGST
                        0,  # IGST
                        0,  # Total
                        getattr(po_doc, 'custom_order_code', '') or '',  # Order Code
                        '',  # Dispatch Status
                        po_doc.workflow_state or po_doc.status or '',  # Order status
                        getattr(po_doc, 'custom_purchase_receipt', '') or '-',  # Purchase Receipt
                        '',  # Vendor status
                        getattr(po_doc, 'custom_vendor', '') or '',  # Vendor Name
                        created_at,  # Created At
                        approved_at,  # Approved At
                    ]
                    
                    writer.writerow(row_data)
                
            except Exception as e:
                frappe.log_error(f"Error processing PO {po_name}: {str(e)}", "PO Export Error")
                continue
    
    return {
        'status': 'success',
        'filename': filename,
        'message': _('Purchase Orders exported successfully')
    }

def format_field_value(po_doc, fieldname):
    """Format field value for export"""
    value = getattr(po_doc, fieldname, '')
    
    if value is None:
        return ''
    elif isinstance(value, (list, dict)):
        return str(value)
    elif hasattr(value, 'strftime'):  # datetime objects
        return value.strftime("%Y-%m-%d %H:%M:%S")
    else:
        return str(value)

@frappe.whitelist()
def download_exported_file(filename):
    """
    Download the exported Excel file
    """
    try:
        temp_dir = tempfile.gettempdir()
        filepath = os.path.join(temp_dir, filename)
        
        if not os.path.exists(filepath):
            frappe.throw(_("File not found or expired"))
        
        # Read file content
        with open(filepath, 'rb') as f:
            file_content = f.read()
        
        # Clean up temporary file
        try:
            os.remove(filepath)
        except:
            pass
        
        # Set response headers for download
        frappe.local.response.filename = filename
        frappe.local.response.filecontent = file_content
        frappe.local.response.type = "download"
        
    except Exception as e:
        frappe.log_error(f"Error downloading file: {str(e)}", "PO Export Download Error")
        frappe.throw(_("Error downloading file"))
