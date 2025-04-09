import frappe
from frappe import _

@frappe.whitelist()
def update_supplier_access(party_specific_item_name):
    """
    Updates the supplier access list in the Item based on Party Specific Item
    
    Args:
        party_specific_item_name (str): Name of the Party Specific Item document
        
    Returns:
        dict: Result of the operation
    """
    # Get the Party Specific Item document
    psi_doc = frappe.get_doc("Party Specific Item", party_specific_item_name)
    
    # Check if party_type is Supplier
    if psi_doc.party_type != "Supplier":
        frappe.msgprint(_("This function only works for Supplier type"))
        return {"success": False, "message": "Invalid party type"}
    
    supplier = psi_doc.party
    restrict_based_on = psi_doc.restrict_based_on
    based_on_value = psi_doc.based_on_value
    
    items_updated = 0
    items_skipped = 0
    
    try:
        # Get items based on restriction type
        if restrict_based_on == "Item":
            # Single item case - already implemented
            items = [{"item_code": based_on_value}]
            
        elif restrict_based_on == "Item Group":
            # Get all items belonging to this item group
            items = frappe.get_all("Item", 
                                  filters={
                                      "item_group": based_on_value,
                                      "disabled": 0  # Only active items
                                  }, 
                                  fields=["item_code"])
            
            # Also get items where custom_sub_category is this item group
            sub_category_items = frappe.get_all("Item",
                                              filters={
                                                  "custom_sub_category": based_on_value,
                                                  "disabled": 0
                                              },
                                              fields=["item_code"])
            
            # Combine both lists and remove duplicates
            item_codes_set = set([item.item_code for item in items])
            for item in sub_category_items:
                if item.item_code not in item_codes_set:
                    items.append(item)
                    
        elif restrict_based_on == "Brand":
            # Get all items belonging to this brand
            items = frappe.get_all("Item", 
                                  filters={
                                      "brand": based_on_value,
                                      "disabled": 0  # Only active items
                                  }, 
                                  fields=["item_code"])
        else:
            frappe.msgprint(_("Invalid restriction type"))
            return {"success": False, "message": "Invalid restriction type"}
        
        # If no items found
        if not items:
            frappe.msgprint(_("No items found for {0}: {1}").format(restrict_based_on, based_on_value))
            return {"success": False, "message": "No items found"}
        
        # Update supplier access for each item
        for item in items:
            try:
                item_code = item.get("item_code")
                item_doc = frappe.get_doc("Item", item_code)
                
                # Check if this supplier is already in the access list
                supplier_exists = False
                for access in item_doc.get("custom_supplier_access_list", []):
                    if access.supplier == supplier:
                        supplier_exists = True
                        break
                
                # If supplier doesn't exist in the list, add it
                if not supplier_exists:
                    item_doc.append("custom_supplier_access_list", {
                        "supplier": supplier
                    })
                    
                    # Save the Item document
                    item_doc.save(ignore_permissions=True)
                    items_updated += 1
                else:
                    items_skipped += 1
                    
            except Exception as e:
                frappe.log_error(frappe.get_traceback(), 
                                 _("Error updating supplier access for item {0}").format(item_code))
                items_skipped += 1
        
        # Show summary message
        if items_updated > 0:
            if restrict_based_on == "Item":
                frappe.msgprint(_("Supplier {0} has been added to access list for item {1}").format(
                    supplier, based_on_value))
            else:
                frappe.msgprint(_("Supplier {0} has been added to access list for {1} items. {2} items already had access.").format(
                    supplier, items_updated, items_skipped))
                
        else:
            frappe.msgprint(_("Supplier {0} already has access to all {1} items.").format(
                supplier, items_skipped))
            
        return {
            "success": True, 
            "message": f"Updated {items_updated} items, skipped {items_skipped} items",
            "updated": items_updated,
            "skipped": items_skipped
        }
            
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("Error updating supplier access list"))
        frappe.msgprint(_("Error updating supplier access list: {0}").format(str(e)), indicator="red")
        return {"success": False, "message": str(e)}