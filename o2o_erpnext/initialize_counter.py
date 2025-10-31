#!/usr/bin/env python3

import pymysql
from sshtunnel import SSHTunnelForwarder
import os

# Database connection settings
PROCUREUAT_CONFIG = {
    'ssh_host': '65.0.222.210',
    'ssh_port': 22,
    'ssh_username': 'ubuntu',
    'ssh_key_path': '/home/erpnext/frappe-bench/apps/o2o_erpnext/o2o-Research/o2o-uat-lightsail.pem',
    'db_host': '127.0.0.1',
    'db_port': 3306,
    'db_username': 'frappeo2o', 
    'db_password': 'Reppyq-pijry0-fyktyq',
    'db_name': 'procureuat'
}

def initialize_invoice_counter():
    """Initialize the invoice_counter table with current highest number"""
    tunnel = None
    connection = None
    
    try:
        print("🔧 INITIALIZING INVOICE COUNTER")
        print("=" * 60)
        
        # Setup SSH tunnel
        ssh_key_path = PROCUREUAT_CONFIG['ssh_key_path']
        tunnel = SSHTunnelForwarder(
            (PROCUREUAT_CONFIG['ssh_host'], PROCUREUAT_CONFIG['ssh_port']),
            ssh_username=PROCUREUAT_CONFIG['ssh_username'],
            ssh_pkey=ssh_key_path,
            remote_bind_address=(PROCUREUAT_CONFIG['db_host'], PROCUREUAT_CONFIG['db_port']),
            local_bind_address=('127.0.0.1', 0)
        )
        
        tunnel.start()
        local_port = tunnel.local_bind_port
        
        # Connect to database
        connection = pymysql.connect(
            host='127.0.0.1',
            port=local_port,
            user=PROCUREUAT_CONFIG['db_username'],
            password=PROCUREUAT_CONFIG['db_password'],
            database=PROCUREUAT_CONFIG['db_name'],
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        
        print("✅ Connected to ProcureUAT database")
        
        with connection.cursor() as cursor:
            # 1. Find current highest AGO2O/25-26/ number
            print("🔍 Finding current highest invoice number...")
            cursor.execute("""
                SELECT MAX(CAST(SUBSTRING_INDEX(order_code, '/', -1) AS UNSIGNED)) as max_num
                FROM purchase_requisitions 
                WHERE order_code LIKE 'AGO2O/25-26/%'
                AND order_code REGEXP 'AGO2O/25-26/[0-9]+$'
            """)
            
            result = cursor.fetchone()
            max_num = result['max_num'] if result and result['max_num'] else 0
            
            print(f"📊 Current highest invoice number: {max_num}")
            
            # 2. Check if counter already exists
            cursor.execute("""
                SELECT * FROM invoice_counter 
                WHERE prefix = 'AGO2O' AND financial_year = '25-26'
            """)
            
            existing_counter = cursor.fetchone()
            
            if existing_counter:
                print(f"⚠️  Counter already exists with value: {existing_counter['last_number']}")
                print("🔄 Updating counter to current maximum...")
                
                cursor.execute("""
                    UPDATE invoice_counter 
                    SET last_number = %s, updated_at = NOW()
                    WHERE prefix = 'AGO2O' AND financial_year = '25-26'
                """, (max_num,))
                
                print(f"✅ Updated counter from {existing_counter['last_number']} to {max_num}")
                
            else:
                print("➕ Creating new counter record...")
                
                cursor.execute("""
                    INSERT INTO invoice_counter (prefix, financial_year, last_number, created_at, updated_at) 
                    VALUES ('AGO2O', '25-26', %s, NOW(), NOW())
                """, (max_num,))
                
                print(f"✅ Created new counter starting at {max_num}")
            
            # 3. Verify the counter
            cursor.execute("""
                SELECT * FROM invoice_counter 
                WHERE prefix = 'AGO2O' AND financial_year = '25-26'
            """)
            
            counter = cursor.fetchone()
            print(f"\n📋 Current counter state:")
            print(f"  Prefix: {counter['prefix']}")
            print(f"  Financial Year: {counter['financial_year']}")
            print(f"  Last Number: {counter['last_number']}")
            print(f"  Next Number: {counter['last_number'] + 1}")
            print(f"  Next Invoice: AGO2O/25-26/{counter['last_number'] + 1:04d}")
            
            # 4. Test atomic increment
            print(f"\n🧪 Testing atomic increment...")
            cursor.execute("""
                UPDATE invoice_counter 
                SET last_number = (@cur_value := last_number) + 1 
                WHERE prefix = 'AGO2O' AND financial_year = '25-26'
            """)
            
            cursor.execute("SELECT @cur_value as test_number")
            test_result = cursor.fetchone()
            test_number = test_result['test_number']
            
            print(f"✅ Atomic increment test successful!")
            print(f"  Generated number: {test_number}")
            print(f"  Would create: AGO2O/25-26/{test_number:04d}")
            
            # 5. Rollback the test increment
            cursor.execute("""
                UPDATE invoice_counter 
                SET last_number = last_number - 1 
                WHERE prefix = 'AGO2O' AND financial_year = '25-26'
            """)
            
            print(f"🔄 Rolled back test increment")
            
            # Commit changes
            connection.commit()
            
            print(f"\n✅ COUNTER INITIALIZATION COMPLETE!")
            print(f"📊 Next invoice will be: AGO2O/25-26/{max_num + 1:04d}")
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        if connection:
            connection.rollback()
        import traceback
        traceback.print_exc()
    
    finally:
        if connection:
            connection.close()
        if tunnel:
            tunnel.stop()

if __name__ == "__main__":
    initialize_invoice_counter()