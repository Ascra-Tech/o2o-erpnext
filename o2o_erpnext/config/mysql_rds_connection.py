"""
MySQL RDS Connection Module with IAM Authentication
For production o2oproddb MySQL RDS instance
"""

import frappe
import pymysql
import boto3
from contextlib import contextmanager
import os

def get_rds_auth_token():
    """
    Generate RDS authentication token using IAM
    """
    try:
        # Create RDS client
        rds_client = boto3.client('rds', region_name='ap-south-1')
        
        # Generate auth token
        token = rds_client.generate_db_auth_token(
            DBHostname='o2oproddb.cwjwq8yhqpn1.ap-south-1.rds.amazonaws.com',
            Port=3306,
            DBUsername='o2o_erpnext_user'
        )
        
        return token
        
    except Exception as e:
        frappe.logger().error(f"Failed to generate RDS auth token: {str(e)}")
        raise

@contextmanager
def get_mysql_rds_connection_with_iam():
    """
    Connect to MySQL RDS using IAM authentication and SSL
    """
    connection = None
    
    try:
        # Get IAM auth token
        auth_token = get_rds_auth_token()
        
        # SSL configuration
        ssl_config = {
            'ca': '/home/erpnext/frappe-bench/apps/o2o_erpnext/ssl/ap-south-1-bundle.pem'
        }
        
        # Create connection
        connection = pymysql.connect(
            host='o2oproddb.cwjwq8yhqpn1.ap-south-1.rds.amazonaws.com',
            port=3306,
            user='o2o_erpnext_user',
            password=auth_token,
            database='procureuat',
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            ssl=ssl_config,
            connect_timeout=30,
            read_timeout=30,
            write_timeout=30,
            autocommit=False
        )
        
        frappe.logger().info("Connected to MySQL RDS with IAM authentication")
        yield connection
        
    except Exception as e:
        frappe.logger().error(f"MySQL RDS IAM connection failed: {str(e)}")
        raise
    finally:
        if connection:
            connection.close()

@contextmanager
def get_mysql_rds_connection_with_password(username, password):
    """
    Connect to MySQL RDS using username/password authentication and SSL
    For initial setup and database user creation
    """
    connection = None
    
    try:
        # SSL configuration
        ssl_config = {
            'ca': '/home/erpnext/frappe-bench/apps/o2o_erpnext/ssl/ap-south-1-bundle.pem'
        }
        
        # Create connection
        connection = pymysql.connect(
            host='o2oproddb.cwjwq8yhqpn1.ap-south-1.rds.amazonaws.com',
            port=3306,
            user=username,
            password=password,
            database='procureuat',
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            ssl=ssl_config,
            connect_timeout=30,
            read_timeout=30,
            write_timeout=30,
            autocommit=False
        )
        
        frappe.logger().info(f"Connected to MySQL RDS with password authentication as {username}")
        yield connection
        
    except Exception as e:
        frappe.logger().error(f"MySQL RDS password connection failed: {str(e)}")
        raise
    finally:
        if connection:
            connection.close()

def create_iam_database_user(admin_username, admin_password):
    """
    Create IAM database user in MySQL RDS
    This should be run once during setup
    """
    try:
        with get_mysql_rds_connection_with_password(admin_username, admin_password) as conn:
            with conn.cursor() as cursor:
                # Create user for IAM authentication
                cursor.execute("CREATE USER IF NOT EXISTS 'o2o_erpnext_user'@'%' IDENTIFIED WITH AWSAuthenticationPlugin AS 'RDS'")
                
                # Grant permissions to procureuat database
                cursor.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON procureuat.* TO 'o2o_erpnext_user'@'%'")
                
                # Grant connection permissions
                cursor.execute("GRANT USAGE ON *.* TO 'o2o_erpnext_user'@'%'")
                
                # Apply changes
                cursor.execute("FLUSH PRIVILEGES")
                
                # Verify user creation
                cursor.execute("SELECT user, host, plugin FROM mysql.user WHERE user = 'o2o_erpnext_user'")
                result = cursor.fetchone()
                
                conn.commit()
                
                frappe.logger().info(f"Created IAM database user: {result}")
                return {
                    'success': True,
                    'message': 'IAM database user created successfully',
                    'user_info': result
                }
                
    except Exception as e:
        frappe.logger().error(f"Failed to create IAM database user: {str(e)}")
        return {
            'success': False,
            'message': f'Failed to create IAM database user: {str(e)}'
        }

def test_iam_connection():
    """
    Test IAM authentication connection
    """
    try:
        with get_mysql_rds_connection_with_iam() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT DATABASE() as db_name, USER() as user_name, VERSION() as version")
                result = cursor.fetchone()
                
                frappe.logger().info(f"IAM connection test successful: {result}")
                return {
                    'success': True,
                    'message': 'IAM connection test successful',
                    'connection_info': result
                }
                
    except Exception as e:
        frappe.logger().error(f"IAM connection test failed: {str(e)}")
        return {
            'success': False,
            'message': f'IAM connection test failed: {str(e)}'
        }
