#!/usr/bin/env python3
"""
Standalone Database Connection Test for O2O ERPNext (No Frappe dependency)
"""

import pymysql
from sshtunnel import SSHTunnelForwarder
import os
import sys

def test_database_connection():
    """Test database connection to ProcureUAT without Frappe context"""
    
    print("Testing Database Connection to ProcureUAT")
    print("=" * 50)
    
    direct_success = False
    ssh_success = False
    
    # Test 1: Direct Database Connection
    print("\n1. Testing Direct Database Connection...")
    try:
        connection = pymysql.connect(
            host='65.0.222.210',
            port=3306,
            user='frappeo2o',
            password='Reppyq-pijry0-fyktyq',
            database='procureuat',
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=30,
            read_timeout=30,
            write_timeout=30
        )
        
        with connection.cursor() as cursor:
            cursor.execute("SELECT VERSION() as version, DATABASE() as db_name, USER() as user")
            result = cursor.fetchone()
            print(f"✅ Direct connection successful!")
            print(f"   MySQL Version: {result['version']}")
            print(f"   Database: {result['db_name']}")
            print(f"   User: {result['user']}")
            
            # Test table access
            cursor.execute("SHOW TABLES LIKE 'invoices'")
            table_exists = cursor.fetchone()
            if table_exists:
                print(f"✅ invoices table found")
                cursor.execute("SELECT COUNT(*) as count FROM invoices")
                count = cursor.fetchone()
                print(f"   Records in invoices: {count['count']}")
                
                # Show table structure
                cursor.execute("DESCRIBE invoices")
                columns = cursor.fetchall()
                print(f"   Table columns: {len(columns)}")
                for col in columns:  # Show all columns for invoices table
                    print(f"     - {col['Field']}: {col['Type']}")
                
                # Show sample data if records exist
                if count['count'] > 0:
                    cursor.execute("SELECT * FROM invoices LIMIT 3")
                    sample_records = cursor.fetchall()
                    print(f"   Sample records:")
                    for i, record in enumerate(sample_records, 1):
                        print(f"     Record {i}:")
                        for key, value in record.items():
                            if value is not None:
                                print(f"       {key}: {value}")
                        print()
            else:
                print(f"❌ invoices table not found")
                
                # List available tables
                cursor.execute("SHOW TABLES")
                tables = cursor.fetchall()
                print(f"   Available tables ({len(tables)}):")
                for table in tables[:10]:  # Show first 10 tables
                    table_name = list(table.values())[0]
                    print(f"     - {table_name}")
                if len(tables) > 10:
                    print(f"     ... and {len(tables) - 10} more tables")
        
        connection.close()
        direct_success = True
        
    except Exception as e:
        print(f"❌ Direct connection failed: {str(e)}")
        print("   This is expected if the database only allows SSH tunnel connections")
    
    # Test 2: SSH Tunnel Connection
    print("\n2. Testing SSH Tunnel Connection...")
    try:
        # Check if SSH key exists
        ssh_key_path = '/home/erpnext/frappe-bench/apps/o2o_erpnext/o2o Research/o2o-uat-lightsail.pem'
        if not os.path.exists(ssh_key_path):
            print(f"❌ SSH key not found at {ssh_key_path}")
            
            # Try alternative locations
            alternative_paths = [
                '/home/erpnext/frappe-bench/o2o-uat-lightsail.pem',
                '/home/erpnext/o2o-uat-lightsail.pem',
                '/home/erpnext/.ssh/o2o-uat-lightsail.pem',
                './o2o-uat-lightsail.pem'
            ]
            
            for alt_path in alternative_paths:
                if os.path.exists(alt_path):
                    ssh_key_path = alt_path
                    print(f"✅ SSH key found at {ssh_key_path}")
                    break
            else:
                print(f"❌ SSH key not found in any expected location:")
                for path in ['/home/erpnext/frappe-bench/apps/o2o_erpnext/o2o Research/o2o-uat-lightsail.pem'] + alternative_paths:
                    print(f"   - {path}")
                return False
        else:
            print(f"✅ SSH key found at {ssh_key_path}")
            
        with SSHTunnelForwarder(
            ('65.0.222.210', 22),
            ssh_username='ubuntu',
            ssh_pkey=ssh_key_path,
            remote_bind_address=('localhost', 3306),  # Try localhost instead of 127.0.0.1
            local_bind_address=('127.0.0.1', 0)  # Use random local port
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
                cursor.execute("SELECT VERSION() as version, DATABASE() as db_name, USER() as user")
                result = cursor.fetchone()
                print(f"✅ SSH tunnel connection successful!")
                print(f"   MySQL Version: {result['version']}")
                print(f"   Database: {result['db_name']}")
                print(f"   User: {result['user']}")
                
                # Test table access
                cursor.execute("SHOW TABLES LIKE 'invoices'")
                table_exists = cursor.fetchone()
                if table_exists:
                    print(f"✅ invoices table found via SSH tunnel")
                    cursor.execute("SELECT COUNT(*) as count FROM invoices")
                    count = cursor.fetchone()
                    print(f"   Records in invoices: {count['count']}")
                    
                    # Show table structure
                    cursor.execute("DESCRIBE invoices")
                    columns = cursor.fetchall()
                    print(f"   Table columns: {len(columns)}")
                    for col in columns:  # Show all columns for invoices table
                        print(f"     - {col['Field']}: {col['Type']}")
                    
                    # Show sample data if records exist
                    if count['count'] > 0:
                        cursor.execute("SELECT * FROM invoices LIMIT 2")
                        sample_records = cursor.fetchall()
                        print(f"   Sample records:")
                        for i, record in enumerate(sample_records, 1):
                            print(f"     Record {i}:")
                            for key, value in record.items():
                                if value is not None:
                                    print(f"       {key}: {value}")
                            print()
                else:
                    print(f"❌ invoices table not found via SSH tunnel")
                    
                    # List available tables for debugging
                    cursor.execute("SHOW TABLES")
                    tables = cursor.fetchall()
                    print(f"   Available tables ({len(tables)}):")
                    for table in tables[:15]:  # Show first 15 tables
                        table_name = list(table.values())[0]
                        print(f"     - {table_name}")
                    if len(tables) > 15:
                        print(f"     ... and {len(tables) - 15} more tables")
                print(f"   Database: {result['db_name']}")
                print(f"   User: {result['user']}")
                
                # Test table access through SSH tunnel
                cursor.execute("SHOW TABLES LIKE 'purchase_invoices'")
                table_exists = cursor.fetchone()
                if table_exists:
                    print(f"✅ purchase_invoices table found via SSH tunnel")
                    cursor.execute("SELECT COUNT(*) as count FROM purchase_invoices")
                    count = cursor.fetchone()
                    print(f"   Records in purchase_invoices: {count['count']}")
                else:
                    print(f"❌ purchase_invoices table not found via SSH tunnel")
                    
                    # List available tables
                    cursor.execute("SHOW TABLES")
                    tables = cursor.fetchall()
                    print(f"   Available tables ({len(tables)}):")
                    for table in tables[:10]:  # Show first 10 tables
                        table_name = list(table.values())[0]
                        print(f"     - {table_name}")
                    if len(tables) > 10:
                        print(f"     ... and {len(tables) - 10} more tables")
                print(f"   Database: {result['database']}")
                print(f"   User: {result['user']}")
                
                # Test table access through SSH tunnel
                cursor.execute("SHOW TABLES LIKE 'purchase_invoices'")
                table_exists = cursor.fetchone()
                if table_exists:
                    print(f"✅ purchase_invoices table found")
                    cursor.execute("SELECT COUNT(*) as count FROM purchase_invoices")
                    count = cursor.fetchone()
                    print(f"   Records in purchase_invoices: {count['count']}")
                    
                    # Show table structure
                    cursor.execute("DESCRIBE purchase_invoices")
                    columns = cursor.fetchall()
                    print(f"   Table columns: {len(columns)}")
                    for col in columns[:5]:  # Show first 5 columns
                        print(f"     - {col['Field']}: {col['Type']}")
                    if len(columns) > 5:
                        print(f"     ... and {len(columns) - 5} more columns")
                else:
                    print(f"❌ purchase_invoices table not found")
                    
                    # List available tables
                    cursor.execute("SHOW TABLES")
                    tables = cursor.fetchall()
                    print(f"   Available tables ({len(tables)}):")
                    for table in tables[:10]:  # Show first 10 tables
                        table_name = list(table.values())[0]
                        print(f"     - {table_name}")
                    if len(tables) > 10:
                        print(f"     ... and {len(tables) - 10} more tables")
            
            connection.close()
            ssh_success = True
            
    except Exception as e:
        print(f"❌ SSH tunnel connection failed: {str(e)}")
    
    return direct_success or ssh_success

def test_python_imports():
    """Test if required Python modules are available"""
    print("\n3. Testing Python Module Imports...")
    
    try:
        import pymysql
        print(f"✅ pymysql version: {pymysql.__version__}")
    except ImportError as e:
        print(f"❌ pymysql import failed: {e}")
        
    try:
        import sshtunnel
        print(f"✅ sshtunnel imported successfully")
    except ImportError as e:
        print(f"❌ sshtunnel import failed: {e}")
        
    # Test if we can import frappe (optional)
    try:
        import frappe
        print(f"✅ frappe imported successfully")
        print(f"   Frappe path: {frappe.__file__}")
    except ImportError as e:
        print(f"ℹ️  frappe not available in this context: {e}")

if __name__ == "__main__":
    print("Standalone Database Connection Test")
    print("This test runs without Frappe context")
    print()
    
    # Test Python imports first
    test_python_imports()
    
    # Test database connection
    success = test_database_connection()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ Database connection test PASSED!")
        print("The sync system should work with this database connection.")
    else:
        print("❌ Database connection test FAILED!")
        print("Please check your network connection, credentials, and SSH key.")
    print("=" * 50)