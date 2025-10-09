#!/usr/bin/env python3
"""
Database Connection Test Command for O2O ERPNext
"""

import click
import frappe
import pymysql
from sshtunnel import SSHTunnelForwarder
import json

@click.command()
@click.option('--site', default='all', help='Site to run test on')
def test_db_connection(site):
    """Test database connection to ProcureUAT"""
    
    if site == 'all':
        sites = frappe.get_all_sites()
        if sites:
            site = sites[0]  # Use first available site
        else:
            click.echo("No sites found!")
            return
    
    # Initialize Frappe for the site
    frappe.init(site=site)
    frappe.connect()
    
    click.echo(f"Testing database connection for site: {site}")
    click.echo("=" * 50)
    
    # Test 1: Direct Database Connection
    click.echo("\n1. Testing Direct Database Connection...")
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
            cursor.execute("SELECT VERSION() as version, DATABASE() as database, USER() as user")
            result = cursor.fetchone()
            click.echo(f"✅ Direct connection successful!")
            click.echo(f"   MySQL Version: {result['version']}")
            click.echo(f"   Database: {result['database']}")
            click.echo(f"   User: {result['user']}")
            
            # Test table access
            cursor.execute("SHOW TABLES LIKE 'purchase_invoices'")
            table_exists = cursor.fetchone()
            if table_exists:
                click.echo(f"✅ purchase_invoices table found")
                cursor.execute("SELECT COUNT(*) as count FROM purchase_invoices")
                count = cursor.fetchone()
                click.echo(f"   Records in purchase_invoices: {count['count']}")
            else:
                click.echo(f"❌ purchase_invoices table not found")
        
        connection.close()
        
    except Exception as e:
        click.echo(f"❌ Direct connection failed: {str(e)}")
    
    # Test 2: SSH Tunnel Connection
    click.echo("\n2. Testing SSH Tunnel Connection...")
    try:
        # Check if SSH key exists
        ssh_key_path = '/home/erpnext/frappe-bench/o2o-uat-lightsail.pem'
        import os
        if not os.path.exists(ssh_key_path):
            click.echo(f"❌ SSH key not found at {ssh_key_path}")
        else:
            click.echo(f"✅ SSH key found at {ssh_key_path}")
            
            with SSHTunnelForwarder(
                ('65.0.222.210', 22),
                ssh_username='ubuntu',
                ssh_pkey=ssh_key_path,
                remote_bind_address=('127.0.0.1', 3306),
                local_bind_address=('127.0.0.1', 0)  # Use random local port
            ) as tunnel:
                tunnel.start()
                click.echo(f"✅ SSH tunnel established on local port {tunnel.local_bind_port}")
                
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
                    cursor.execute("SELECT VERSION() as version")
                    result = cursor.fetchone()
                    click.echo(f"✅ SSH tunnel connection successful!")
                    click.echo(f"   MySQL Version: {result['version']}")
                
                connection.close()
                
    except Exception as e:
        click.echo(f"❌ SSH tunnel connection failed: {str(e)}")
    
    # Test 3: Check Frappe Database Connection Record
    click.echo("\n3. Testing Frappe Database Connection Record...")
    try:
        if frappe.db.exists("Database Connection", "ProcureUAT"):
            doc = frappe.get_doc("Database Connection", "ProcureUAT")
            click.echo(f"✅ Database Connection record 'ProcureUAT' exists")
            click.echo(f"   Host: {doc.host}")
            click.echo(f"   Port: {doc.port}")
            click.echo(f"   Database: {doc.database_name}")
            click.echo(f"   Username: {doc.username}")
        else:
            click.echo(f"❌ Database Connection record 'ProcureUAT' not found")
            
            # Create the record
            click.echo("   Creating Database Connection record...")
            doc = frappe.new_doc("Database Connection")
            doc.connection_name = "ProcureUAT"
            doc.host = "65.0.222.210"
            doc.port = 3306
            doc.database_name = "procureuat"
            doc.username = "frappeo2o"
            doc.password = "Reppyq-pijry0-fyktyq"
            doc.save()
            frappe.db.commit()
            click.echo("✅ Database Connection record created successfully")
            
    except Exception as e:
        click.echo(f"❌ Frappe Database Connection test failed: {str(e)}")
    
    # Test 4: Check O2O ERPNext App Installation
    click.echo("\n4. Testing O2O ERPNext App Installation...")
    try:
        if "o2o_erpnext" in frappe.get_installed_apps():
            click.echo("✅ O2O ERPNext app is installed")
            
            # Check if Invoice Sync Log doctype exists
            if frappe.db.exists("DocType", "Invoice Sync Log"):
                click.echo("✅ Invoice Sync Log doctype exists")
                
                # Check for existing sync logs
                count = frappe.db.count("Invoice Sync Log")
                click.echo(f"   Existing sync logs: {count}")
            else:
                click.echo("❌ Invoice Sync Log doctype not found")
        else:
            click.echo("❌ O2O ERPNext app is not installed")
            
    except Exception as e:
        click.echo(f"❌ App installation test failed: {str(e)}")
    
    # Test 5: Check Custom Fields
    click.echo("\n5. Testing Custom Fields on Purchase Invoice...")
    try:
        meta = frappe.get_meta("Purchase Invoice")
        custom_fields = [
            'external_id', 'external_sync_status', 'external_last_sync',
            'external_sync_error', 'external_created_at', 'external_updated_at'
        ]
        
        existing_fields = [field.fieldname for field in meta.fields]
        
        for field in custom_fields:
            if field in existing_fields:
                click.echo(f"✅ Custom field '{field}' exists")
            else:
                click.echo(f"❌ Custom field '{field}' missing")
                
    except Exception as e:
        click.echo(f"❌ Custom fields test failed: {str(e)}")
    
    click.echo("\n" + "=" * 50)
    click.echo("Database connection test completed!")
    
    frappe.destroy()

commands = [test_db_connection]