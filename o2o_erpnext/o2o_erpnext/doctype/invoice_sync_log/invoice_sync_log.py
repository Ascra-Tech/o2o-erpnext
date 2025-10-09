# Copyright (c) 2025, Ascratech LLP and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, get_datetime
import json

class InvoiceSyncLog(Document):
	def before_insert(self):
		"""Set defaults before inserting"""
		if not self.sync_timestamp:
			self.sync_timestamp = now_datetime()
		
		if not self.retry_count:
			self.retry_count = 0
			
		if not self.sync_method:
			self.sync_method = "Automatic"
	
	def validate(self):
		"""Validate sync log data"""
		# Ensure sync direction matches source/target systems
		if self.sync_direction == "ERPNext to ProcureUAT":
			self.source_system = "ERPNext"
			self.target_system = "ProcureUAT"
		elif self.sync_direction == "ProcureUAT to ERPNext":
			self.source_system = "ProcureUAT"
			self.target_system = "ERPNext"
		
		# Validate invoice reference format
		if self.sync_direction == "ERPNext to ProcureUAT" and self.erpnext_invoice_id:
			self.invoice_reference = self.erpnext_invoice_id
		elif self.sync_direction == "ProcureUAT to ERPNext" and self.procureuat_invoice_id:
			self.invoice_reference = f"PROC-{self.procureuat_invoice_id}"
	
	def mark_success(self, success_message=None, target_data=None):
		"""Mark sync as successful"""
		self.sync_status = "Success"
		self.sync_timestamp = now_datetime()
		if success_message:
			self.success_message = success_message
		if target_data:
			self.target_data = json.dumps(target_data) if isinstance(target_data, dict) else target_data
		self.save(ignore_permissions=True)
		frappe.db.commit()
	
	def mark_failed(self, error_message, retry=False):
		"""Mark sync as failed"""
		self.sync_status = "Failed" if not retry else "Retry"
		self.sync_timestamp = now_datetime()
		self.error_message = error_message
		if retry:
			self.retry_count = (self.retry_count or 0) + 1
		self.save(ignore_permissions=True)
		frappe.db.commit()
	
	def mark_in_progress(self):
		"""Mark sync as in progress"""
		self.sync_status = "In Progress"
		self.sync_timestamp = now_datetime()
		self.save(ignore_permissions=True)
		frappe.db.commit()
	
	def can_retry(self, max_retries=3):
		"""Check if sync can be retried"""
		return (self.retry_count or 0) < max_retries and self.sync_status in ["Failed", "Retry"]
	
	@staticmethod
	def create_sync_log(sync_direction, invoice_reference, **kwargs):
		"""
		Create a new sync log entry
		
		Args:
			sync_direction: Direction of sync
			invoice_reference: Reference to the invoice
			**kwargs: Additional fields
			
		Returns:
			InvoiceSyncLog: Created sync log document
		"""
		log_doc = frappe.new_doc("Invoice Sync Log")
		log_doc.sync_direction = sync_direction
		log_doc.invoice_reference = invoice_reference
		
		# Set optional fields
		for key, value in kwargs.items():
			if hasattr(log_doc, key):
				setattr(log_doc, key, value)
		
		log_doc.insert(ignore_permissions=True)
		frappe.db.commit()
		return log_doc
	
	@staticmethod
	def get_existing_log(sync_direction, invoice_reference, sync_status=None):
		"""
		Get existing sync log for an invoice
		
		Args:
			sync_direction: Direction of sync
			invoice_reference: Reference to the invoice
			sync_status: Optional status filter
			
		Returns:
			InvoiceSyncLog or None: Existing log if found
		"""
		filters = {
			"sync_direction": sync_direction,
			"invoice_reference": invoice_reference
		}
		
		if sync_status:
			filters["sync_status"] = sync_status
		
		logs = frappe.get_all("Invoice Sync Log",
							 filters=filters,
							 order_by="creation desc",
							 limit=1)
		
		if logs:
			return frappe.get_doc("Invoice Sync Log", logs[0].name)
		return None
	
	@staticmethod
	def get_pending_syncs(sync_direction=None, limit=100):
		"""
		Get pending sync operations
		
		Args:
			sync_direction: Optional direction filter
			limit: Maximum number of records
			
		Returns:
			list: List of pending sync logs
		"""
		filters = {
			"sync_status": ["in", ["Pending", "Retry", "Failed"]]
		}
		
		if sync_direction:
			filters["sync_direction"] = sync_direction
		
		return frappe.get_all("Invoice Sync Log",
							 filters=filters,
							 fields=["name", "sync_direction", "invoice_reference", 
									"sync_status", "retry_count", "creation"],
							 order_by="creation asc",
							 limit=limit)
	
	@staticmethod
	def cleanup_old_logs(days=90):
		"""
		Clean up old successful sync logs
		
		Args:
			days: Number of days to keep logs
		"""
		from frappe.utils import add_days, nowdate
		
		cutoff_date = add_days(nowdate(), -days)
		
		frappe.db.sql("""
			DELETE FROM `tabInvoice Sync Log`
			WHERE sync_status = 'Success'
			AND DATE(creation) < %s
		""", cutoff_date)
		
		frappe.db.commit()
	
	@staticmethod
	def get_sync_statistics(from_date=None, to_date=None):
		"""
		Get sync statistics
		
		Args:
			from_date: Start date for statistics
			to_date: End date for statistics
			
		Returns:
			dict: Sync statistics
		"""
		filters = []
		if from_date:
			filters.append(f"DATE(creation) >= '{from_date}'")
		if to_date:
			filters.append(f"DATE(creation) <= '{to_date}'")
		
		where_clause = ""
		if filters:
			where_clause = "WHERE " + " AND ".join(filters)
		
		stats = frappe.db.sql(f"""
			SELECT 
				sync_direction,
				sync_status,
				COUNT(*) as count
			FROM `tabInvoice Sync Log`
			{where_clause}
			GROUP BY sync_direction, sync_status
		""", as_dict=True)
		
		# Organize statistics
		result = {
			"ERPNext to ProcureUAT": {"Success": 0, "Failed": 0, "Pending": 0, "Total": 0},
			"ProcureUAT to ERPNext": {"Success": 0, "Failed": 0, "Pending": 0, "Total": 0},
			"Overall": {"Success": 0, "Failed": 0, "Pending": 0, "Total": 0}
		}
		
		for stat in stats:
			direction = stat.sync_direction
			status = stat.sync_status
			count = stat.count
			
			# Map status
			if status in ["Success"]:
				status_key = "Success"
			elif status in ["Failed", "Retry"]:
				status_key = "Failed"
			else:
				status_key = "Pending"
			
			if direction in result:
				result[direction][status_key] += count
				result[direction]["Total"] += count
				result["Overall"][status_key] += count
				result["Overall"]["Total"] += count
		
		return result