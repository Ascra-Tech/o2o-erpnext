import frappe
from frappe.utils.pdf import get_pdf
from PyPDF2 import PdfMerger
import io
import base64
import zipfile
import tempfile
import os

@frappe.whitelist()
def merge_invoice_and_po_pdfs(invoice_name):
    """Merge Purchase Invoice and associated POs into a single PDF"""
    # Get the Purchase Invoice document
    doc = frappe.get_doc("Purchase Invoice", invoice_name)
    if not doc.items:
        frappe.throw("No items found in this Invoice")
    
    # Get unique POs
    purchase_orders = list(set([item.purchase_order for item in doc.items if item.purchase_order]))
    
    if not purchase_orders:
        frappe.msgprint(f"No Purchase Orders found for Invoice {invoice_name}. Only Invoice PDF will be generated.", alert=True)
    
    # Initialize PDF merger
    merger = PdfMerger()
    
    try:
        # Get print format for PI and convert to PDF
        pi_html = frappe.get_print(
            doctype="Purchase Invoice",
            name=invoice_name,
            print_format="With Header Purchase Invoice"
        )
        
        pi_pdf = get_pdf(pi_html)
        pi_stream = io.BytesIO(pi_pdf)
        merger.append(pi_stream)
        
        # Add all PO PDFs
        for po_name in purchase_orders:
            if not po_name:
                continue
            
            try:
                # Get print format for PO and convert to PDF
                po_html = frappe.get_print(
                    doctype="Purchase Order",
                    name=po_name,
                    print_format="Purchase Order"
                )
                
                # Try to generate PDF with error handling for broken images
                try:
                    po_pdf = get_pdf(po_html)
                    po_stream = io.BytesIO(po_pdf)
                    merger.append(po_stream)
                except Exception as pdf_error:
                    # If PDF generation fails due to images, try without images
                    try:
                        po_pdf = get_pdf(po_html, {"load-error-handling": "ignore", "load-media-error-handling": "ignore"})
                        po_stream = io.BytesIO(po_pdf)
                        merger.append(po_stream)
                    except Exception as fallback_error:
                        frappe.log_error(f"PO PDF Error: {po_name}", str(fallback_error)[:500])
                        continue
                        
            except Exception as po_error:
                frappe.log_error(f"PO Error: {po_name}", str(po_error)[:500])
                continue
        
        # Create output buffer
        output = io.BytesIO()
        merger.write(output)
        output.seek(0)
        
        # Return merged PDF
        filename = f"{invoice_name}_with_POs.pdf"
        frappe.response["filename"] = filename
        frappe.response["filecontent"] = output.getvalue()
        frappe.response["type"] = "download"
        frappe.response["content_type"] = "application/pdf"
        
        # Show success message
        frappe.msgprint(f"PDF successfully generated: {filename}", alert=True)
        
    except Exception as e:
        frappe.log_error(f"PDF Generation Error: {str(e)}")
        frappe.throw(f"Failed to generate PDF: {str(e)}")

@frappe.whitelist()
def merge_multiple_invoices_and_pos_zip(invoice_names):
    """Merge multiple Purchase Invoices with their POs into a ZIP file"""
    if isinstance(invoice_names, str):
        import json
        invoice_names = json.loads(invoice_names)
    
    if not invoice_names or len(invoice_names) == 0:
        frappe.throw("No Purchase Invoices selected")
    
    # Create temporary directory for PDF files
    temp_dir = tempfile.mkdtemp()
    pdf_files = []
    failed_invoices = []
    
    try:
        # Process each invoice
        for invoice_name in invoice_names:
            try:
                # Get the Purchase Invoice document
                doc = frappe.get_doc("Purchase Invoice", invoice_name)
                if not doc.items:
                    failed_invoices.append(invoice_name)
                    continue
                
                # Get unique POs for this invoice
                purchase_orders = list(set([item.purchase_order for item in doc.items if item.purchase_order]))
                
                # Initialize PDF merger for this invoice
                merger = PdfMerger()
                
                # Get print format for PI and convert to PDF
                pi_html = frappe.get_print(
                    doctype="Purchase Invoice",
                    name=invoice_name,
                    print_format="With Header Purchase Invoice"
                )
                
                # Try to generate PI PDF with error handling
                try:
                    pi_pdf = get_pdf(pi_html)
                    pi_stream = io.BytesIO(pi_pdf)
                    merger.append(pi_stream)
                except Exception as pi_error:
                    # Try with image loading disabled
                    try:
                        pi_pdf = get_pdf(pi_html, {"load-error-handling": "ignore", "load-media-error-handling": "ignore"})
                        pi_stream = io.BytesIO(pi_pdf)
                        merger.append(pi_stream)
                    except Exception as pi_fallback_error:
                        failed_invoices.append(invoice_name)
                        continue
                
                # Add all PO PDFs for this invoice
                for po_name in purchase_orders:
                    if not po_name:
                        continue
                    
                    try:
                        # Get print format for PO and convert to PDF
                        po_html = frappe.get_print(
                            doctype="Purchase Order",
                            name=po_name,
                            print_format="Purchase Order"
                        )
                        
                        try:
                            po_pdf = get_pdf(po_html)
                            po_stream = io.BytesIO(po_pdf)
                            merger.append(po_stream)
                        except Exception as po_pdf_error:
                            # Try with image loading disabled
                            try:
                                po_pdf = get_pdf(po_html, {"load-error-handling": "ignore", "load-media-error-handling": "ignore"})
                                po_stream = io.BytesIO(po_pdf)
                                merger.append(po_stream)
                            except Exception as po_fallback_error:
                                continue
                                
                    except Exception as po_error:
                        continue
                
                # Create merged PDF for this invoice
                output = io.BytesIO()
                merger.write(output)
                output.seek(0)
                
                # Save to temporary file - sanitize filename
                safe_invoice_name = invoice_name.replace("/", "-").replace("\\", "-")
                pdf_filename = f"{safe_invoice_name}_with_POs.pdf"
                pdf_path = os.path.join(temp_dir, pdf_filename)
                
                with open(pdf_path, 'wb') as f:
                    f.write(output.getvalue())
                
                pdf_files.append((pdf_path, pdf_filename))
                
                # Close merger to free memory
                merger.close()
                
            except Exception as invoice_error:
                failed_invoices.append(invoice_name)
                frappe.log_error(f"ZIP PI Error", str(invoice_error)[:500])
                continue
        
        if not pdf_files:
            frappe.throw("No valid PDFs could be generated")
        
        # Create ZIP file
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for pdf_path, pdf_filename in pdf_files:
                zip_file.write(pdf_path, pdf_filename)
        
        zip_buffer.seek(0)
        
        # Clean up temporary files
        for pdf_path, _ in pdf_files:
            try:
                os.remove(pdf_path)
            except:
                pass
        
        try:
            os.rmdir(temp_dir)
        except:
            pass
        
        # Return ZIP file
        zip_filename = f"Purchase_Invoices_with_POs_{len(pdf_files)}_files.zip"
        frappe.response["filename"] = zip_filename
        frappe.response["filecontent"] = zip_buffer.getvalue()
        frappe.response["type"] = "download"
        frappe.response["content_type"] = "application/zip"
        
        # Show success message with failed invoices info if any
        if failed_invoices:
            frappe.msgprint(f"ZIP created with {len(pdf_files)} PDFs. {len(failed_invoices)} invoice(s) failed.", alert=True)
        
    except Exception as e:
        # Clean up on error
        for pdf_path, _ in pdf_files:
            try:
                os.remove(pdf_path)
            except:
                pass
        
        try:
            os.rmdir(temp_dir)
        except:
            pass
        
        frappe.log_error("ZIP Error", str(e)[:500])
        frappe.throw(f"Failed to generate ZIP file: {str(e)}")