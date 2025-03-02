import frappe
from frappe.utils.background_jobs import enqueue
from frappe.utils import now_datetime, get_first_day, get_last_day, add_months

def setup_monthly_budget_update():
    """
    Set up a scheduled job to update budgets for Branch doctype on the 1st of every month.
    This function should be called during app installation or setup.
    """
    if not frappe.db.exists("Scheduled Job Type", "Auto Update Branch Budget"):
        frappe.get_doc({
            "doctype": "Scheduled Job Type",
            "method": "o2o_erpnext.branch_update.update_all_branch_budgets",
            "frequency": "Monthly",
            "cron_format": "0 0 1 * *",  # At 00:00 on the 1st of every month
            "docstatus": 0,
            "name": "Auto Update Branch Budget"
        }).insert()
        frappe.db.commit()

def update_all_branch_budgets():
    """
    Update budgets for all branches.
    This function is called by the scheduler on the 1st of every month.
    """
    try:
        branches = frappe.get_all("Branch", fields=["name", "custom_auto_update_capex_budget", "custom_auto_update_opex_budget"])
        
        for branch in branches:
            try:
                branch_doc = frappe.get_doc("Branch", branch.name)
                
                # Update CAPEX budget if available
                if branch.custom_auto_update_capex_budget:
                    branch_doc.capex_budget = branch.custom_auto_update_capex_budget
                
                # Update OPEX budget if available
                if branch.custom_auto_update_opex_budget:
                    branch_doc.opex_budget = branch.custom_auto_update_opex_budget
                
                # Save the document
                branch_doc.save()
                
                frappe.logger().info(f"Successfully updated budgets for Branch: {branch.name}")
            except Exception as e:
                frappe.logger().error(f"Error updating Branch {branch.name}: {str(e)}")
        
        frappe.db.commit()
        frappe.logger().info("Branch budget auto-update completed successfully")
    except Exception as e:
        frappe.logger().error(f"Error in branch budget auto-update: {str(e)}")

def setup_monthly_sub_branch_budget_update():
    """
    Set up a scheduled job to update budgets for Sub Branch doctype on the 1st of every month.
    This function should be called during app installation or setup.
    """
    if not frappe.db.exists("Scheduled Job Type", "Auto Update Sub Branch Budget"):
        frappe.get_doc({
            "doctype": "Scheduled Job Type",
            "method": "o2o_erpnext.branch_update.update_all_sub_branch_budgets",
            "frequency": "Monthly",
            "cron_format": "0 0 1 * *",  # At 00:00 on the 1st of every month
            "docstatus": 0,
            "name": "Auto Update Sub Branch Budget"
        }).insert()
        frappe.db.commit()

def update_all_sub_branch_budgets():
    """
    Update budgets for all sub branches.
    This function is called by the scheduler on the 1st of every month.
    """
    try:
        sub_branches = frappe.get_all("Sub Branch", fields=["name", "custom_auto_update_capex_budget", "custom_auto_update_opex_budget"])
        
        for sub_branch in sub_branches:
            try:
                sub_branch_doc = frappe.get_doc("Sub Branch", sub_branch.name)
                
                # Update CAPEX budget if available
                if sub_branch.custom_auto_update_capex_budget:
                    sub_branch_doc.capex_budget = sub_branch.custom_auto_update_capex_budget
                
                # Update OPEX budget if available
                if sub_branch.custom_auto_update_opex_budget:
                    sub_branch_doc.opex_budget = sub_branch.custom_auto_update_opex_budget
                
                # Save the document
                sub_branch_doc.save()
                
                frappe.logger().info(f"Successfully updated budgets for Sub Branch: {sub_branch.name}")
            except Exception as e:
                frappe.logger().error(f"Error updating Sub Branch {sub_branch.name}: {str(e)}")
        
        frappe.db.commit()
        frappe.logger().info("Sub Branch budget auto-update completed successfully")
    except Exception as e:
        frappe.logger().error(f"Error in sub branch budget auto-update: {str(e)}")

@frappe.whitelist()
def manual_update_sub_branch_budgets():
    """
    Manually trigger the sub branch budget update process.
    Can be called from client-side or used for testing.
    """
    enqueue(update_all_sub_branch_budgets, queue="long", timeout=1500)
    return {"message": "Sub Branch budget update has been queued"}

def test_sub_branch_budget_update(sub_branch_name=None):
    """
    Test function to verify the budget update for a specific sub branch or all sub branches.
    For debugging purposes only.
    """
    if sub_branch_name:
        sub_branch = frappe.get_doc("Sub Branch", sub_branch_name)
        print(f"Before update - CAPEX: {sub_branch.capex_budget}, OPEX: {sub_branch.opex_budget}")
        
        if sub_branch.custom_auto_update_capex_budget:
            sub_branch.capex_budget = sub_branch.custom_auto_update_capex_budget
            
        if sub_branch.custom_auto_update_opex_budget:
            sub_branch.opex_budget = sub_branch.custom_auto_update_opex_budget
            
        sub_branch.save()
        
        # Reload and verify
        sub_branch.reload()
        print(f"After update - CAPEX: {sub_branch.capex_budget}, OPEX: {sub_branch.opex_budget}")
    else:
        # Test for all sub branches
        update_all_sub_branch_budgets()
        print("Test completed for all sub branches")

# Function to setup both branch and sub branch scheduled jobs
def setup_all_budget_updates():
    """
    Set up scheduled jobs for both Branch and Sub Branch budget updates.
    """
    setup_monthly_budget_update()
    setup_monthly_sub_branch_budget_update()
    return "All budget update scheduled jobs have been set up."