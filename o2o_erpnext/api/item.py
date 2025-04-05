import frappe

@frappe.whitelist()
def get_items_for_supplier(supplier):
    """
    Get all items that have the specified supplier in their supplier access list
    """
    # Get the actual child table field name and doctype from the Item doctype
    meta = frappe.get_meta("Item")
    supplier_access_field = None
    
    # Find the field that contains the supplier access list
    for field in meta.fields:
        if field.fieldname == "custom_supplier_access_list":
            supplier_access_field = field
            break
    
    if not supplier_access_field:
        frappe.log_error("Supplier access field not found in Item doctype")
        return []
    
    # Get items that have this supplier in their access list
    items = frappe.db.sql("""
        SELECT parent 
        FROM `tab{child_doctype}` 
        WHERE supplier = %s AND parenttype = 'Item'
    """.format(child_doctype=supplier_access_field.options), (supplier,), as_dict=True)
    
    return [item.parent for item in items]