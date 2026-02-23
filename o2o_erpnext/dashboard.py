#!/usr/bin/env python3

import frappe
from frappe import _
from frappe.utils import flt, formatdate, format_time
import json

@frappe.whitelist()
def get_workflow_states():
    """Get all available workflow states from Purchase Order workflow configuration"""
    try:
        # First get states from actual Purchase Orders
        po_states = frappe.db.sql("""
            SELECT DISTINCT workflow_state 
            FROM `tabPurchase Order` 
            WHERE workflow_state IS NOT NULL 
            AND workflow_state != ''
            ORDER BY workflow_state
        """, as_dict=True)
        
        existing_states = [state.workflow_state for state in po_states if state.workflow_state]
        
        # Also get all possible states from workflow configuration
        try:
            workflow_doc = frappe.get_doc("Workflow", "Purchase Order")
            workflow_states = [state.state for state in workflow_doc.states]
            
            # Combine both lists and remove duplicates
            all_states = list(set(existing_states + workflow_states))
            all_states.sort()
            
            return all_states
        except:
            # If workflow configuration is not accessible, return existing states
            return existing_states
            
    except Exception as e:
        frappe.log_error(f"Error fetching workflow states: {str(e)}")
        return []

@frappe.whitelist()
def get_po_dashboard_data(workflow_state, filters=None):
    """Get Purchase Order dashboard data for a specific workflow state with advanced filtering"""
    try:
        # Base query conditions
        conditions = ["workflow_state = %s"]
        values = [workflow_state]
        
        # Apply additional filters if provided
        if filters:
            filters = frappe.parse_json(filters) if isinstance(filters, str) else filters
            
            if filters.get('supplier'):
                conditions.append("supplier LIKE %s")
                values.append(f"%{filters['supplier']}%")
            
            if filters.get('branch'):
                conditions.append("custom_branch = %s")
                values.append(filters['branch'])
            
            if filters.get('date_range'):
                date_range = filters['date_range']
                if date_range.get('from_date'):
                    conditions.append("transaction_date >= %s")
                    values.append(date_range['from_date'])
                if date_range.get('to_date'):
                    conditions.append("transaction_date <= %s")
                    values.append(date_range['to_date'])
            
            if filters.get('amount_range'):
                amount_range = filters['amount_range']
                if amount_range.get('min_amount'):
                    conditions.append("grand_total >= %s")
                    values.append(amount_range['min_amount'])
                if amount_range.get('max_amount'):
                    conditions.append("grand_total <= %s")
                    values.append(amount_range['max_amount'])
        
        # Fetch Purchase Orders with the selected workflow state and filters
        purchase_orders = frappe.db.sql(f"""
            SELECT 
                name, supplier, transaction_date, grand_total, 
                workflow_state, status, company, currency,
                net_total, total_taxes_and_charges, custom_sub_branch,
                custom_vendor, custom_purchase_receipt, creation,
                modified, owner, custom_branch,
                custom__approved_at, custom_created_user, custom_created_by,
                per_billed, per_received, advance_paid, schedule_date,
                supplier_name, order_confirmation_no, order_confirmation_date
            FROM `tabPurchase Order`
            WHERE {' AND '.join(conditions)}
            ORDER BY transaction_date DESC
            LIMIT 200
        """, values, as_dict=True)
        
        if not purchase_orders:
            return {
                'success': True,
                'data': {
                    'workflow_state': workflow_state,
                    'summary': {
                        'total_orders': 0,
                        'total_amount': 0,
                        'avg_amount': 0,
                        'unique_suppliers': 0
                    },
                    'purchase_orders': [],
                    'supplier_stats': {}
                },
                'message': f'No Purchase Orders found with workflow state: {workflow_state}'
            }
        
        # Calculate summary statistics
        total_orders = len(purchase_orders)
        total_amount = sum(flt(po.grand_total or 0) for po in purchase_orders)
        avg_amount = total_amount / total_orders if total_orders > 0 else 0
        
        # Group by supplier for statistics
        supplier_stats = {}
        for po in purchase_orders:
            supplier = po.supplier or 'Unknown'
            if supplier not in supplier_stats:
                supplier_stats[supplier] = {'count': 0, 'total': 0}
            supplier_stats[supplier]['count'] += 1
            supplier_stats[supplier]['total'] += flt(po.grand_total or 0)
        
        # Sort suppliers by total amount
        sorted_suppliers = sorted(
            supplier_stats.items(), 
            key=lambda x: x[1]['total'], 
            reverse=True
        )[:10]  # Top 10 suppliers
        
        # Format dates for display
        for po in purchase_orders:
            if po.transaction_date:
                po.formatted_date = formatdate(po.transaction_date)
            if po.creation:
                po.formatted_creation = formatdate(po.creation) + " " + format_time(po.creation)
        
        return {
            'success': True,
            'data': {
                'workflow_state': workflow_state,
                'summary': {
                    'total_orders': total_orders,
                    'total_amount': total_amount,
                    'avg_amount': avg_amount,
                    'unique_suppliers': len(supplier_stats)
                },
                'purchase_orders': purchase_orders,
                'supplier_stats': dict(sorted_suppliers)
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Error fetching PO dashboard data: {str(e)}")
        return {
            'success': False,
            'message': f'Error loading dashboard data: {str(e)}'
        }

@frappe.whitelist()
def get_po_details(po_name):
    """Get detailed information for a specific Purchase Order"""
    try:
        po_doc = frappe.get_doc("Purchase Order", po_name)
        
        # Get items with tax details
        items_data = []
        for item in po_doc.items:
            item_data = {
                'item_code': item.item_code,
                'item_name': item.item_name,
                'qty': item.qty,
                'rate': item.rate,
                'amount': item.amount,
                'uom': item.uom,
                'cgst_amount': getattr(item, 'cgst_amount', 0) or 0,
                'sgst_amount': getattr(item, 'sgst_amount', 0) or 0,
                'igst_amount': getattr(item, 'igst_amount', 0) or 0
            }
            items_data.append(item_data)
        
        # Get tax details
        taxes_data = []
        if hasattr(po_doc, 'taxes') and po_doc.taxes:
            for tax in po_doc.taxes:
                tax_data = {
                    'account_head': tax.account_head,
                    'rate': tax.rate,
                    'tax_amount': tax.tax_amount,
                    'total': tax.total
                }
                taxes_data.append(tax_data)
        
        return {
            'success': True,
            'data': {
                'basic_info': {
                    'name': po_doc.name,
                    'supplier': po_doc.supplier,
                    'transaction_date': po_doc.transaction_date,
                    'grand_total': po_doc.grand_total,
                    'net_total': po_doc.net_total,
                    'total_taxes_and_charges': po_doc.total_taxes_and_charges,
                    'workflow_state': po_doc.workflow_state,
                    'status': po_doc.status,
                    'company': po_doc.company,
                    'currency': po_doc.currency,
                    'custom_sub_branch': getattr(po_doc, 'custom_sub_branch', ''),
                    'custom_vendor': getattr(po_doc, 'custom_vendor', ''),
                    'custom_purchase_receipt': getattr(po_doc, 'custom_purchase_receipt', '')
                },
                'items': items_data,
                'taxes': taxes_data
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Error fetching PO details: {str(e)}")
        return {
            'success': False,
            'message': f'Error loading PO details: {str(e)}'
        }

@frappe.whitelist()
def get_dashboard_summary():
    """Get overall Purchase Order dashboard summary"""
    try:
        # Get counts by workflow state
        workflow_summary = frappe.db.sql("""
            SELECT 
                workflow_state,
                COUNT(*) as count,
                SUM(grand_total) as total_amount
            FROM `tabPurchase Order`
            WHERE workflow_state IS NOT NULL 
            AND workflow_state != ''
            GROUP BY workflow_state
            ORDER BY count DESC
        """, as_dict=True)
        
        # Get recent activity
        recent_pos = frappe.db.sql("""
            SELECT 
                name, supplier, transaction_date, grand_total, 
                workflow_state, status
            FROM `tabPurchase Order`
            ORDER BY creation DESC
            LIMIT 10
        """, as_dict=True)
        
        return {
            'success': True,
            'data': {
                'workflow_summary': workflow_summary,
                'recent_activity': recent_pos
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Error fetching dashboard summary: {str(e)}")
        return {
            'success': False,
            'message': f'Error loading dashboard summary: {str(e)}'
        }

@frappe.whitelist()
def get_workflow_actions(po_name):
    """Get available workflow actions for a Purchase Order"""
    try:
        from frappe.model.workflow import get_transitions
        
        po_doc = frappe.get_doc("Purchase Order", po_name)
        transitions = get_transitions(po_doc)
        
        return {
            'success': True,
            'data': {
                'transitions': transitions,
                'current_state': po_doc.workflow_state,
                'can_edit': po_doc.has_permission('write')
            }
        }
    except Exception as e:
        frappe.log_error(f"Error fetching workflow actions: {str(e)}")
        return {
            'success': False,
            'message': f'Error loading workflow actions: {str(e)}'
        }

@frappe.whitelist()
def apply_workflow_action(po_name, action):
    """Apply workflow action to a Purchase Order"""
    try:
        from frappe.model.workflow import apply_workflow, get_transitions
        
        po_doc = frappe.get_doc("Purchase Order", po_name)
        
        # First check if the action is available for this PO
        available_transitions = get_transitions(po_doc)
        available_actions = [t.get('action') for t in available_transitions]
        
        if action not in available_actions:
            return {
                'success': False,
                'message': f'Action "{action}" is not available for this Purchase Order. Available actions: {", ".join(available_actions)}'
            }
        
        # Apply the workflow action
        result = apply_workflow(po_doc, action)
        
        return {
            'success': True,
            'message': f'Action "{action}" applied successfully',
            'data': {
                'new_state': result.workflow_state,
                'status': result.status
            }
        }
    except Exception as e:
        frappe.log_error(f"Error applying workflow action: {str(e)}")
        return {
            'success': False,
            'message': f'Error applying action: {str(e)}'
        }

@frappe.whitelist()
def bulk_workflow_action(po_names, action):
    """Apply workflow action to multiple Purchase Orders"""
    try:
        from frappe.model.workflow import bulk_workflow_approval
        
        po_names_list = frappe.parse_json(po_names) if isinstance(po_names, str) else po_names
        
        # Use Frappe's built-in bulk workflow approval
        bulk_workflow_approval(po_names_list, "Purchase Order", action)
        
        return {
            'success': True,
            'message': f'Bulk action "{action}" applied to {len(po_names_list)} Purchase Orders'
        }
    except Exception as e:
        frappe.log_error(f"Error in bulk workflow action: {str(e)}")
        return {
            'success': False,
            'message': f'Error in bulk action: {str(e)}'
        }

@frappe.whitelist()
def create_purchase_receipt(po_name):
    """Create Purchase Receipt from Purchase Order"""
    try:
        from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt
        
        pr_doc = make_purchase_receipt(po_name)
        pr_doc.save()
        
        return {
            'success': True,
            'message': f'Purchase Receipt {pr_doc.name} created successfully',
            'data': {
                'pr_name': pr_doc.name,
                'pr_url': f'/app/purchase-receipt/{pr_doc.name}'
            }
        }
    except Exception as e:
        frappe.log_error(f"Error creating Purchase Receipt: {str(e)}")
        return {
            'success': False,
            'message': f'Error creating Purchase Receipt: {str(e)}'
        }

@frappe.whitelist()
def create_purchase_invoice(po_name):
    """Create Purchase Invoice from Purchase Order"""
    try:
        from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_invoice
        
        pi_doc = make_purchase_invoice(po_name)
        pi_doc.save()
        
        return {
            'success': True,
            'message': f'Purchase Invoice {pi_doc.name} created successfully',
            'data': {
                'pi_name': pi_doc.name,
                'pi_url': f'/app/purchase-invoice/{pi_doc.name}'
            }
        }
    except Exception as e:
        frappe.log_error(f"Error creating Purchase Invoice: {str(e)}")
        return {
            'success': False,
            'message': f'Error creating Purchase Invoice: {str(e)}'
        }

@frappe.whitelist()
def get_dashboard_filters():
    """Get available filter options for dashboard"""
    try:
        # Get unique suppliers
        suppliers = frappe.db.sql("""
            SELECT DISTINCT supplier, supplier_name 
            FROM `tabPurchase Order` 
            WHERE supplier IS NOT NULL 
            ORDER BY supplier_name
        """, as_dict=True)
        
        # Get unique branches
        branches = frappe.db.sql("""
            SELECT DISTINCT custom_branch 
            FROM `tabPurchase Order` 
            WHERE custom_branch IS NOT NULL 
            ORDER BY custom_branch
        """, as_dict=True)
        
        # Get workflow states
        workflow_states = get_workflow_states()
        
        return {
            'success': True,
            'data': {
                'suppliers': suppliers,
                'branches': [b.custom_branch for b in branches],
                'workflow_states': workflow_states
            }
        }
    except Exception as e:
        frappe.log_error(f"Error fetching dashboard filters: {str(e)}")
        return {
            'success': False,
            'message': f'Error loading filters: {str(e)}'
        }
