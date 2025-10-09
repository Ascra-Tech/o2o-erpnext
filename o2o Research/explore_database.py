#!/usr/bin/env python3
"""
Database Explorer for ProcureUAT
"""

import pymysql
from sshtunnel import SSHTunnelForwarder
import os

def explore_database():
    """Explore the ProcureUAT database structure"""
    
    print("Exploring ProcureUAT Database Structure")
    print("=" * 50)
    
    ssh_key_path = '/home/erpnext/frappe-bench/apps/o2o_erpnext/o2o Research/o2o-uat-lightsail.pem'
    
    try:
        with SSHTunnelForwarder(
            ('65.0.222.210', 22),
            ssh_username='ubuntu',
            ssh_pkey=ssh_key_path,
            remote_bind_address=('127.0.0.1', 3306),
            local_bind_address=('127.0.0.1', 0)
        ) as tunnel:
            tunnel.start()
            print(f"✅ SSH tunnel established on local port {tunnel.local_bind_port}")
            
            connection = pymysql.connect(
                host='127.0.0.1',
                port=tunnel.local_bind_port,
                user='frappeo2o',
                password='Reppyq-pijry0-fyktyq',
                database='procureuat',
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            
            with connection.cursor() as cursor:
                # List all tables
                print("\n1. All Tables in Database:")
                cursor.execute("SHOW TABLES")
                tables = cursor.fetchall()
                table_names = [list(table.values())[0] for table in tables]
                
                for i, table_name in enumerate(table_names, 1):
                    print(f"   {i:2d}. {table_name}")
                
                # Look for invoice-related tables
                print("\n2. Invoice-related Tables:")
                invoice_tables = [t for t in table_names if 'invoice' in t.lower()]
                if invoice_tables:
                    for table in invoice_tables:
                        print(f"   - {table}")
                        cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                        count = cursor.fetchone()
                        print(f"     Records: {count['count']}")
                else:
                    print("   No tables with 'invoice' in the name found")
                
                # Look for purchase-related tables
                print("\n3. Purchase-related Tables:")
                purchase_tables = [t for t in table_names if 'purchase' in t.lower()]
                if purchase_tables:
                    for table in purchase_tables:
                        print(f"   - {table}")
                        cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                        count = cursor.fetchone()
                        print(f"     Records: {count['count']}")
                else:
                    print("   No tables with 'purchase' in the name found")
                
                # Look for order-related tables
                print("\n4. Order-related Tables:")
                order_tables = [t for t in table_names if 'order' in t.lower()]
                if order_tables:
                    for table in order_tables:
                        print(f"   - {table}")
                        cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                        count = cursor.fetchone()
                        print(f"     Records: {count['count']}")
                else:
                    print("   No tables with 'order' in the name found")
                
                # Look for billing-related tables
                print("\n5. Billing/Payment-related Tables:")
                billing_tables = [t for t in table_names if any(word in t.lower() for word in ['bill', 'payment', 'vendor', 'supplier'])]
                if billing_tables:
                    for table in billing_tables:
                        print(f"   - {table}")
                        cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                        count = cursor.fetchone()
                        print(f"     Records: {count['count']}")
                else:
                    print("   No billing/payment related tables found")
                
                # Show structure of the most promising table
                if purchase_tables:
                    main_table = purchase_tables[0]
                elif order_tables:
                    main_table = order_tables[0]
                elif invoice_tables:
                    main_table = invoice_tables[0]
                else:
                    # Try common table names
                    common_names = ['pos', 'transactions', 'sales', 'receipts']
                    main_table = None
                    for name in common_names:
                        matching = [t for t in table_names if name in t.lower()]
                        if matching:
                            main_table = matching[0]
                            break
                
                if main_table:
                    print(f"\n6. Structure of '{main_table}' table:")
                    cursor.execute(f"DESCRIBE {main_table}")
                    columns = cursor.fetchall()
                    for col in columns:
                        null_str = "NULL" if col['Null'] == 'YES' else "NOT NULL"
                        default = f"DEFAULT {col['Default']}" if col['Default'] else ""
                        print(f"   {col['Field']:20s} {col['Type']:15s} {null_str:8s} {default}")
                    
                    # Show sample data
                    print(f"\n7. Sample data from '{main_table}':")
                    cursor.execute(f"SELECT * FROM {main_table} LIMIT 3")
                    samples = cursor.fetchall()
                    if samples:
                        for i, sample in enumerate(samples, 1):
                            print(f"   Record {i}:")
                            for key, value in sample.items():
                                print(f"     {key}: {value}")
                            print()
                    else:
                        print("   No data in table")
            
            connection.close()
            
    except Exception as e:
        print(f"❌ Database exploration failed: {str(e)}")

if __name__ == "__main__":
    explore_database()