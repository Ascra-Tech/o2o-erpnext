#!/usr/bin/env python3
"""
Bidirectional Sync Test Script for O2O ERPNext System
This script tests the complete bidirectional synchronization functionality.
"""

import os
import sys
import frappe
from frappe import _
import json
from datetime import datetime, timedelta
import traceback

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

def test_external_database_connection():
    """Test external database connection"""
    print("\n🔌 Testing External Database Connection...")
    
    try:
        from o2o_erpnext.config.external_db import get_external_db_connection
        
        with get_external_db_connection() as cursor:
            # Test basic connectivity
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()
            print(f"✅ Connected to external database: MySQL {version['VERSION()']}")
            
            # Test required tables
            cursor.execute("SELECT COUNT(*) as count FROM invoices")
            invoice_count = cursor.fetchone()
            print(f"📊 External invoices: {invoice_count['count']}")
            
            cursor.execute("SELECT COUNT(*) as count FROM vendors")
            vendor_count = cursor.fetchone()
            print(f"📊 External vendors: {vendor_count['count']}")
            
            return True
            
    except Exception as e:
        print(f"❌ External database connection failed: {str(e)}")
        traceback.print_exc()
        return False

def test_field_mappings():
    """Test field mapping configurations"""
    print("\n🗺️  Testing Field Mappings...")
    
    try:
        from o2o_erpnext.config.field_mappings import (
            ERPNEXT_TO_PROCUREUAT_MAPPING,
            STATUS_MAPPING,
            get_vendor_id_from_supplier
        )
        
        print(f"✅ Field mappings loaded successfully")
        print(f"   ERPNext to ProcureUAT mappings: {len(ERPNEXT_TO_PROCUREUAT_MAPPING)} fields")
        print(f"   Status mappings: {len(STATUS_MAPPING)} statuses")
        
        # Test sample mapping
        sample_erpnext_data = {
            'name': 'PINV-2025-00001',
            'bill_no': 'EXT-INV-001',
            'grand_total': 1000.0,
            'posting_date': '2025-01-01'
        }
        
        mapped_data = {}
        for erpnext_field, external_field in ERPNEXT_TO_PROCUREUAT_MAPPING.items():
            if erpnext_field in sample_erpnext_data:
                mapped_data[external_field] = sample_erpnext_data[erpnext_field]
        
        print(f"✅ Sample mapping test successful")
        print(f"   Original: {sample_erpnext_data}")
        print(f"   Mapped: {mapped_data}")
        
        return True
        
    except Exception as e:
        print(f"❌ Field mapping test failed: {str(e)}")
        traceback.print_exc()
        return False

def create_test_supplier():
    """Create a test supplier for sync testing"""
    print("\n👥 Creating Test Supplier...")
    
    try:
        supplier_name = "Test Sync Supplier"
        
        # Check if supplier already exists
        if frappe.db.exists("Supplier", supplier_name):
            print(f"ℹ️  Supplier '{supplier_name}' already exists")
            return supplier_name
        
        supplier = frappe.get_doc({
            "doctype": "Supplier",
            "supplier_name": supplier_name,
            "supplier_group": "All Supplier Groups",
            "supplier_type": "Company"
        })
        
        supplier.insert()
        frappe.db.commit()
        
        print(f"✅ Created test supplier: {supplier_name}")
        return supplier_name
        
    except Exception as e:
        print(f"❌ Failed to create test supplier: {str(e)}")
        return None

def create_test_purchase_invoice():
    """Create a test Purchase Invoice for sync testing"""
    print("\n📄 Creating Test Purchase Invoice...")
    
    try:
        # Get or create test supplier
        supplier = create_test_supplier()
        if not supplier:
            return None
        
        # Create purchase invoice
        invoice = frappe.get_doc({
            "doctype": "Purchase Invoice",
            "supplier": supplier,
            "posting_date": datetime.now().date(),
            "bill_no": f"TEST-BILL-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "items": [
                {
                    "item_code": "_Test Item",
                    "qty": 1,
                    "rate": 100,
                    "amount": 100
                }
            ],
            "custom_external_invoice_id": f"EXT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "custom_gst_percentage": 18.0,
            "custom_sync_status": "Not Synced"
        })
        
        invoice.insert()
        frappe.db.commit()
        
        print(f"✅ Created test invoice: {invoice.name}")
        return invoice.name
        
    except Exception as e:
        print(f"❌ Failed to create test invoice: {str(e)}")
        traceback.print_exc()
        return None

def test_invoice_sync_log():
    """Test Invoice Sync Log functionality"""
    print("\n📝 Testing Invoice Sync Log...")
    
    try:
        # Create a test sync log
        sync_log = frappe.get_doc({
            "doctype": "Invoice Sync Log",
            "invoice_id": "TEST-INVOICE-001",
            "sync_direction": "ERPNext to External",
            "operation_type": "Create",
            "status": "In Progress",
            "started_at": datetime.now(),
            "external_data": json.dumps({"test": "data"})
        })
        
        sync_log.insert()
        frappe.db.commit()
        
        print(f"✅ Created sync log: {sync_log.name}")
        
        # Test marking as completed
        sync_log.mark_success("Test successful sync")
        
        # Reload and verify
        sync_log.reload()
        if sync_log.status == "Completed":
            print("✅ Sync log status update successful")
        else:
            print("❌ Sync log status update failed")
        
        return sync_log.name
        
    except Exception as e:
        print(f"❌ Sync log test failed: {str(e)}")
        traceback.print_exc()
        return None

def test_erpnext_to_external_sync():
    """Test ERPNext to External sync"""
    print("\n📤 Testing ERPNext to External Sync...")
    
    try:
        # Create test invoice
        invoice_name = create_test_purchase_invoice()
        if not invoice_name:
            return False
        
        # Import sync function
        from o2o_erpnext.sync.erpnext_to_external import sync_invoice_to_external
        
        # Test sync
        result = sync_invoice_to_external(invoice_name)
        
        if result.get('success'):
            print(f"✅ ERPNext to External sync successful")
            print(f"   Result: {result}")
            return True
        else:
            print(f"❌ ERPNext to External sync failed: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ ERPNext to External sync test failed: {str(e)}")
        traceback.print_exc()
        return False

def test_external_to_erpnext_sync():
    """Test External to ERPNext sync"""
    print("\n📥 Testing External to ERPNext Sync...")
    
    try:
        from o2o_erpnext.sync.external_to_erpnext import sync_invoices_from_external
        
        # Test sync (limit to 1 invoice for testing)
        result = sync_invoices_from_external(limit=1, test_mode=True)
        
        if result.get('success'):
            print(f"✅ External to ERPNext sync successful")
            print(f"   Processed: {result.get('processed', 0)} invoices")
            return True
        else:
            print(f"❌ External to ERPNext sync failed: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ External to ERPNext sync test failed: {str(e)}")
        traceback.print_exc()
        return False

def test_sync_utilities():
    """Test sync utility functions"""
    print("\n🔧 Testing Sync Utilities...")
    
    try:
        from o2o_erpnext.sync.sync_utils import (
            test_database_connection,
            get_sync_status,
            cleanup_old_logs
        )
        
        # Test database connection
        conn_result = test_database_connection()
        print(f"✅ Database connection test: {conn_result}")
        
        # Test sync status
        status = get_sync_status()
        print(f"✅ Sync status retrieved: {status}")
        
        # Test log cleanup (dry run)
        cleanup_result = cleanup_old_logs(days=30, dry_run=True)
        print(f"✅ Log cleanup test: {cleanup_result}")
        
        return True
        
    except Exception as e:
        print(f"❌ Sync utilities test failed: {str(e)}")
        traceback.print_exc()
        return False

def run_performance_test():
    """Run basic performance tests"""
    print("\n⚡ Running Performance Tests...")
    
    try:
        import time
        
        # Test database connection time
        start_time = time.time()
        from o2o_erpnext.config.external_db import get_external_db_connection
        
        with get_external_db_connection() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        
        connection_time = time.time() - start_time
        print(f"✅ Database connection time: {connection_time:.3f} seconds")
        
        # Test field mapping time
        start_time = time.time()
        from o2o_erpnext.config.field_mappings import ERPNEXT_TO_PROCUREUAT_MAPPING
        
        # Simulate mapping 100 records
        for i in range(100):
            mapped = {external: f"value_{i}" for erpnext, external in ERPNEXT_TO_PROCUREUAT_MAPPING.items()}
        
        mapping_time = time.time() - start_time
        print(f"✅ Field mapping time (100 records): {mapping_time:.3f} seconds")
        
        return True
        
    except Exception as e:
        print(f"❌ Performance test failed: {str(e)}")
        return False

def main():
    """Main test function"""
    print("🚀 O2O ERPNext Bidirectional Sync Test Suite")
    print("=" * 60)
    
    # Initialize Frappe
    if not initialize_frappe():
        return
    
    try:
        test_results = {}
        
        # Test 1: External database connection
        test_results['external_db'] = test_external_database_connection()
        
        # Test 2: Field mappings
        test_results['field_mappings'] = test_field_mappings()
        
        # Test 3: Invoice Sync Log
        test_results['sync_log'] = test_invoice_sync_log()
        
        # Test 4: ERPNext to External sync
        test_results['erpnext_to_external'] = test_erpnext_to_external_sync()
        
        # Test 5: External to ERPNext sync
        test_results['external_to_erpnext'] = test_external_to_erpnext_sync()
        
        # Test 6: Sync utilities
        test_results['sync_utilities'] = test_sync_utilities()
        
        # Test 7: Performance tests
        test_results['performance'] = run_performance_test()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 COMPREHENSIVE TEST RESULTS")
        print("=" * 60)
        
        total_tests = len(test_results)
        passed_tests = sum(1 for result in test_results.values() if result)
        
        for test_name, result in test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name.replace('_', ' ').title()}: {status}")
        
        print(f"\n📈 Overall: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("\n🎉 ALL TESTS PASSED!")
            print("💡 Your bidirectional sync system is ready for production use.")
        elif passed_tests >= total_tests * 0.7:
            print("\n⚠️  MOST TESTS PASSED")
            print("💡 System is mostly functional but some issues need attention.")
        else:
            print("\n❌ MULTIPLE TEST FAILURES")
            print("💡 System needs significant troubleshooting before use.")
            
        # Recommendations
        print("\n💡 RECOMMENDATIONS:")
        if not test_results.get('external_db'):
            print("   - Check database credentials and network connectivity")
        if not test_results.get('field_mappings'):
            print("   - Verify field mapping configuration")
        if not test_results.get('sync_log'):
            print("   - Check Invoice Sync Log doctype installation")
        if not test_results.get('erpnext_to_external'):
            print("   - Debug ERPNext to External sync logic")
        if not test_results.get('external_to_erpnext'):
            print("   - Debug External to ERPNext sync logic")
        if not test_results.get('sync_utilities'):
            print("   - Check sync utility function implementations")
            
    except Exception as e:
        print(f"❌ Test suite failed with error: {str(e)}")
        traceback.print_exc()
    
    finally:
        frappe.destroy()

if __name__ == "__main__":
    main()