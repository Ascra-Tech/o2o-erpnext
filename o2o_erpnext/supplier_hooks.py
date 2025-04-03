import frappe

def create_party_specific_item(doc, method):
    """
    Create a Party Specific Item record when a new Supplier is created
    """
    try:
        # Create a new Party Specific Item
        party_specific_item = frappe.new_doc("Party Specific Item")
        party_specific_item.party_type = "Supplier"
        party_specific_item.party = doc.name
        party_specific_item.restrict_based_on = "Item Group"
        
        # Check if "Default Item Group" exists
        if frappe.db.exists("Item Group", "Default Item Group"):
            party_specific_item.based_on_value = "Default Item Group"
        else:
            # Use the first available Item Group
            item_groups = frappe.get_all("Item Group", limit=1)
            if item_groups:
                party_specific_item.based_on_value = item_groups[0].name
            else:
                frappe.logger().error("No Item Groups found in the system")
                return
        
        # Save the document
        party_specific_item.insert(ignore_permissions=True)
        
        # Removed the msgprint line to prevent the popup
        
    except Exception as e:
        frappe.logger().error(f"Error creating Party Specific Item: {str(e)}")
        frappe.log_error(f"Error creating Party Specific Item: {str(e)}")