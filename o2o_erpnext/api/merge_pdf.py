import frappe
from frappe.utils.pdf import get_pdf
from PyPDF2 import PdfMerger
import io
import base64

@frappe.whitelist()
def merge_invoice_and_po_pdfs(invoice_name):
    """Merge Purchase Invoice and associated POs into a single PDF"""
    # Get the Purchase Invoice document
    doc = frappe.get_doc("Purchase Invoice", invoice_name)
    if not doc.items:
        frappe.throw("No items found in this Invoice")
    
    # Get unique POs
    purchase_orders = list(set([item.purchase_order for item in doc.items if item.purchase_order]))
    
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
            
            # Get print format for PO and convert to PDF
            po_html = frappe.get_print(
                doctype="Purchase Order",
                name=po_name,
                print_format="Purchase Order"
            )
            po_pdf = get_pdf(po_html)
            po_stream = io.BytesIO(po_pdf)
            merger.append(po_stream)
        
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