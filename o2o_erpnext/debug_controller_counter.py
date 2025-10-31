#!/usr/bin/env python3

import frappe
from o2o_erpnext.config.external_db_updated import get_external_db_connection

def check_counter_and_controller():
    """
    Check current counter status and test if our controller override is working
    """
    print("🔍 DEBUGGING CONTROLLER AND COUNTER INTEGRATION")
    print("=" * 60)
    
    # 1. Check current counter status
    try:
        with get_external_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM invoice_counter WHERE id = 1")
                counter = cursor.fetchone()
                
                if counter:
                    print(f"1️⃣ Current Counter Status:")
                    print(f"   Last Number: {counter['last_number']}")
                    print(f"   Updated: {counter['updated_at']}")
                    print(f"   Next Expected: AGO2O/25-26/{counter['last_number'] + 1:04d}")
                else:
                    print("1️⃣ No counter found!")
                    
    except Exception as e:
        print(f"1️⃣ Counter Check Failed: {e}")
    
    # 2. Check if our controller is registered
    try:
        from o2o_erpnext.o2o_erpnext.hooks import override_doctype_class
        
        print(f"\n2️⃣ Controller Override Configuration:")
        pi_override = override_doctype_class.get('Purchase Invoice')
        print(f"   Purchase Invoice Override: {pi_override}")
        
        if pi_override:
            print(f"   ✅ Controller override is configured")
        else:
            print(f"   ❌ No controller override found")
            
    except Exception as e:
        print(f"2️⃣ Controller Check Failed: {e}")
    
    # 3. Test the actual controller class being used
    try:
        print(f"\n3️⃣ Testing Controller Class:")
        
        # Check what class ERPNext is actually using
        import frappe.model.document as doc_module
        pi_class = doc_module.get_controller('Purchase Invoice')
        
        print(f"   Current Controller Class: {pi_class}")
        print(f"   Module Path: {pi_class.__module__}")
        
        # Check if it has our autoname method
        if hasattr(pi_class, 'autoname'):
            print(f"   ✅ Has autoname method")
            
            # Check the method source
            import inspect
            autoname_source = inspect.getsource(pi_class.autoname)
            if 'RemoteInvoiceCreator' in autoname_source:
                print(f"   ✅ autoname method contains RemoteInvoiceCreator")
            else:
                print(f"   ❌ autoname method does not use RemoteInvoiceCreator")
        else:
            print(f"   ❌ No autoname method found")
            
    except Exception as e:
        print(f"3️⃣ Controller Test Failed: {e}")
    
    # 4. Test the remote counter function directly
    try:
        print(f"\n4️⃣ Testing Remote Counter Function:")
        
        from o2o_erpnext.api.remote_invoice_creator import RemoteInvoiceCreator
        creator = RemoteInvoiceCreator()
        
        # Don't actually call it, just check if it's importable
        print(f"   ✅ RemoteInvoiceCreator imported successfully")
        print(f"   Method available: {hasattr(creator, 'get_next_invoice_code')}")
        
    except Exception as e:
        print(f"4️⃣ Remote Counter Test Failed: {e}")
    
    # 5. Check ERPNext naming series configuration
    try:
        print(f"\n5️⃣ ERPNext Naming Configuration:")
        
        # Check Purchase Invoice DocType naming configuration
        pi_meta = frappe.get_meta('Purchase Invoice')
        print(f"   DocType autoname: {pi_meta.autoname}")
        
        # Check if there are any naming series defined
        naming_series_field = None
        for field in pi_meta.fields:
            if field.fieldname == 'naming_series':
                naming_series_field = field
                break
        
        if naming_series_field:
            print(f"   ❌ naming_series field exists: {naming_series_field.options}")
            print(f"   This might be conflicting with autoname!")
        else:
            print(f"   ✅ No naming_series field found")
            
    except Exception as e:
        print(f"5️⃣ Naming Configuration Check Failed: {e}")

if __name__ == "__main__":
    check_counter_and_controller()