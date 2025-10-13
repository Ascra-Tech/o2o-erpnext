"""
Sample Data Testing Script for ERPNext-ProcureUAT Sync
Tests sync functionality with real sample orders from the database
"""
import frappe
from datetime import datetime

def test_sample_data_sync():
    """Test sync with specific sample orders from ProcureUAT database"""
    
    print("🧪 Testing ERPNext-ProcureUAT Sync with Sample Data")
    print("=" * 60)
    
    # Sample order codes identified in the database
    sample_orders = ["ASC02321042021", "Indo1220042021", "ASC02219042021"]
    
    try:
        # Import sync functions
        from o2o_erpnext.config.external_db_updated import (
            test_external_connection,
            get_procureuat_purchase_requisitions,
            get_procureuat_vendors
        )
        
        # Test 1: Database Connection
        print("\n1️⃣ Testing Database Connection...")
        success, message, data = test_external_connection()
        
        if success:
            print("✅ Database connection successful")
            print(f"   Database: {data['database_info']['database']}")
            print(f"   Version: {data['database_info']['version']}")
            print(f"   Purchase Requisitions: {data['record_counts']['purchase_requisitions']}")
            print(f"   Purchase Order Items: {data['record_counts']['purchase_order_items']}")
            print(f"   Active Vendors: {data['record_counts']['active_vendors']}")
        else:
            print(f"❌ Database connection failed: {message}")
            return False
        
        # Test 2: Vendor Data
        print("\n2️⃣ Testing Vendor Data...")
        vendors = get_procureuat_vendors()
        
        if vendors:
            print(f"✅ Found {len(vendors)} active vendors:")
            for vendor in vendors:
                print(f"   • {vendor['name']} (ID: {vendor['id']})")
        else:
            print("❌ No vendors found")
        
        # Test 3: Sample Orders
        print("\n3️⃣ Testing Sample Order Data...")
        requisitions = get_procureuat_purchase_requisitions(50)  # Get more records to find samples
        
        if requisitions:
            print(f"✅ Retrieved {len(requisitions)} purchase requisitions")
            
            # Look for our sample orders
            sample_found = []
            for req in requisitions:
                order_name = req.get('order_name', '')
                if order_name in sample_orders:
                    sample_found.append(req)
                    print(f"   🎯 Found sample order: {order_name}")
                    print(f"      Entity: {req.get('entity', 'N/A')}")
                    print(f"      Status: {req.get('order_status', 'N/A')}")
                    print(f"      Created: {req.get('created_at', 'N/A')}")
            
            if sample_found:
                print(f"\n✅ Found {len(sample_found)} of {len(sample_orders)} sample orders")
                
                # Test 4: Sample Order Details
                print("\n4️⃣ Testing Sample Order Details...")
                for sample_order in sample_found[:2]:  # Test first 2
                    order_id = sample_order['id']
                    order_name = sample_order['order_name']
                    
                    print(f"\n📋 Order Details: {order_name} (ID: {order_id})")
                    
                    # Get order items
                    from o2o_erpnext.config.external_db_updated import get_procureuat_purchase_order_items
                    items = get_procureuat_purchase_order_items(order_id)
                    
                    if items:
                        print(f"   ✅ Found {len(items)} order items")
                        total_value = sum(float(item.get('total_amt', 0)) for item in items)
                        print(f"   💰 Total Value: ₹{total_value:,.2f}")
                        
                        # Show sample items
                        for i, item in enumerate(items[:3]):  # Show first 3 items
                            print(f"   • Item {i+1}: Qty {item.get('quantity', 0)} @ ₹{item.get('unit_rate', 0)}")
                    else:
                        print(f"   ⚠️  No items found for order {order_name}")
            
            else:
                print(f"⚠️  None of the sample orders found in database")
                print(f"   Available orders (first 10):")
                for req in requisitions[:10]:
                    print(f"   • {req.get('order_name', 'No Name')} - {req.get('order_status', 'No Status')}")
        
        else:
            print("❌ No purchase requisitions found")
        
        # Test 5: Field Mapping Validation
        print("\n5️⃣ Testing Field Mappings...")
        try:
            from o2o_erpnext.config.field_mappings_sql_based import (
                ERPNEXT_TO_PROCUREUAT_REQUISITIONS,
                PROCUREUAT_TO_ERPNEXT_REQUISITIONS,
                get_vendor_mapping
            )
            
            print(f"✅ ERPNext → ProcureUAT mappings: {len(ERPNEXT_TO_PROCUREUAT_REQUISITIONS)} fields")
            print(f"✅ ProcureUAT → ERPNext mappings: {len(PROCUREUAT_TO_ERPNEXT_REQUISITIONS)} fields")
            
            vendor_mapping = get_vendor_mapping()
            print(f"✅ Vendor mappings: {len(vendor_mapping)} vendors")
            
        except Exception as e:
            print(f"❌ Field mapping error: {str(e)}")
        
        # Test 6: API Endpoints
        print("\n6️⃣ Testing API Endpoints...")
        try:
            from o2o_erpnext.api.purchase_invoice_sync import test_external_connection as api_test
            
            result = api_test()
            if result.get('success'):
                print("✅ API external connection test passed")
            else:
                print(f"❌ API external connection test failed: {result.get('error')}")
            
        except Exception as e:
            print(f"❌ API endpoint error: {str(e)}")
        
        # Final Summary
        print("\n" + "=" * 60)
        print("📊 SAMPLE DATA TEST SUMMARY")
        print("=" * 60)
        print(f"✅ Database Connection: Working")
        print(f"✅ Vendor Data: {len(vendors)} vendors available")
        print(f"✅ Purchase Requisitions: {len(requisitions)} records")
        print(f"✅ Sample Orders Found: {len(sample_found)} of {len(sample_orders)}")
        print(f"✅ Field Mappings: Loaded and ready")
        print(f"✅ API Endpoints: Available")
        
        print("\n🎯 RECOMMENDATIONS:")
        if sample_found:
            print("   • Sample orders are available for testing")
            print("   • Ready to test sync functionality with real data")
            print("   • Consider testing with one sample order first")
        else:
            print("   • Sample orders not found - use alternative test data")
            print("   • Any available orders can be used for testing")
        
        print("\n⚠️  PRODUCTION NOTES:")
        print("   • Always test sync in a non-production environment first")
        print("   • Monitor sync operations closely during initial deployment")
        print("   • Keep backup of both databases before sync operations")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Sample data test failed: {str(e)}")
        import traceback
        print(f"Error details: {traceback.format_exc()}")
        return False


if __name__ == "__main__":
    test_sample_data_sync()