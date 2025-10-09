#!/usr/bin/env python3
"""
SSH Diagnostic Script to check services on remote server
"""

import paramiko
import os

def ssh_diagnostic():
    """Connect via SSH and run diagnostic commands"""
    
    print("SSH Diagnostic for o2o-uat-lightsail server")
    print("=" * 50)
    
    ssh_key_path = '/home/erpnext/frappe-bench/apps/o2o_erpnext/o2o Research/o2o-uat-lightsail.pem'
    
    if not os.path.exists(ssh_key_path):
        print(f"❌ SSH key not found at {ssh_key_path}")
        return
    
    try:
        # Create SSH client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddHostPolicy())
        
        # Load private key
        private_key = paramiko.RSAKey.from_private_key_file(ssh_key_path)
        
        # Connect
        print("Connecting to 65.0.222.210 via SSH...")
        ssh.connect(
            hostname='65.0.222.210',
            username='ubuntu',
            pkey=private_key,
            timeout=30
        )
        print("✅ SSH connection successful!")
        
        # Run diagnostic commands
        commands = [
            ("Check MySQL service status", "sudo systemctl status mysql"),
            ("Check MySQL process", "ps aux | grep mysql"),
            ("Check listening ports", "sudo netstat -tlnp | grep :3306"),
            ("Check MySQL configuration", "sudo cat /etc/mysql/mysql.conf.d/mysqld.cnf | grep bind-address"),
            ("Check if MySQL is installed", "which mysql mysqld"),
            ("Check MariaDB service (alternative)", "sudo systemctl status mariadb"),
            ("Check all listening ports", "sudo netstat -tlnp"),
            ("Check system information", "uname -a"),
            ("Check available databases", "sudo mysql -e 'SHOW DATABASES;'")
        ]
        
        for description, command in commands:
            print(f"\n📋 {description}:")
            print(f"   Command: {command}")
            try:
                stdin, stdout, stderr = ssh.exec_command(command, timeout=30)
                output = stdout.read().decode().strip()
                error = stderr.read().decode().strip()
                
                if output:
                    print(f"   Output:\n{output}")
                if error:
                    print(f"   Error:\n{error}")
                    
            except Exception as e:
                print(f"   ❌ Failed to execute: {str(e)}")
        
        ssh.close()
        print("\n✅ SSH diagnostic completed!")
        
    except Exception as e:
        print(f"❌ SSH connection failed: {str(e)}")

if __name__ == "__main__":
    ssh_diagnostic()