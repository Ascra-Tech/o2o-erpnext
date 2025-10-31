#!/usr/bin/env python3

import pymysql
import sshtunnel
from datetime import datetime

def verify_counter_status():
    """Verify current counter status after invoice creation"""
    
    # Database connection through SSH tunnel
    with sshtunnel.SSHTunnelForwarder(
        ('154.114.6.77', 22),
        ssh_username='o2ocloudadmin',
        ssh_password='b5_k-8fSjN29',
        remote_bind_address=('localhost', 3306),
        local_bind_address=('localhost', 3307)
    ) as tunnel:
        
        connection = pymysql.connect(
            host='localhost',
            port=3307,
            user='o2olabs',
            password='o2oLabs@12345',
            database='ProcureUAT',
            cursorclass=pymysql.cursors.DictCursor
        )
        
        try:
            with connection.cursor() as cursor:
                
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
                    print("   (This is normal if the invoice is still in Draft status in ERPNext)")
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
                print(f"📋 RECENT AGO2O INVOICES:")
                if recent:
                    for inv in recent:
                        print(f"   ├─ {inv['invoice_number']} (Order: {inv['order_code']}) - {inv['created_at']}")
                else:
                    print("   └─ No AGO2O invoices found")
                print()
                
                # 4. Test what next number would be
                print(f"🧪 TESTING NEXT NUMBER GENERATION:")
                
                # Save current state
                cursor.execute("SELECT last_number FROM invoice_counter WHERE id = 1")
                current_number = cursor.fetchone()['last_number']
                
                # Start transaction for testing
                connection.begin()
                try:
                    # Test atomic increment
                    cursor.execute("""
                        UPDATE invoice_counter 
                        SET last_number = (@cur_value := last_number + 1) 
                        WHERE prefix = 'AGO2O' AND financial_year = '25-26'
                    """)
                    
                    cursor.execute("SELECT @cur_value as next_num")
                    test_result = cursor.fetchone()
                    next_num = test_result['next_num']
                    
                    print(f"   ├─ Current Counter: {current_number}")
                    print(f"   ├─ Next Number Would Be: {next_num}")
                    print(f"   └─ Next Invoice Would Be: AGO2O/25-26/{next_num:04d}")
                    
                    # Rollback test transaction
                    connection.rollback()
                    print("   (Test changes rolled back)")
                    
                except Exception as e:
                    connection.rollback()
                    print(f"   ❌ Test failed: {e}")
                
                print()
                print("🎯 VERIFICATION SUMMARY:")
                if counter['last_number'] == 12:
                    print("   ✅ Counter is correctly set to 12")
                    print("   ✅ Your invoice AGO2O/25-26/0012 used the correct number")
                    print("   ✅ Next invoice will be AGO2O/25-26/0013")
                else:
                    print(f"   ⚠️  Counter is at {counter['last_number']}, expected 12")
                    print("   ⚠️  This might indicate the counter wasn't incremented")
                
        finally:
            connection.close()

if __name__ == "__main__":
    verify_counter_status()