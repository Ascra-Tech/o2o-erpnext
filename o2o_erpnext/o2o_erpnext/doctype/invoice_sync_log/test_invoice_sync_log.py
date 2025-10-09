# Copyright (c) 2025, Ascratech LLP and Contributors
# See license.txt

import frappe
import unittest

class TestInvoiceSyncLog(unittest.TestCase):
	def setUp(self):
		# Create test data
		pass
	
	def test_create_sync_log(self):
		"""Test creation of sync log"""
		log = frappe.get_doc({
			"doctype": "Invoice Sync Log",
			"sync_direction": "ERPNext to ProcureUAT",
			"invoice_reference": "PINV-TEST-001",
			"sync_status": "Pending",
			"erpnext_invoice_id": "PINV-TEST-001"
		})
		log.insert()
		
		self.assertEqual(log.source_system, "ERPNext")
		self.assertEqual(log.target_system, "ProcureUAT")
		self.assertIsNotNone(log.sync_timestamp)
	
	def test_mark_success(self):
		"""Test marking sync as successful"""
		log = frappe.get_doc({
			"doctype": "Invoice Sync Log",
			"sync_direction": "ERPNext to ProcureUAT",
			"invoice_reference": "PINV-TEST-002",
			"sync_status": "Pending"
		})
		log.insert()
		
		log.mark_success("Sync completed successfully")
		
		self.assertEqual(log.sync_status, "Success")
		self.assertEqual(log.success_message, "Sync completed successfully")
	
	def test_mark_failed(self):
		"""Test marking sync as failed"""
		log = frappe.get_doc({
			"doctype": "Invoice Sync Log",
			"sync_direction": "ERPNext to ProcureUAT",
			"invoice_reference": "PINV-TEST-003",
			"sync_status": "Pending"
		})
		log.insert()
		
		log.mark_failed("Connection error", retry=True)
		
		self.assertEqual(log.sync_status, "Retry")
		self.assertEqual(log.error_message, "Connection error")
		self.assertEqual(log.retry_count, 1)
	
	def test_can_retry(self):
		"""Test retry logic"""
		log = frappe.get_doc({
			"doctype": "Invoice Sync Log",
			"sync_direction": "ERPNext to ProcureUAT",
			"invoice_reference": "PINV-TEST-004",
			"sync_status": "Failed",
			"retry_count": 2
		})
		log.insert()
		
		self.assertTrue(log.can_retry(max_retries=3))
		self.assertFalse(log.can_retry(max_retries=2))
	
	def tearDown(self):
		# Clean up test data
		frappe.db.sql("DELETE FROM `tabInvoice Sync Log` WHERE invoice_reference LIKE 'PINV-TEST-%'")