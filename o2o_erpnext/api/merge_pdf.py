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
    
    # Debug: Log the POs found
    frappe.log_error(f"Invoice {invoice_name}: Found {len(purchase_orders)} POs: {purchase_orders}", "Debug PO Merge")
    
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
        
        # Add a message about missing images if needed
        if "404 Not Found" in frappe.log_error().get("error", ""):
            frappe.msgprint("Some images may be missing in the generated PDF", alert=True)
        
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
                    frappe.log_error(f"Successfully added PO {po_name} to merger (with images)", "Debug PO Merge")
                except Exception as pdf_error:
                    # If PDF generation fails due to images, try without images
                    frappe.log_error(f"PDF generation failed for PO {po_name} with images: {str(pdf_error)}")
                    
                    # Try generating PDF with image loading disabled
                    try:
                        po_pdf = get_pdf(po_html, {"load-error-handling": "ignore", "load-media-error-handling": "ignore"})
                        po_stream = io.BytesIO(po_pdf)
                        merger.append(po_stream)
                        frappe.msgprint(f"Warning: Images may be missing in PO {po_name}", alert=True)
                        frappe.log_error(f"Successfully added PO {po_name} to merger (without images)", "Debug PO Merge")
                    except Exception as fallback_error:
                        frappe.log_error(f"Failed to generate PDF for PO {po_name} even without images: {str(fallback_error)}")
                        frappe.msgprint(f"Warning: Could not include PO {po_name} in merged PDF due to generation errors", alert=True)
                        continue
                        
            except Exception as po_error:
                frappe.log_error(f"Error processing PO {po_name}: {str(po_error)}")
                frappe.msgprint(f"Warning: Could not process PO {po_name}", alert=True)
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
    
    # Debug: Log the ZIP function call
    frappe.log_error(f"ZIP function called with {len(invoice_names)} invoices: {invoice_names}", "Debug ZIP Function")
    
    # Create temporary directory for PDF files
    temp_dir = tempfile.mkdtemp()
    pdf_files = []
    
    try:
        # Process each invoice
        frappe.log_error(f"Starting to process {len(invoice_names)} invoices", "Debug ZIP Function")
        
        for idx, invoice_name in enumerate(invoice_names):
            frappe.log_error(f"Processing invoice {idx + 1}/{len(invoice_names)}: {invoice_name}", "Debug ZIP Function")
            
            try:
                # Get the Purchase Invoice document
                doc = frappe.get_doc("Purchase Invoice", invoice_name)
                if not doc.items:
                    frappe.log_error(f"No items found in Invoice {invoice_name}, skipping...", "Debug ZIP Function")
                    continue
                
                # Get unique POs for this invoice
                purchase_orders = list(set([item.purchase_order for item in doc.items if item.purchase_order]))
                frappe.log_error(f"Invoice {invoice_name}: Found {len(purchase_orders)} POs: {purchase_orders}", "Debug ZIP Function")
                
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
                    frappe.log_error(f"Successfully added PI {invoice_name} to merger", "Debug ZIP Function")
                except Exception as pi_error:
                    frappe.log_error(f"Failed to generate PI PDF for {invoice_name}: {str(pi_error)}", "Debug ZIP Function")
                    # Try with image loading disabled
                    try:
                        pi_pdf = get_pdf(pi_html, {"load-error-handling": "ignore", "load-media-error-handling": "ignore"})
                        pi_stream = io.BytesIO(pi_pdf)
                        merger.append(pi_stream)
                        frappe.log_error(f"Successfully added PI {invoice_name} to merger (without images)", "Debug ZIP Function")
                    except Exception as pi_fallback_error:
                        frappe.log_error(f"Failed to generate PI PDF for {invoice_name} even without images: {str(pi_fallback_error)}", "Debug ZIP Function")
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
                            frappe.log_error(f"Successfully added PO {po_name} to merger", "Debug ZIP Function")
                        except Exception as po_pdf_error:
                            frappe.log_error(f"Failed to generate PO PDF for {po_name}: {str(po_pdf_error)}", "Debug ZIP Function")
                            # Try with image loading disabled
                            try:
                                po_pdf = get_pdf(po_html, {"load-error-handling": "ignore", "load-media-error-handling": "ignore"})
                                po_stream = io.BytesIO(po_pdf)
                                merger.append(po_stream)
                                frappe.log_error(f"Successfully added PO {po_name} to merger (without images)", "Debug ZIP Function")
                            except Exception as po_fallback_error:
                                frappe.log_error(f"Failed to generate PO PDF for {po_name} even without images: {str(po_fallback_error)}", "Debug ZIP Function")
                                continue
                                
                    except Exception as po_error:
                        frappe.log_error(f"Error processing PO {po_name}: {str(po_error)}", "Debug ZIP Function")
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
                frappe.log_error(f"Successfully created merged PDF for {invoice_name}: {pdf_filename}", "Debug ZIP Function")
                
                # Close merger to free memory
                merger.close()
                
            except Exception as invoice_error:
                frappe.log_error(f"Error processing Invoice {invoice_name}: {str(invoice_error)}", "Debug ZIP Function")
                continue
        
        frappe.log_error(f"Finished processing. Total PDFs created: {len(pdf_files)}", "Debug ZIP Function")
        
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
        
        # Show success message
        frappe.msgprint(f"ZIP file successfully generated with {len(pdf_files)} PDF(s): {zip_filename}", alert=True)
        
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
        
        frappe.log_error(f"ZIP Generation Error: {str(e)}")
        frappe.throw(f"Failed to generate ZIP file: {str(e)}")