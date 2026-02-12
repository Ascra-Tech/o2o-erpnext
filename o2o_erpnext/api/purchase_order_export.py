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
            return export_to_excel_with_items(po_names, predefined_fields, temp_dir, timestamp)
        else:
            return export_to_csv_with_items(po_names, predefined_fields, temp_dir, timestamp)
        
    except Exception as e:
        frappe.log_error(f"Error exporting POs: {str(e)}", "PO Export Error")
        return {
            'status': 'error',
            'message': str(e)
        }

def export_to_excel_with_items(po_names, fields_list, temp_dir, timestamp):
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
    
    item_header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#E8F4FD',
        'border': 1,
        'align': 'center',
        'valign': 'vcenter'
    })
    
    # Get field labels for headers
    meta = frappe.get_meta("Purchase Order")
    field_labels = {}
    for field in meta.fields:
        field_labels[field.fieldname] = field.label or field.fieldname.replace('_', ' ').title()
    
    # Define headers including items
    headers = []
    for fieldname in fields_list:
        headers.append(field_labels.get(fieldname, fieldname.replace('_', ' ').title()))
    
    # Add item headers (removed: Item Code, UOM, Product Type)
    item_headers = ['Item Name', 'Qty', 'Rate', 'Amount', 'Category']
    headers.extend(item_headers)
    
    # Write headers
    for col, header in enumerate(headers):
        if col < len(fields_list):
            worksheet.write(0, col, header, header_format)
        else:
            worksheet.write(0, col, header, item_header_format)
        worksheet.set_column(col, col, 15)
    
    # Fetch and write Purchase Order data
    row = 1
    for po_name in po_names:
        try:
            po_doc = frappe.get_doc("Purchase Order", po_name)
            
            # If PO has items, write one row per item
            if po_doc.items:
                for item in po_doc.items:
                    # Write PO fields
                    for col, fieldname in enumerate(fields_list):
                        value = format_field_value(po_doc, fieldname)
                        worksheet.write(row, col, value, cell_format)
                    
                    # Write item fields (removed: item_code, uom, custom_product_type)
                    base_col = len(fields_list)
                    worksheet.write(row, base_col, item.item_name or '', cell_format)
                    worksheet.write(row, base_col + 1, item.qty or 0, cell_format)
                    worksheet.write(row, base_col + 2, item.rate or 0, cell_format)
                    worksheet.write(row, base_col + 3, item.amount or 0, cell_format)
                    worksheet.write(row, base_col + 4, item.item_group or '', cell_format)
                    
                    row += 1
            else:
                # Write PO without items
                for col, fieldname in enumerate(fields_list):
                    value = format_field_value(po_doc, fieldname)
                    worksheet.write(row, col, value, cell_format)
                
                # Empty item columns
                base_col = len(fields_list)
                for i in range(len(item_headers)):
                    worksheet.write(row, base_col + i, '', cell_format)
                
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

def export_to_csv_with_items(po_names, fields_list, temp_dir, timestamp):
    """Export to CSV format with Purchase Order Items as fallback"""
    filename = f"purchase_orders_export_{timestamp}.csv"
    filepath = os.path.join(temp_dir, filename)
    
    # Get field labels for headers
    meta = frappe.get_meta("Purchase Order")
    field_labels = {}
    for field in meta.fields:
        field_labels[field.fieldname] = field.label or field.fieldname.replace('_', ' ').title()
    
    with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        # Write headers including items
        headers = []
        for fieldname in fields_list:
            headers.append(field_labels.get(fieldname, fieldname.replace('_', ' ').title()))
        
        # Add item headers (removed: Item Code, UOM, Product Type)
        item_headers = ['Item Name', 'Qty', 'Rate', 'Amount', 'Category']
        headers.extend(item_headers)
        writer.writerow(headers)
        
        # Fetch and write Purchase Order data
        for po_name in po_names:
            try:
                po_doc = frappe.get_doc("Purchase Order", po_name)
                
                # If PO has items, write one row per item
                if po_doc.items:
                    for item in po_doc.items:
                        row_data = []
                        
                        # Write PO fields
                        for fieldname in fields_list:
                            value = format_field_value(po_doc, fieldname)
                            row_data.append(value)
                        
                        # Write item fields (removed: item_code, uom, custom_product_type)
                        row_data.extend([
                            item.item_name or '',
                            item.qty or 0,
                            item.rate or 0,
                            item.amount or 0,
                            item.item_group or ''
                        ])
                        
                        writer.writerow(row_data)
                else:
                    # Write PO without items
                    row_data = []
                    for fieldname in fields_list:
                        value = format_field_value(po_doc, fieldname)
                        row_data.append(value)
                    
                    # Empty item columns
                    row_data.extend([''] * len(item_headers))
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
