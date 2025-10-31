import frappe
import json
from datetime import datetime
from frappe import _
from o2o_erpnext.config.external_db_updated import get_external_db_connection

class RemoteInvoiceCreator:
    """Handles creation of invoices in ProcureUAT database"""
    
    def get_next_invoice_code(self, prefix='AGO2O', financial_year='25-26'):
        """
        Generate next invoice code atomically using existing ProcureUAT structure
        
        Args:
            prefix (str): Invoice prefix (default: 'AGO2O')
            financial_year (str): Financial year (default: '25-26')
        
        Returns:
            str: Next invoice code (e.g., 'AGO2O/25-26/0046')
        """
        try:
            with get_external_db_connection() as conn:
                # IMPORTANT: Set autocommit=True to ensure counter changes are immediately committed
                conn.autocommit(True)
                
                with conn.cursor() as cursor:
                    # Check if counter table exists, create if not
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS invoice_counter (
                            id INT PRIMARY KEY AUTO_INCREMENT,
                            prefix VARCHAR(20) NOT NULL DEFAULT 'AGO2O',
                            financial_year VARCHAR(10) NOT NULL,
                            last_number INT NOT NULL DEFAULT 0,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                            UNIQUE KEY unique_prefix_year (prefix, financial_year)
                        )
                    """)
                    
                    # Initialize counter if not exists
                    cursor.execute("""
                        INSERT IGNORE INTO invoice_counter (prefix, financial_year, last_number)
                        SELECT %s, %s, COALESCE(MAX(CAST(SUBSTRING_INDEX(invoice_number, '/', -1) AS UNSIGNED)), 0)
                        FROM purchase_requisitions 
                        WHERE invoice_number LIKE %s
                    """, (prefix, financial_year, f"{prefix}/{financial_year}/%"))
                    
                    # Atomic increment using MySQL session variable  
                    print(f"🔥 DEBUG: About to increment counter for {prefix}/{financial_year}")
                    cursor.execute("""
                        UPDATE invoice_counter 
                        SET last_number = (@cur_value := last_number + 1) 
                        WHERE prefix = %s AND financial_year = %s
                    """, (prefix, financial_year))
                    print(f"🔥 DEBUG: Counter increment executed, affected rows: {cursor.rowcount}")
                    
                    if cursor.rowcount == 0:
                        # Initialize if somehow missed
                        cursor.execute("""
                            INSERT INTO invoice_counter (prefix, financial_year, last_number)
                            VALUES (%s, %s, 1)
                        """, (prefix, financial_year))
                        next_number = 1
                    else:
                        # Get the incremented value from session variable
                        cursor.execute("SELECT @cur_value as invoice_num")
                        result = cursor.fetchone()
                        
                        if not result or not result['invoice_num']:
                            raise Exception("Failed to generate invoice number")
                        
                        next_number = int(result['invoice_num'])
                    
                    invoice_code = f"{prefix}/{financial_year}/{next_number:04d}"
                    
                    frappe.logger().info(f"Generated invoice code: {invoice_code}")
                    print(f"🔥 DEBUG: Generated final invoice code: {invoice_code}")
                    print(f"🔥 DEBUG: Counter should now be permanently at: {next_number}")
                    
                    # Verify the counter was actually updated
                    cursor.execute("SELECT last_number FROM invoice_counter WHERE prefix = %s AND financial_year = %s", (prefix, financial_year))
                    verify_result = cursor.fetchone()
                    print(f"🔥 DEBUG: Verification - counter is now at: {verify_result['last_number'] if verify_result else 'NOT FOUND'}")
                    
                    return invoice_code
                    
        except Exception as e:
            frappe.logger().error(f"Error generating invoice code: {str(e)}")
            raise
    
    def map_erpnext_to_procure_data(self, purchase_invoice):
        """
        Map ERPNext Purchase Invoice data to ProcureUAT format
        
        Args:
            purchase_invoice: ERPNext Purchase Invoice document
        
        Returns:
            dict: Mapped data for ProcureUAT insertion
        """
        # Get financial year from posting date or current
        posting_date = purchase_invoice.posting_date
        current_year = posting_date.year if posting_date else datetime.now().year
        
        # Calculate financial year (April to March)
        if posting_date and posting_date.month >= 4:
            fy_start = current_year % 100
            fy_end = (current_year + 1) % 100
        else:
            fy_start = (current_year - 1) % 100
            fy_end = current_year % 100
        
        financial_year = f"{fy_start:02d}-{fy_end:02d}"
        
        # Use the Purchase Invoice name as remote invoice code (already generated by naming series)
        remote_invoice_code = purchase_invoice.name  # This is already AGO2O/25-26/012 format
        
        # Map ERPNext fields to ProcureUAT fields
        mapped_data = {
            'entity': purchase_invoice.custom_vendor or purchase_invoice.supplier_name,
            'subentity_id': purchase_invoice.custom_sub_branch or 'Default',
            'order_name': purchase_invoice.supplier_name,
            'delivery_date': posting_date,
            'validity_date': purchase_invoice.due_date or posting_date,
            'order_code': purchase_invoice.name,  # ERPNext Purchase Invoice ID
            'address': self.format_address(purchase_invoice),
            'remark': 'No Remarks',
            'acknowledgement': 1,
            'gru_ack': 0,
            'currency_id': 1,  # Assuming INR
            'category': 0,
            'amend_no': '0',
            'order_status': 2,  # Active status
            'finance_status': 1,
            'reason': 'Purchase Invoice imported from ERPNext',  # Key identifier
            'clone_id': 0,
            'is_delete': 0,
            'status': 'active',
            'transportation_mode': 'Road',
            'vehicle_no': 'None',
            'challan_number': 'TBD',
            'freight_rate': '0.00',
            'freight_cost': str(purchase_invoice.total_taxes_and_charges or 0),
            'requisition_at': posting_date,
            'requisition_by': 1,  # ERPNext system user
            'invoice_series': 1,
            'invoice_number': remote_invoice_code,  # Use ERPNext name (already from atomic counter)
            'invoice_generated': 1,
            'invoice_generated_at': posting_date,
            'is_visible_header': 1,
            'created_by': 1,  # ERPNext system user
            'vendor_created': 1,  # Indicates ERPNext origin
            'updated_by': 1,
            'gst_percentage': str(self.calculate_avg_gst_rate(purchase_invoice)),
            'is_new_invoice': 1,
            'is_invoice_cancel': 0,
            'credit_note_number': purchase_invoice.bill_no,  # Supplier invoice number
        }
        
        return mapped_data, remote_invoice_code
    
    def format_address(self, purchase_invoice):
        """Format address from ERPNext data"""
        if hasattr(purchase_invoice, 'address_display') and purchase_invoice.address_display:
            return purchase_invoice.address_display.replace('<br>', ', ')
        return f"{purchase_invoice.company}, India"
    
    def calculate_avg_gst_rate(self, purchase_invoice):
        """Calculate average GST rate from tax details"""
        try:
            total_gst = 0
            total_taxable = 0
            
            for tax in purchase_invoice.taxes:
                if 'gst' in tax.description.lower():
                    total_gst += tax.tax_amount or 0
                    total_taxable += tax.total or 0
            
            if total_taxable > 0:
                avg_rate = (total_gst / total_taxable) * 100
                return round(avg_rate)
            return 18  # Default GST rate
            
        except Exception:
            return 18  # Default fallback
    
    def create_remote_invoice(self, purchase_invoice):
        """
        Create invoice in ProcureUAT database
        
        Args:
            purchase_invoice: ERPNext Purchase Invoice document
        
        Returns:
            tuple: (success: bool, remote_invoice_code: str, message: str)
        """
        try:
            # Check if already synced
            if hasattr(purchase_invoice, 'custom_portal_sync_id') and purchase_invoice.custom_portal_sync_id:
                return True, purchase_invoice.custom_portal_sync_id, "Already synced"
            
            # Map data
            mapped_data, remote_invoice_code = self.map_erpnext_to_procure_data(purchase_invoice)
            
            # Insert into remote database
            with get_external_db_connection() as conn:
                with conn.cursor() as cursor:
                    # Build insert query
                    columns = list(mapped_data.keys())
                    placeholders = ', '.join(['%s'] * len(columns))
                    column_names = ', '.join(columns)
                    
                    insert_query = f"""
                        INSERT INTO purchase_requisitions ({column_names})
                        VALUES ({placeholders})
                    """
                    
                    values = list(mapped_data.values())
                    
                    frappe.logger().info(f"Inserting invoice {remote_invoice_code} into ProcureUAT")
                    cursor.execute(insert_query, values)
                    
                    # Get inserted ID
                    remote_id = cursor.lastrowid
                    
                    # Commit transaction
                    conn.commit()
                    
                    frappe.logger().info(f"Successfully created remote invoice {remote_invoice_code} with ID {remote_id}")
                    
                    return True, remote_invoice_code, f"Created with remote ID: {remote_id}"
                    
        except Exception as e:
            error_msg = f"Failed to create remote invoice: {str(e)}"
            frappe.logger().error(error_msg)
            return False, None, error_msg
    
    def update_erpnext_sync_status(self, purchase_invoice_name, remote_invoice_code, success=True):
        """
        Update ERPNext Purchase Invoice with sync status
        
        Args:
            purchase_invoice_name (str): ERPNext document name
            remote_invoice_code (str): Generated remote invoice code
            success (bool): Sync success status
        """
        try:
            doc = frappe.get_doc("Purchase Invoice", purchase_invoice_name)
            
            if success:
                doc.custom_portal_sync_id = remote_invoice_code
                doc.custom_sync_status = "Synced"
            else:
                doc.custom_sync_status = "Failed"
            
            # Save without triggering hooks
            doc.save(ignore_permissions=True)
            frappe.db.commit()
            
        except Exception as e:
            frappe.logger().error(f"Failed to update sync status: {str(e)}")

# Utility functions for API endpoints
def create_remote_invoice(purchase_invoice):
    """
    Main function to create remote invoice
    
    Args:
        purchase_invoice: ERPNext Purchase Invoice document
    
    Returns:
        tuple: (success: bool, invoice_code: str, message: str)
    """
    creator = RemoteInvoiceCreator()
    return creator.create_remote_invoice(purchase_invoice)

@frappe.whitelist()
def sync_purchase_invoice_to_remote(purchase_invoice_name):
    """
    API endpoint: Sync specific Purchase Invoice to remote database
    
    Args:
        purchase_invoice_name (str): Purchase Invoice name
    
    Returns:
        dict: Sync result
    """
    try:
        # Check permissions
        if not frappe.has_permission("Purchase Invoice", "write", purchase_invoice_name):
            return {
                'success': False,
                'message': 'Insufficient permissions to sync this invoice'
            }
        
        purchase_invoice = frappe.get_doc("Purchase Invoice", purchase_invoice_name)
        
        # Check if submitted
        if purchase_invoice.docstatus != 1:
            return {
                'success': False,
                'message': 'Only submitted invoices can be synced to portal'
            }
        
        creator = RemoteInvoiceCreator()
        
        success, remote_code, message = creator.create_remote_invoice(purchase_invoice)
        
        # Update sync status
        creator.update_erpnext_sync_status(purchase_invoice_name, remote_code, success)
        
        if success:
            frappe.msgprint(
                f"✅ Invoice {purchase_invoice_name} successfully synced to portal as {remote_code}",
                title="Sync Successful",
                indicator="green"
            )
        
        return {
            'success': success,
            'remote_invoice_code': remote_code,
            'message': message
        }
        
    except Exception as e:
        frappe.log_error(f"Manual sync error: {str(e)}", "Manual Invoice Sync Failed")
        return {
            'success': False,
            'message': str(e)
        }

@frappe.whitelist()
def batch_sync_invoices(invoice_names):
    """
    API endpoint: Batch sync multiple invoices
    
    Args:
        invoice_names (list): List of Purchase Invoice names
    
    Returns:
        dict: Batch sync results
    """
    try:
        if isinstance(invoice_names, str):
            invoice_names = json.loads(invoice_names)
        
        results = []
        success_count = 0
        
        for invoice_name in invoice_names:
            result = sync_purchase_invoice_to_remote(invoice_name)
            results.append({
                'invoice_name': invoice_name,
                **result
            })
            
            if result['success']:
                success_count += 1
        
        return {
            'success': True,
            'results': results,
            'total_processed': len(results),
            'successful': success_count,
            'failed': len(results) - success_count,
            'message': f'Batch sync completed: {success_count}/{len(results)} successful'
        }
        
    except Exception as e:
        frappe.log_error(f"Batch sync error: {str(e)}", "Batch Invoice Sync Failed")
        return {
            'success': False,
            'message': str(e)
        }

@frappe.whitelist()
def get_invoice_sync_status(purchase_invoice_name):
    """
    API endpoint: Get sync status of Purchase Invoice
    
    Args:
        purchase_invoice_name (str): Purchase Invoice name
    
    Returns:
        dict: Sync status info
    """
    try:
        doc = frappe.get_doc("Purchase Invoice", purchase_invoice_name)
        
        return {
            'success': True,
            'sync_status': doc.get('custom_sync_status', 'Not Synced'),
            'portal_sync_id': doc.get('custom_portal_sync_id'),
            'skip_external_sync': doc.get('custom_skip_external_sync', 0),
            'invoice_name': purchase_invoice_name
        }
        
    except Exception as e:
        return {
            'success': False,
            'message': str(e)
        }