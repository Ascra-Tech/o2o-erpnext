#!/usr/bin/env python3
"""
Database Connection Test Script for O2O ERPNext Sync System
This script tests the database connection and validates the sync system setup.
"""

import os
import sys
import frappe
from frappe import _
import pymysql
from sshtunnel import SSHTunnelForwarder
import json
from datetime import datetime

def initialize_frappe():
    """Initialize Frappe context"""
    try:
        # Get the site name from frappe-bench directory
        sites_path = "/home/erpnext/frappe-bench/sites"
        sites = [d for d in os.listdir(sites_path) if os.path.isdir(os.path.join(sites_path, d)) and not d.startswith('.')]
        
        if not sites:
            print("❌ No sites found in frappe-bench")
            return False
            
        # Use the first site found
        site = sites[0]
        print(f"🔍 Using site: {site}")
        
        # Initialize Frappe
        frappe.init(site=site)
        frappe.connect()
        
        print(f"✅ Frappe initialized successfully for site: {site}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to initialize Frappe: {str(e)}")
        return False

def get_database_connections():
    """Fetch all Database Connection records"""
    try:
        connections = frappe.get_all(
            'Database Connection',
            fields=['name', 'db_name', 'hostname', 'port', 'username', 'ssh_host', 'ssh_port', 'ssh_username', 'enabled']
        )
        
        print(f"📊 Found {len(connections)} Database Connection records:")
        for conn in connections:
            print(f"  - {conn.name}: {conn.db_name}@{conn.hostname}:{conn.port} (Enabled: {conn.enabled})")
            
        return connections
        
    except Exception as e:
        print(f"❌ Failed to fetch Database Connection records: {str(e)}")
        return []

def test_direct_connection():
    """Test direct database connection with provided credentials"""
    print("\n🔌 Testing Direct Database Connection...")
    
    try:
        connection = pymysql.connect(
            host='65.0.222.210',
            port=3306,
            user='frappeo2o',
            password='Reppyq-pijry0-fyktyq',
            database='procureuat',
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=10,
            read_timeout=30,
            write_timeout=30
        )
        
        with connection.cursor() as cursor:
            # Test basic connectivity
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()
            print(f"✅ Connected to MySQL {version['VERSION()']}")
            
            # Test database access
            cursor.execute("SELECT DATABASE()")
            db = cursor.fetchone()
            print(f"✅ Connected to database: {db['DATABASE()']}")
            
            # Check if required tables exist
            cursor.execute("SHOW TABLES LIKE 'invoices'")
            invoices_table = cursor.fetchone()
            
            cursor.execute("SHOW TABLES LIKE 'vendors'")
            vendors_table = cursor.fetchone()
            
            if invoices_table:
                print("✅ 'invoices' table found")
                # Get table structure
                cursor.execute("DESCRIBE invoices")
                columns = cursor.fetchall()
                print(f"   Columns: {', '.join([col['Field'] for col in columns])}")
            else:
                print("❌ 'invoices' table not found")
                
            if vendors_table:
                print("✅ 'vendors' table found")
                # Get table structure
                cursor.execute("DESCRIBE vendors")
                columns = cursor.fetchall()
                print(f"   Columns: {', '.join([col['Field'] for col in columns])}")
            else:
                print("❌ 'vendors' table not found")
            
            # Test data access
            cursor.execute("SELECT COUNT(*) as count FROM invoices")
            invoice_count = cursor.fetchone()
            print(f"📊 Found {invoice_count['count']} invoices in external database")
            
            cursor.execute("SELECT COUNT(*) as count FROM vendors")
            vendor_count = cursor.fetchone()
            print(f"📊 Found {vendor_count['count']} vendors in external database")
            
        connection.close()
        print("✅ Direct connection test successful!")
        return True
        
    except Exception as e:
        print(f"❌ Direct connection failed: {str(e)}")
        return False

def test_ssh_tunnel_connection():
    """Test SSH tunnel connection"""
    print("\n🔒 Testing SSH Tunnel Connection...")
    
    try:
        # SSH tunnel configuration
        ssh_config = {
            'ssh_address_or_host': '65.0.222.210',
            'ssh_port': 22,
            'ssh_username': 'ec2-user',
            'ssh_pkey': '/home/erpnext/frappe-bench/apps/o2o_erpnext/o2o Research/o2o-uat-lightsail.pem',
            'remote_bind_address': '127.0.0.1',
            'remote_bind_port': 3306
        }
        
        print(f"🔑 SSH Config: {ssh_config['ssh_username']}@{ssh_config['ssh_address_or_host']}:{ssh_config['ssh_port']}")
        
        with SSHTunnelForwarder(
            ssh_address_or_host=(ssh_config['ssh_address_or_host'], ssh_config['ssh_port']),
            ssh_username=ssh_config['ssh_username'],
            ssh_pkey=ssh_config['ssh_pkey'],
            remote_bind_address=(ssh_config['remote_bind_address'], ssh_config['remote_bind_port']),
            local_bind_address=('127.0.0.1', 0)  # Use any available local port
        ) as tunnel:
            
            print(f"✅ SSH tunnel established on local port {tunnel.local_bind_port}")
            
            # Connect through tunnel
            connection = pymysql.connect(
                host='127.0.0.1',
                port=tunnel.local_bind_port,
                user='frappeo2o',
                password='Reppyq-pijry0-fyktyq',
                database='procureuat',
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor,
                connect_timeout=10
            )
            
            with connection.cursor() as cursor:
                cursor.execute("SELECT VERSION()")
                version = cursor.fetchone()
                print(f"✅ Connected through SSH tunnel to MySQL {version['VERSION()']}")
                
                # Test a simple query
                cursor.execute("SELECT COUNT(*) as count FROM invoices")
                result = cursor.fetchone()
                print(f"✅ Query successful: {result['count']} invoices found")
                
            connection.close()
            print("✅ SSH tunnel connection test successful!")
            return True
            
    except Exception as e:
        print(f"❌ SSH tunnel connection failed: {str(e)}")
        return False

def test_sync_system_components():
    """Test sync system components"""
    print("\n🔧 Testing Sync System Components...")
    
    try:
        # Test imports
        print("📦 Testing imports...")
        
        try:
            from o2o_erpnext.config.external_db import get_external_db_connection
            print("✅ external_db module imported successfully")
        except ImportError as e:
            print(f"❌ Failed to import external_db: {e}")
            
        try:
            from o2o_erpnext.config.field_mappings import ERPNEXT_TO_PROCUREUAT_MAPPING
            print("✅ field_mappings module imported successfully")
        except ImportError as e:
            print(f"❌ Failed to import field_mappings: {e}")
            
        try:
            from o2o_erpnext.sync.sync_utils import test_database_connection
            print("✅ sync_utils module imported successfully")
        except ImportError as e:
            print(f"❌ Failed to import sync_utils: {e}")
        
        # Test custom fields on Purchase Invoice
        print("\n📋 Testing Purchase Invoice custom fields...")
        doc = frappe.get_meta("Purchase Invoice")
        
        required_fields = [
            'custom_external_invoice_id',
            'custom_external_vendor_id', 
            'custom_gst_percentage',
            'custom_last_sync_date',
            'custom_sync_status',
            'custom_skip_external_sync',
            'custom_auto_created_from_external'
        ]
        
        existing_fields = [f.fieldname for f in doc.fields]
        
        for field in required_fields:
            if field in existing_fields:
                print(f"✅ Custom field '{field}' exists")
            else:
                print(f"❌ Custom field '{field}' missing")
        
        # Test Invoice Sync Log doctype
        print("\n📝 Testing Invoice Sync Log doctype...")
        try:
            frappe.get_meta("Invoice Sync Log")
            print("✅ Invoice Sync Log doctype exists")
        except Exception as e:
            print(f"❌ Invoice Sync Log doctype missing: {e}")
            
        return True
        
    except Exception as e:
        print(f"❌ Sync system component test failed: {str(e)}")
        return False

def create_test_database_connection():
    """Create a test Database Connection record"""
    print("\n📝 Creating test Database Connection record...")
    
    try:
        # Check if connection already exists
        existing = frappe.db.exists("Database Connection", "ProcureUAT Test")
        if existing:
            print("ℹ️  Database Connection 'ProcureUAT Test' already exists")
            return existing
        
        doc = frappe.get_doc({
            "doctype": "Database Connection",
            "name": "ProcureUAT Test",
            "db_name": "procureuat",
            "hostname": "65.0.222.210",
            "port": 3306,
            "username": "frappeo2o",
            "password": "Reppyq-pijry0-fyktyq",
            "ssh_host": "65.0.222.210",
            "ssh_port": 22,
            "ssh_username": "ec2-user",
            "ssh_private_key_path": "/home/erpnext/frappe-bench/apps/o2o_erpnext/o2o Research/o2o-uat-lightsail.pem",
            "enabled": 1
        })
        
        doc.insert()
        frappe.db.commit()
        
        print(f"✅ Created Database Connection: {doc.name}")
        return doc.name
        
    except Exception as e:
        print(f"❌ Failed to create Database Connection: {str(e)}")
        return None

def main():
    """Main test function"""
    print("🚀 O2O ERPNext Database Connection Test")
    print("=" * 50)
    
    # Initialize Frappe
    if not initialize_frappe():
        return
    
    try:
        # Test 1: Check existing database connections
        connections = get_database_connections()
        
        # Test 2: Test direct database connection
        direct_success = test_direct_connection()
        
        # Test 3: Test SSH tunnel connection
        ssh_success = test_ssh_tunnel_connection()
        
        # Test 4: Test sync system components
        components_success = test_sync_system_components()
        
        # Test 5: Create test database connection if needed
        if not connections:
            create_test_database_connection()
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)
        print(f"Direct Connection: {'✅ PASS' if direct_success else '❌ FAIL'}")
        print(f"SSH Tunnel: {'✅ PASS' if ssh_success else '❌ FAIL'}")
        print(f"System Components: {'✅ PASS' if components_success else '❌ FAIL'}")
        
        if direct_success or ssh_success:
            print("\n🎉 Database connectivity is working!")
            print("💡 You can now proceed with sync testing.")
        else:
            print("\n⚠️  Database connectivity issues detected.")
            print("💡 Please check your network connection and credentials.")
            
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
    
    finally:
        frappe.destroy()

if __name__ == "__main__":
    main()