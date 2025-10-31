#!/usr/bin/env python3

import os
import sys

# Add the Frappe app path
sys.path.append('/home/erpnext/frappe-bench/apps/frappe')
sys.path.append('/home/erpnext/frappe-bench/apps/o2o_erpnext')

import frappe
from o2o_erpnext.config.external_db_updated import get_external_db_connection

def verify_counter_status():
    """Verify current counter status using existing DB connection"""
    
    try:
        with get_external_db_connection() as conn:
            with conn.cursor() as cursor:
                
                print("🔍 COUNTER VERIFICATION AFTER AGO2O/25-26/0012")
                print("=" * 60)
                
                # 1. Check current counter status
                cursor.execute("SELECT * FROM invoice_counter WHERE id = 1")
                counter = cursor.fetchone()
                
                if counter:
                    print(f"📊 COUNTER STATUS:")
                    print(f"   ├─ Counter ID: {counter['id']}")
                    print(f"   ├─ Prefix: {counter['prefix']}")
                    print(f"   ├─ Financial Year: {counter['financial_year']}")
                    print(f"   ├─ Last Number: {counter['last_number']}")
                    print(f"   ├─ Created: {counter['created_at']}")
                    print(f"   └─ Updated: {counter['updated_at']}")
                    print()
                    
                    expected_next = counter['last_number'] + 1
                    print(f"🎯 NEXT EXPECTED: AGO2O/25-26/{expected_next:04d}")
                    print()
                    
                else:
                    print("❌ Counter not found!")
                    return
                
                # 2. Check if AGO2O/25-26/0012 exists in purchase_requisitions
                cursor.execute("""
                    SELECT invoice_number, order_code, created_at 
                    FROM purchase_requisitions 
                    WHERE invoice_number = 'AGO2O/25-26/0012'
                """)
                
                invoice_record = cursor.fetchone()
                if invoice_record:
                    print(f"✅ INVOICE FOUND IN DATABASE:")
                    print(f"   ├─ Invoice Number: {invoice_record['invoice_number']}")
                    print(f"   ├─ Order Code: {invoice_record['order_code']}")
                    print(f"   └─ Created: {invoice_record['created_at']}")
                    print()
                else:
                    print("⚠️  AGO2O/25-26/0012 NOT found in purchase_requisitions table")
                    print("   (This is normal if the invoice is still in Draft status)")
                    print("   (Counter increments on naming, not on save to remote DB)")
                    print()
                
                # 3. Show recent invoice numbers
                cursor.execute("""
                    SELECT invoice_number, order_code, created_at 
                    FROM purchase_requisitions 
                    WHERE invoice_number LIKE 'AGO2O/25-26/%'
                    ORDER BY created_at DESC 
                    LIMIT 5
                """)
                
                recent = cursor.fetchall()
                print(f"📋 RECENT AGO2O INVOICES IN REMOTE DB:")
                if recent:
                    for inv in recent:
                        print(f"   ├─ {inv['invoice_number']} (Order: {inv['order_code']}) - {inv['created_at']}")
                else:
                    print("   └─ No AGO2O invoices found")
                print()
                
                print("🎯 VERIFICATION SUMMARY:")
                if counter['last_number'] == 12:
                    print("   ✅ Counter is correctly set to 12")
                    print("   ✅ Your invoice AGO2O/25-26/0012 used the correct number")
                    print("   ✅ Next invoice will be AGO2O/25-26/0013")
                    print("   📝 Note: Invoice may not appear in remote DB until submitted/synced")
                else:
                    print(f"   ⚠️  Counter is at {counter['last_number']}")
                    if counter['last_number'] == 11:
                        print("   ❌ Counter was not incremented - there may be an issue")
                    elif counter['last_number'] > 12:
                        print("   ⚠️  Counter is ahead - other invoices may have been created")
                
    except Exception as e:
        print(f"❌ Error connecting to database: {str(e)}")
        print("Make sure the external database connection is properly configured.")

if __name__ == "__main__":
    # Initialize Frappe context
    os.chdir('/home/erpnext/frappe-bench')
    
    try:
        import frappe
        frappe.init(site='o2o.php')
        frappe.connect()
        verify_counter_status()
    except Exception as e:
        print(f"Error initializing Frappe: {e}")
        # Try without Frappe context
        verify_counter_status()