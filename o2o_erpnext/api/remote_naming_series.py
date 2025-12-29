#!/usr/bin/env python3

import frappe
from frappe import _
from frappe.model.naming import make_autoname
from o2o_erpnext.config.external_db_updated import get_external_db_connection

def get_next_invoice_number_from_remote(prefix='AGO2O', financial_year='25-26'):
    """
    Get next invoice number from remote database counter
    This will be used for ERPNext Purchase Invoice naming series
    
    Args:
        prefix (str): Invoice prefix (default: 'AGO2O')
        financial_year (str): Financial year (default: '25-26')
    
    Returns:
        str: Next invoice number (e.g., 'AGO2O/25-26/012')
    """
    try:
        with get_external_db_connection() as conn:
            with conn.cursor() as cursor:
                # Use erpnext_invoice_counter table (single counter system)
                # Check if counter table exists, create if not
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS erpnext_invoice_counter (
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
                    INSERT IGNORE INTO erpnext_invoice_counter (prefix, financial_year, last_number)
                    SELECT %s, %s, COALESCE(MAX(CAST(SUBSTRING_INDEX(invoice_number, '/', -1) AS UNSIGNED)), 0)
                    FROM purchase_requisitions 
                    WHERE invoice_number LIKE %s
                """, (prefix, financial_year, f"{prefix}/{financial_year}/%"))
                
                # Atomic increment using MySQL session variable
                cursor.execute("""
                    UPDATE erpnext_invoice_counter 
                    SET last_number = (@cur_value := last_number) + 1 
                    WHERE prefix = %s AND financial_year = %s
                """, (prefix, financial_year))
                
                if cursor.rowcount == 0:
                    # Initialize if somehow missed
                    cursor.execute("""
                        INSERT INTO erpnext_invoice_counter (prefix, financial_year, last_number)
                        VALUES (%s, %s, 1)
                    """, (prefix, financial_year))
                    next_number = 1
                else:
                    # Get the incremented value
                    cursor.execute("SELECT @cur_value as invoice_num")
                    result = cursor.fetchone()
                    
                    if not result or not result['invoice_num']:
                        raise Exception("Failed to generate invoice number")
                    
                    next_number = int(result['invoice_num'])
                
                invoice_number = f"{prefix}/{financial_year}/{next_number:03d}"
                
                frappe.logger().info(f"Generated invoice number from remote counter: {invoice_number}")
                return invoice_number
                
    except Exception as e:
        frappe.logger().error(f"Error generating invoice number from remote: {str(e)}")
        # Fallback to standard ERPNext naming if remote fails
        frappe.log_error(f"Remote counter failed: {str(e)}", "Remote Invoice Naming")
        raise Exception(f"Remote counter unavailable: {str(e)}")

def get_current_financial_year():
    """
    Get current financial year in format YY-YY (e.g., 25-26)
    Based on April to March financial year
    """
    import datetime
    
    today = datetime.date.today()
    current_month = today.month
    current_year = today.year
    
    if current_month >= 4:  # April to March financial year
        start_year = current_year % 100
        end_year = (current_year + 1) % 100
    else:
        start_year = (current_year - 1) % 100
        end_year = current_year % 100
    
    return f"{start_year:02d}-{end_year:02d}"

@frappe.whitelist()
def get_next_purchase_invoice_name():
    """
    API to get next Purchase Invoice name from remote counter
    This can be called from client script
    """
    try:
        financial_year = get_current_financial_year()
        invoice_number = get_next_invoice_number_from_remote('AGO2O', financial_year)
        
        return {
            'success': True,
            'invoice_number': invoice_number,
            'message': f'Next invoice number: {invoice_number}'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to get remote invoice number'
        }