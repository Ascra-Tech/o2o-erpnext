import frappe
from frappe import _

def format_address_details(address):
    """Format address details for display"""
    parts = []
    if address.address_line1:
        parts.append(address.address_line1)
    if address.city:
        parts.append(address.city)
    if address.state:
        parts.append(address.state)
    if address.country:
        parts.append(address.country)
    return ', '.join(parts)

def get_gst_updates(address, branch):
    """Get GST field updates from address"""
    updates = {}
    
    if address.gstin and not branch.gstin:
        updates['gstin'] = address.gstin
    if address.gst_state and not branch.gst_state:
        updates['gst_state'] = address.gst_state
    if address.gst_category and not branch.gst_category:
        updates['gst_category'] = address.gst_category
    if address.tax_category and not branch.tax_category:
        updates['tax_category'] = address.tax_category
        
    return updates

def auto_link_branch_addresses(branch, billing_addresses, shipping_addresses):
    """Auto-link addresses to a single branch"""
    result = {
        'billing_linked': False,
        'shipping_linked': False,
        'gst_updated': False
    }
    
    updates = {}
    
    try:
        # Link billing address if not already linked and available
        if not branch.address and billing_addresses:
            best_billing = billing_addresses[0]  # Take first available
            updates['address'] = best_billing.name
            updates['custom_billing_address_details'] = format_address_details(best_billing)
            result['billing_linked'] = True
        
        # Link shipping address if available and not already linked
        if shipping_addresses and not getattr(branch, 'custom_shipping_address', None):
            best_shipping = shipping_addresses[0]
            updates['custom_shipping_address'] = best_shipping.name
            updates['custom_shipping_address_details'] = format_address_details(best_shipping)
            result['shipping_linked'] = True
        
        # Update GST details from first available address if missing
        first_address = billing_addresses[0] if billing_addresses else (shipping_addresses[0] if shipping_addresses else None)
        if first_address:
            gst_updates = get_gst_updates(first_address, branch)
            if gst_updates:
                updates.update(gst_updates)
                result['gst_updated'] = True
        
        # Apply updates if any
        if updates:
            frappe.db.set_value('Branch', branch.name, updates)
            frappe.db.commit()
        
        return result
        
    except Exception as e:
        frappe.log_error(f"Branch auto-link error: {str(e)}", "Branch Auto Link")
        return result

@frappe.whitelist()
def auto_link_addresses():
    """Auto-link addresses to all Branches"""
    try:
        # Get all Branches
        branches = frappe.get_all('Branch', 
            fields=['name', 'branch', 'address', 'custom_shipping_address', 
                   'gstin', 'gst_state', 'gst_category', 'tax_category', 'custom_supplier'],
            limit=0
        )
        
        # Get all addresses with Dynamic Links to Branch
        dynamic_links = frappe.get_all('Dynamic Link',
            filters={
                'link_doctype': 'Branch',
                'parenttype': 'Address'
            },
            fields=['parent', 'link_name'],
            limit=0
        )
        
        # Get address details
        address_names = [link.parent for link in dynamic_links]
        addresses = []
        if address_names:
            addresses = frappe.get_all('Address',
                filters={'name': ['in', address_names]},
                fields=['name', 'address_type', 'address_line1', 'city', 'state', 'country', 
                       'gstin', 'gst_state', 'gst_category', 'tax_category'],
                limit=0
            )
        
        # Create lookup dictionaries
        address_lookup = {addr.name: addr for addr in addresses}
        branch_addresses = {branch.name: [] for branch in branches}
        
        # Map addresses to branches
        for link in dynamic_links:
            if link.parent in address_lookup:
                branch_addresses[link.link_name].append(address_lookup[link.parent])
        
        # Process each branch
        results = {
            'total_branches': len(branches),
            'billing_linked': 0,
            'shipping_linked': 0,
            'gst_updated': 0
        }
        
        for branch in branches:
            branch_doc = frappe.get_doc('Branch', branch.name)
            linked_addrs = branch_addresses.get(branch.name, [])
            billing = [a for a in linked_addrs if a.address_type == 'Billing']
            shipping = [a for a in linked_addrs if a.address_type == 'Shipping']
            
            result = auto_link_branch_addresses(branch_doc, billing, shipping)
            
            if result['billing_linked']:
                results['billing_linked'] += 1
            if result['shipping_linked']:
                results['shipping_linked'] += 1
            if result['gst_updated']:
                results['gst_updated'] += 1
        
        return results
        
    except Exception as e:
        frappe.log_error(f"Auto-link addresses error: {str(e)}", "Auto Link Addresses")
        return {'error': str(e)}

@frappe.whitelist()
def get_mapping_analysis():
    """Get detailed mapping analysis for all Branches"""
    try:
        # Get all Branches
        branches = frappe.get_all('Branch', 
            fields=['name', 'branch', 'address', 'custom_shipping_address', 
                   'gstin', 'gst_state', 'gst_category', 'tax_category'],
            limit=0
        )
        
        # Get all addresses with Dynamic Links to Branch
        dynamic_links = frappe.get_all('Dynamic Link',
            filters={
                'link_doctype': 'Branch',
                'parenttype': 'Address'
            },
            fields=['parent', 'link_name'],
            limit=0
        )
        
        # Get address details
        address_names = [link.parent for link in dynamic_links]
        addresses = []
        if address_names:
            addresses = frappe.get_all('Address',
                filters={'name': ['in', address_names]},
                fields=['name', 'address_type', 'address_line1', 'city', 'state', 'country'],
                limit=0
            )
        
        # Create lookup dictionaries
        address_lookup = {addr.name: addr for addr in addresses}
        branch_addresses = {branch.name: [] for branch in branches}
        
        # Map addresses to branches
        for link in dynamic_links:
            if link.parent in address_lookup:
                branch_addresses[link.link_name].append(address_lookup[link.parent])
        
        # Analyze each branch
        analysis = []
        for branch in branches:
            linked_addrs = branch_addresses.get(branch.name, [])
            billing = [a for a in linked_addrs if a.address_type == 'Billing']
            shipping = [a for a in linked_addrs if a.address_type == 'Shipping']
            
            # Check if branch has shipping address field
            current_shipping = getattr(branch, 'custom_shipping_address', None)
            
            branch_analysis = {
                'name': branch.name,
                'title': branch.branch,
                'current_billing': branch.address,
                'current_shipping': current_shipping,
                'available_billing': billing,
                'available_shipping': shipping,
                'billing_status': get_detailed_address_status(branch.address, billing, 'Billing'),
                'shipping_status': get_detailed_address_status(current_shipping, shipping, 'Shipping'),
                'gst_complete': bool(branch.gstin and branch.gst_state and branch.gst_category and branch.tax_category)
            }
            analysis.append(branch_analysis)
        
        return {
            'branches': analysis,
            'total_addresses': len(addresses),
            'billing_addresses': len([a for a in addresses if a.address_type == 'Billing']),
            'shipping_addresses': len([a for a in addresses if a.address_type == 'Shipping'])
        }
        
    except Exception as e:
        frappe.log_error(f"Mapping analysis error: {str(e)}", "Mapping Analysis")
        return {'error': str(e)}

def get_address_status(current_address, available_addresses):
    """Determine address status for a branch"""
    # If there's a current address set, it's linked
    if current_address:
        return 'linked'
    # If no current address but addresses are available via Dynamic Links, they're available to link
    elif available_addresses and len(available_addresses) > 0:
        return 'available'
    # No current address and no available addresses
    else:
        return 'missing'

def get_detailed_address_status(current_address, available_addresses, address_type):
    """Get detailed address status with better logic"""
    # If there's a current address set in the Branch, it's linked
    if current_address:
        return 'linked'
    
    # If no current address but there are addresses of this type available via Dynamic Links
    if available_addresses and len(available_addresses) > 0:
        return 'available'
    
    # No current address and no available addresses of this type
    return 'missing'

@frappe.whitelist()
def auto_link_single_branch(branch_name):
    """Auto-link addresses for a single Branch"""
    try:
        # Get Branch
        branch = frappe.get_doc('Branch', branch_name)
        
        # Get addresses linked to this Branch via Dynamic Links
        dynamic_links = frappe.get_all('Dynamic Link',
            filters={
                'link_doctype': 'Branch',
                'link_name': branch_name,
                'parenttype': 'Address'
            },
            fields=['parent'],
            limit=0
        )
        
        # Get address details
        address_names = [link.parent for link in dynamic_links]
        addresses = []
        if address_names:
            addresses = frappe.get_all('Address',
                filters={'name': ['in', address_names]},
                fields=['name', 'address_type', 'address_line1', 'city', 'state', 'country',
                       'gstin', 'gst_state', 'gst_category', 'tax_category'],
                limit=0
            )
        
        # Categorize addresses
        billing_addresses = [addr for addr in addresses if addr.address_type == 'Billing']
        shipping_addresses = [addr for addr in addresses if addr.address_type == 'Shipping']
        
        updates = {}
        linked_count = 0
        
        # Link billing address if not already linked and available
        if not branch.address and billing_addresses:
            best_billing = billing_addresses[0]
            updates['address'] = best_billing.name
            linked_count += 1
        
        # Link shipping address if available and not already linked
        if shipping_addresses and not getattr(branch, 'custom_shipping_address', None):
            best_shipping = shipping_addresses[0]
            updates['custom_shipping_address'] = best_shipping.name
            linked_count += 1
        
        # Update GST details from first available address if missing
        first_address = billing_addresses[0] if billing_addresses else (shipping_addresses[0] if shipping_addresses else None)
        if first_address:
            gst_updated = False
            if first_address.gstin and not branch.gstin:
                updates['gstin'] = first_address.gstin
                gst_updated = True
            if first_address.gst_state and not branch.gst_state:
                updates['gst_state'] = first_address.gst_state
                gst_updated = True
            if first_address.gst_category and not branch.gst_category:
                updates['gst_category'] = first_address.gst_category
                gst_updated = True
            if first_address.tax_category and not branch.tax_category:
                updates['tax_category'] = first_address.tax_category
                gst_updated = True
        
        # Apply updates
        if updates:
            frappe.db.set_value('Branch', branch_name, updates)
            frappe.db.commit()
        
        return {
            'status': 'success',
            'message': f'Linked {linked_count} addresses to {branch.branch}',
            'linked_count': linked_count
        }
        
    except Exception as e:
        frappe.log_error(f"Single branch auto-link error: {str(e)}", "Single Branch Auto Link")
        return {
            'status': 'error',
            'message': str(e)
        }

@frappe.whitelist()
def get_branch_address_details(branch_name):
    """Get address details for a specific Branch"""
    try:
        # Get Branch
        branch = frappe.get_doc('Branch', branch_name)
        
        # Get addresses linked to this Branch via Dynamic Links
        dynamic_links = frappe.get_all('Dynamic Link',
            filters={
                'link_doctype': 'Branch',
                'link_name': branch_name,
                'parenttype': 'Address'
            },
            fields=['parent'],
            limit=0
        )
        
        # Get address details
        address_names = [link.parent for link in dynamic_links]
        addresses = []
        if address_names:
            addresses = frappe.get_all('Address',
                filters={'name': ['in', address_names]},
                fields=['name', 'address_type', 'address_line1', 'city', 'state', 'country'],
                limit=0
            )
            
            # Categorize addresses
            available_billing = [addr for addr in addresses if addr.address_type == 'Billing']
            available_shipping = [addr for addr in addresses if addr.address_type == 'Shipping']
        
        return {
            'current_billing': branch.address,
            'current_shipping': getattr(branch, 'custom_shipping_address', None),
            'available_billing': available_billing,
            'available_shipping': available_shipping,
            'branch_name': branch.branch
        }
        
    except Exception as e:
        frappe.log_error(f"Branch address details error: {str(e)}", "Branch Address Details")
        return {
            'error': str(e)
        }

@frappe.whitelist()
def link_single_address(branch_name, address_name, address_type):
    """Link a single address to a Branch"""
    try:
        # Get address details
        address = frappe.get_doc('Address', address_name)
        
        # Prepare updates for both billing and shipping addresses
        updates = {}
        if address_type == 'billing':
            updates['address'] = address_name
        elif address_type == 'shipping':
            updates['custom_shipping_address'] = address_name
        
        # Update GST details if missing
        branch = frappe.get_doc('Branch', branch_name)
        gst_updates = get_gst_updates(address, branch)
        if gst_updates:
            updates.update(gst_updates)
        
        # Apply updates
        frappe.db.set_value('Branch', branch_name, updates)
        frappe.db.commit()
        
        return {
            'status': 'success',
            'message': f'{address_type.title()} address linked successfully to {branch.branch}'
        }
        
    except Exception as e:
        frappe.log_error(f"Single address link error: {str(e)}", "Single Address Link")
        return {
            'status': 'error',
            'message': str(e)
        }
