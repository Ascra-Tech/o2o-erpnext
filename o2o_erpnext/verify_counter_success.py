#!/usr/bin/env python3

import frappe
from o2o_erpnext.config.external_db_updated import get_external_db_connection

@frappe.whitelist()
def verify_current_counter():
    """
    Verify current counter status after the successful increment
    """
    try:
        with get_external_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM invoice_counter WHERE id = 1")
                counter = cursor.fetchone()
                
                if counter:
                    print(f"✅ COUNTER VERIFICATION:")
                    print(f"   Current last_number: {counter['last_number']}")
                    print(f"   Last updated: {counter['updated_at']}")
                    print(f"   Next invoice will be: AGO2O/25-26/{counter['last_number'] + 1:04d}")
                    
                    return {
                        'success': True,
                        'last_number': counter['last_number'],
                        'updated_at': str(counter['updated_at']),
                        'next_number': f"AGO2O/25-26/{counter['last_number'] + 1:04d}"
                    }
                else:
                    return {'success': False, 'message': 'Counter not found'}
                    
    except Exception as e:
        return {'success': False, 'error': str(e)}

if __name__ == "__main__":
    verify_current_counter()