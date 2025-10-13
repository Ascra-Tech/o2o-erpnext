#!/usr/bin/env python3
"""
Test Script for SSH Tunnel Control Panel Setup
Run this script to verify the installation
"""

import os
import sys

def test_file_exists(filepath, description):
    """Test if a file exists"""
    if os.path.exists(filepath):
        print(f"✅ {description}: {filepath}")
        return True
    else:
        print(f"❌ {description} NOT FOUND: {filepath}")
        return False

def test_ssh_key_permissions(filepath):
    """Test SSH key file permissions"""
    if not os.path.exists(filepath):
        print(f"❌ SSH key file not found: {filepath}")
        return False
    
    file_stat = os.stat(filepath)
    permissions = oct(file_stat.st_mode)[-3:]
    
    if permissions == '600':
        print(f"✅ SSH key has correct permissions (600): {filepath}")
        return True
    else:
        print(f"⚠️  SSH key has incorrect permissions ({permissions}): {filepath}")
        print(f"   Run: chmod 600 {filepath}")
        return False

def main():
    print("=" * 70)
    print("SSH Tunnel Control Panel - Installation Verification")
    print("=" * 70)
    print()
    
    base_path = "/home/erpnext/frappe-bench/apps/o2o_erpnext/o2o_erpnext"
    
    # Test new files
    print("📁 Checking New Files:")
    print("-" * 70)
    
    tests = []
    
    tests.append(test_file_exists(
        f"{base_path}/config/ssh_tunnel_manager.py",
        "SSH Tunnel Manager"
    ))
    
    tests.append(test_file_exists(
        f"{base_path}/api/database_connection_api.py",
        "Database Connection API"
    ))
    
    tests.append(test_file_exists(
        f"{base_path}/install.py",
        "Installation Script"
    ))
    
    tests.append(test_file_exists(
        f"{base_path}/o2o_erpnext/doctype/database_connection/database_connection_list.js",
        "Database Connection List JS"
    ))
    
    print()
    
    # Test SSH key
    print("🔑 Checking SSH Key:")
    print("-" * 70)
    ssh_key_path = "/home/erpnext/frappe-bench/apps/o2o_erpnext/o2o-Research/o2o-uat-lightsail.pem"
    tests.append(test_file_exists(ssh_key_path, "SSH Key File"))
    tests.append(test_ssh_key_permissions(ssh_key_path))
    
    print()
    
    # Test hooks
    print("🔧 Checking Hooks Configuration:")
    print("-" * 70)
    hooks_file = f"{base_path}/hooks.py"
    if os.path.exists(hooks_file):
        with open(hooks_file, 'r') as f:
            hooks_content = f.read()
            if 'after_install = "o2o_erpnext.install.after_install"' in hooks_content:
                print("✅ after_install hook is configured")
                tests.append(True)
            else:
                print("❌ after_install hook NOT configured")
                tests.append(False)
    else:
        print("❌ hooks.py not found")
        tests.append(False)
    
    print()
    
    # Test DocType JSON
    print("📝 Checking DocType JSON:")
    print("-" * 70)
    doctype_json = f"{base_path}/o2o_erpnext/doctype/database_connection/database_connection.json"
    if os.path.exists(doctype_json):
        with open(doctype_json, 'r') as f:
            json_content = f.read()
            required_fields = ['ssh_host', 'ssh_port', 'ssh_username', 'ssh_key_file', 'tunnel_status']
            all_found = True
            for field in required_fields:
                if f'"fieldname": "{field}"' in json_content:
                    print(f"✅ Field '{field}' exists")
                else:
                    print(f"❌ Field '{field}' NOT found")
                    all_found = False
            tests.append(all_found)
    else:
        print("❌ database_connection.json not found")
        tests.append(False)
    
    print()
    
    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    total_tests = len(tests)
    passed_tests = sum(tests)
    
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    
    if all(tests):
        print()
        print("✅ ALL TESTS PASSED!")
        print()
        print("Next Steps:")
        print("1. Clear cache and restart: bench --site o2o.php clear-cache && bench restart")
        print("2. Navigate to Database Connection List")
        print("3. Fill in username/password for ProcureUAT connection")
        print("4. Click 'SSH Tunnel Control Panel' button")
        print("5. Start the tunnel and test the connection")
    else:
        print()
        print("❌ SOME TESTS FAILED")
        print("Please review the errors above and fix them before proceeding.")
    
    print()
    print("=" * 70)

if __name__ == "__main__":
    main()

