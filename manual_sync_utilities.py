#!/usr/bin/env python3
"""
Manual Sync Utilities for O2O ERPNext System
This script provides manual sync operations and debugging tools.
"""

import os
import sys
import frappe
from frappe import _
import json
from datetime import datetime, timedelta
import argparse
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

def manual_sync_invoice_to_external(invoice_id):
    """Manually sync a specific invoice to external system"""
    print(f"\n📤 Manually syncing invoice {invoice_id} to external system...")
    
    try:
        from o2o_erpnext.sync.erpnext_to_external_updated import sync_invoice_to_external
        
        result = sync_invoice_to_external(invoice_id)
        
        if result.get('success'):
            print(f"✅ Successfully synced invoice {invoice_id}")
            print(f"   External ID: {result.get('external_id')}")
            print(f"   Sync time: {result.get('sync_time')}")
        else:
            print(f"❌ Failed to sync invoice {invoice_id}: {result.get('error')}")
            
        return result
        
    except Exception as e:
        print(f"❌ Manual sync failed: {str(e)}")
        traceback.print_exc()
        return {'success': False, 'error': str(e)}

def manual_sync_from_external(limit=10):
    """Manually sync invoices from external system"""
    print(f"\n📥 Manually syncing up to {limit} invoices from external system...")
    
    try:
        from o2o_erpnext.sync.external_to_erpnext_updated import sync_invoices_from_external
        
        result = sync_invoices_from_external(limit=limit)
        
        if result.get('success'):
            print(f"✅ Successfully processed {result.get('processed', 0)} invoices")
            print(f"   Created: {result.get('created', 0)}")
            print(f"   Updated: {result.get('updated', 0)}")
            print(f"   Errors: {result.get('errors', 0)}")
        else:
            print(f"❌ Failed to sync from external: {result.get('error')}")
            
        return result
        
    except Exception as e:
        print(f"❌ Manual sync from external failed: {str(e)}")
        traceback.print_exc()
        return {'success': False, 'error': str(e)}

def check_sync_status():
    """Check overall sync status"""
    print("\n📊 Checking sync status...")
    
    try:
        from o2o_erpnext.sync.sync_utils import get_sync_status
        
        status = get_sync_status()
        
        print(f"✅ Sync Status Retrieved:")
        print(f"   Last sync: {status.get('last_sync')}")
        print(f"   Pending syncs: {status.get('pending_syncs', 0)}")
        print(f"   Failed syncs: {status.get('failed_syncs', 0)}")
        print(f"   Total logs: {status.get('total_logs', 0)}")
        
        return status
        
    except Exception as e:
        print(f"❌ Failed to check sync status: {str(e)}")
        return None

def list_pending_syncs():
    """List all pending sync operations"""
    print("\n⏳ Listing pending sync operations...")
    
    try:
        # Get Purchase Invoices with sync status "Not Synced" or "Failed"
        pending = frappe.get_all(
            'Purchase Invoice',
            filters={
                'custom_sync_status': ['in', ['Not Synced', 'Failed']],
                'custom_skip_external_sync': 0
            },
            fields=['name', 'supplier', 'grand_total', 'custom_sync_status', 'custom_last_sync_date'],
            limit=20
        )
        
        if pending:
            print(f"📋 Found {len(pending)} pending syncs:")
            for invoice in pending:
                print(f"   - {invoice.name}: {invoice.supplier} (₹{invoice.grand_total}) - {invoice.custom_sync_status}")
        else:
            print("✅ No pending syncs found")
            
        return pending
        
    except Exception as e:
        print(f"❌ Failed to list pending syncs: {str(e)}")
        return []

def list_failed_syncs():
    """List all failed sync operations"""
    print("\n❌ Listing failed sync operations...")
    
    try:
        failed_logs = frappe.get_all(
            'Invoice Sync Log',
            filters={'status': 'Failed'},
            fields=['name', 'invoice_id', 'sync_direction', 'error_message', 'started_at'],
            order_by='started_at desc',
            limit=20
        )
        
        if failed_logs:
            print(f"📋 Found {len(failed_logs)} failed syncs:")
            for log in failed_logs:
                print(f"   - {log.name}: {log.invoice_id} ({log.sync_direction}) - {log.error_message[:50]}...")
        else:
            print("✅ No failed syncs found")
            
        return failed_logs
        
    except Exception as e:
        print(f"❌ Failed to list failed syncs: {str(e)}")
        return []

def retry_failed_sync(sync_log_id):
    """Retry a specific failed sync"""
    print(f"\n🔄 Retrying failed sync {sync_log_id}...")
    
    try:
        from o2o_erpnext.sync.sync_utils import retry_failed_sync
        
        result = retry_failed_sync(sync_log_id)
        
        if result.get('success'):
            print(f"✅ Successfully retried sync {sync_log_id}")
        else:
            print(f"❌ Failed to retry sync {sync_log_id}: {result.get('error')}")
            
        return result
        
    except Exception as e:
        print(f"❌ Retry failed: {str(e)}")
        return {'success': False, 'error': str(e)}

def cleanup_old_logs(days=30, dry_run=True):
    """Clean up old sync logs"""
    print(f"\n🧹 Cleaning up sync logs older than {days} days (dry_run={dry_run})...")
    
    try:
        from o2o_erpnext.sync.sync_utils import cleanup_old_logs
        
        result = cleanup_old_logs(days=days, dry_run=dry_run)
        
        if dry_run:
            print(f"🔍 Would delete {result.get('count', 0)} old logs")
        else:
            print(f"✅ Deleted {result.get('count', 0)} old logs")
            
        return result
        
    except Exception as e:
        print(f"❌ Cleanup failed: {str(e)}")
        return {'success': False, 'error': str(e)}

def reset_invoice_sync_status(invoice_id):
    """Reset sync status of a specific invoice"""
    print(f"\n🔄 Resetting sync status for invoice {invoice_id}...")
    
    try:
        invoice = frappe.get_doc('Purchase Invoice', invoice_id)
        
        # Reset sync fields
        invoice.custom_sync_status = 'Not Synced'
        invoice.custom_last_sync_date = None
        invoice.custom_external_sync_date = None
        invoice.custom_skip_external_sync = 0
        
        invoice.save()
        frappe.db.commit()
        
        print(f"✅ Reset sync status for invoice {invoice_id}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to reset sync status: {str(e)}")
        return False

def view_invoice_sync_details(invoice_id):
    """View detailed sync information for an invoice"""
    print(f"\n🔍 Viewing sync details for invoice {invoice_id}...")
    
    try:
        # Get invoice details
        invoice = frappe.get_doc('Purchase Invoice', invoice_id)
        
        print(f"📄 Invoice Details:")
        print(f"   Name: {invoice.name}")
        print(f"   Supplier: {invoice.supplier}")
        print(f"   Bill No: {invoice.bill_no}")
        print(f"   Grand Total: ₹{invoice.grand_total}")
        print(f"   Sync Status: {invoice.custom_sync_status}")
        print(f"   External ID: {invoice.custom_external_invoice_id or 'N/A'}")
        print(f"   Last Sync: {invoice.custom_last_sync_date or 'Never'}")
        print(f"   Skip Sync: {invoice.custom_skip_external_sync}")
        
        # Get related sync logs
        logs = frappe.get_all(
            'Invoice Sync Log',
            filters={'invoice_id': invoice_id},
            fields=['name', 'sync_direction', 'operation_type', 'status', 'started_at', 'completed_at'],
            order_by='started_at desc'
        )
        
        if logs:
            print(f"\n📝 Sync Logs ({len(logs)}):")
            for log in logs:
                duration = ""
                if log.started_at and log.completed_at:
                    start = datetime.fromisoformat(str(log.started_at))
                    end = datetime.fromisoformat(str(log.completed_at))
                    duration = f" ({(end - start).total_seconds():.1f}s)"
                
                print(f"   - {log.name}: {log.sync_direction} {log.operation_type} - {log.status}{duration}")
        else:
            print("\n📝 No sync logs found")
            
        return True
        
    except Exception as e:
        print(f"❌ Failed to view sync details: {str(e)}")
        return False

def test_external_connection():
    """Test external database connection"""
    print("\n🔌 Testing external database connection...")
    
    try:
        from o2o_erpnext.config.external_db_updated import get_external_db_connection
        
        with get_external_db_connection() as cursor:
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()
            print(f"✅ Connected to MySQL {version['VERSION()']}")
            
            cursor.execute("SELECT COUNT(*) as count FROM invoices")
            invoice_count = cursor.fetchone()
            print(f"📊 External invoices: {invoice_count['count']}")
            
            cursor.execute("SELECT COUNT(*) as count FROM vendors")
            vendor_count = cursor.fetchone()
            print(f"📊 External vendors: {vendor_count['count']}")
            
            return True
            
    except Exception as e:
        print(f"❌ Connection test failed: {str(e)}")
        return False

def main():
    """Main function with command line interface"""
    parser = argparse.ArgumentParser(description='O2O ERPNext Manual Sync Utilities')
    parser.add_argument('action', choices=[
        'test-connection', 'sync-to-external', 'sync-from-external', 
        'status', 'pending', 'failed', 'retry', 'cleanup', 'reset', 'details'
    ], help='Action to perform')
    
    parser.add_argument('--invoice-id', help='Invoice ID for specific operations')
    parser.add_argument('--sync-log-id', help='Sync Log ID for retry operations')
    parser.add_argument('--limit', type=int, default=10, help='Limit for batch operations')
    parser.add_argument('--days', type=int, default=30, help='Days for cleanup operations')
    parser.add_argument('--dry-run', action='store_true', help='Dry run for cleanup')
    
    args = parser.parse_args()
    
    print("🔧 O2O ERPNext Manual Sync Utilities")
    print("=" * 50)
    
    # Initialize Frappe
    if not initialize_frappe():
        return
    
    try:
        if args.action == 'test-connection':
            test_external_connection()
            
        elif args.action == 'sync-to-external':
            if not args.invoice_id:
                print("❌ --invoice-id required for sync-to-external")
                return
            manual_sync_invoice_to_external(args.invoice_id)
            
        elif args.action == 'sync-from-external':
            manual_sync_from_external(args.limit)
            
        elif args.action == 'status':
            check_sync_status()
            
        elif args.action == 'pending':
            list_pending_syncs()
            
        elif args.action == 'failed':
            list_failed_syncs()
            
        elif args.action == 'retry':
            if not args.sync_log_id:
                print("❌ --sync-log-id required for retry")
                return
            retry_failed_sync(args.sync_log_id)
            
        elif args.action == 'cleanup':
            cleanup_old_logs(args.days, args.dry_run)
            
        elif args.action == 'reset':
            if not args.invoice_id:
                print("❌ --invoice-id required for reset")
                return
            reset_invoice_sync_status(args.invoice_id)
            
        elif args.action == 'details':
            if not args.invoice_id:
                print("❌ --invoice-id required for details")
                return
            view_invoice_sync_details(args.invoice_id)
            
    except Exception as e:
        print(f"❌ Operation failed: {str(e)}")
        traceback.print_exc()
    
    finally:
        frappe.destroy()

if __name__ == "__main__":
    if len(sys.argv) == 1:
        # Interactive mode
        print("🔧 O2O ERPNext Manual Sync Utilities - Interactive Mode")
        print("=" * 60)
        
        if not initialize_frappe():
            sys.exit(1)
        
        try:
            while True:
                print("\n📋 Available Operations:")
                print("1. Test external connection")
                print("2. Check sync status")
                print("3. List pending syncs")
                print("4. List failed syncs")
                print("5. Sync specific invoice to external")
                print("6. Sync from external (batch)")
                print("7. View invoice sync details")
                print("8. Reset invoice sync status")
                print("9. Cleanup old logs")
                print("0. Exit")
                
                choice = input("\nEnter your choice (0-9): ").strip()
                
                if choice == '0':
                    break
                elif choice == '1':
                    test_external_connection()
                elif choice == '2':
                    check_sync_status()
                elif choice == '3':
                    list_pending_syncs()
                elif choice == '4':
                    list_failed_syncs()
                elif choice == '5':
                    invoice_id = input("Enter invoice ID: ").strip()
                    if invoice_id:
                        manual_sync_invoice_to_external(invoice_id)
                elif choice == '6':
                    limit = input("Enter limit (default 10): ").strip()
                    limit = int(limit) if limit.isdigit() else 10
                    manual_sync_from_external(limit)
                elif choice == '7':
                    invoice_id = input("Enter invoice ID: ").strip()
                    if invoice_id:
                        view_invoice_sync_details(invoice_id)
                elif choice == '8':
                    invoice_id = input("Enter invoice ID: ").strip()
                    if invoice_id:
                        reset_invoice_sync_status(invoice_id)
                elif choice == '9':
                    days = input("Enter days (default 30): ").strip()
                    days = int(days) if days.isdigit() else 30
                    dry_run = input("Dry run? (y/n, default y): ").strip().lower()
                    dry_run = dry_run != 'n'
                    cleanup_old_logs(days, dry_run)
                else:
                    print("❌ Invalid choice. Please try again.")
                    
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
        except Exception as e:
            print(f"❌ Error: {str(e)}")
        finally:
            frappe.destroy()
    else:
        # Command line mode
        main()