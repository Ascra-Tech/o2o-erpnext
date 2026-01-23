import frappe
from frappe import _
from frappe.utils import cstr, flt
import json

@frappe.whitelist()
def auto_link_addresses():
    """
    Auto-link addresses to Sub Branches based on Dynamic Links
    Returns detailed results for the advanced dashboard
    """
    try:
        # Get all Sub Branches
        sub_branches = frappe.get_all('Sub Branch', 
            fields=['name', 'sub_branch_name', 'address', 'custom_shipping_address', 
                   'gstin', 'gst_state', 'gst_category', 'tax_category', 'custom_supplier'],
            limit=0
        )
        
        # Get all Addresses with address_type
        addresses = frappe.get_all('Address',
            fields=['name', 'address_title', 'address_type', 'city', 'state', 'country',
                   'gstin', 'gst_state', 'gst_category', 'tax_category', 'address_line1'],
            limit=0
        )
        
        # Get Dynamic Links between Address and Sub Branch
        dynamic_links = frappe.get_all('Dynamic Link',
            filters={
                'parenttype': 'Address',
                'link_doctype': 'Sub Branch'
            },
            fields=['parent', 'link_name'],
            limit=0
        )
        
        # Build address mapping
        address_lookup = {addr.name: addr for addr in addresses}
        branch_addresses = {}
        
        for link in dynamic_links:
            if link.link_name not in branch_addresses:
                branch_addresses[link.link_name] = []
            if link.parent in address_lookup:
                branch_addresses[link.link_name].append(address_lookup[link.parent])
        
        # Process each Sub Branch
        results = {
            'total_branches': len(sub_branches),
            'processed': 0,
            'billing_linked': 0,
            'shipping_linked': 0,
            'gst_updated': 0,
            'errors': [],
            'branch_details': [],
            'summary': {
                'complete_branches': 0,
                'partial_branches': 0,
                'missing_branches': 0
            }
        }
        
        for branch in sub_branches:
            branch_result = process_single_branch(branch, branch_addresses.get(branch.name, []))
            results['branch_details'].append(branch_result)
            results['processed'] += 1
            
            if branch_result['billing_linked']:
                results['billing_linked'] += 1
            if branch_result['shipping_linked']:
                results['shipping_linked'] += 1
            if branch_result['gst_updated']:
                results['gst_updated'] += 1
            
            # Update summary counts
            if branch_result['billing_linked'] and branch_result['shipping_linked']:
                results['summary']['complete_branches'] += 1
            elif branch_result['billing_linked'] or branch_result['shipping_linked']:
                results['summary']['partial_branches'] += 1
            else:
                results['summary']['missing_branches'] += 1
        
        frappe.db.commit()
        return results
        
    except Exception as e:
        frappe.log_error(f"Auto-linking error: {str(e)}", "Address Auto-Linking")
        return {
            'error': str(e),
            'total_branches': 0,
            'processed': 0
        }

def process_single_branch(branch, linked_addresses):
    """Process a single Sub Branch for address linking"""
    result = {
        'name': branch.name,
        'sub_branch_name': branch.sub_branch_name,
        'billing_linked': False,
        'shipping_linked': False,
        'gst_updated': False,
        'current_billing': branch.address,
        'current_shipping': branch.custom_shipping_address,
        'available_billing': [],
        'available_shipping': [],
        'errors': []
    }
    
    # Categorize available addresses
    billing_addresses = [addr for addr in linked_addresses if addr.address_type == 'Billing']
    shipping_addresses = [addr for addr in linked_addresses if addr.address_type == 'Shipping']
    
    result['available_billing'] = billing_addresses
    result['available_shipping'] = shipping_addresses
    
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
            frappe.db.set_value('Sub Branch', branch.name, updates)
            
    except Exception as e:
        result['errors'].append(str(e))
        frappe.log_error(f"Error processing branch {branch.name}: {str(e)}", "Branch Processing Error")
    
    return result

def format_address_details(address):
    """Format address details into a readable string"""
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
    """Get GST field updates from address if branch fields are missing"""
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

@frappe.whitelist()
def get_mapping_analysis():
    """Get detailed mapping analysis for the advanced dashboard"""
    try:
        # Get all Sub Branches with current address links
        sub_branches = frappe.get_all('Sub Branch',
            fields=['name', 'sub_branch_name', 'address', 'custom_shipping_address',
                   'gstin', 'gst_state', 'gst_category', 'tax_category', 'custom_supplier'],
            limit=0
        )
        
        # Get all addresses
        addresses = frappe.get_all('Address',
            fields=['name', 'address_title', 'address_type', 'city', 'state'],
            limit=0
        )
        
        # Get dynamic links
        dynamic_links = frappe.get_all('Dynamic Link',
            filters={'parenttype': 'Address', 'link_doctype': 'Sub Branch'},
            fields=['parent', 'link_name'],
            limit=0
        )
        
        # Build mapping
        address_lookup = {addr.name: addr for addr in addresses}
        branch_addresses = {}
        
        for link in dynamic_links:
            if link.link_name not in branch_addresses:
                branch_addresses[link.link_name] = []
            if link.parent in address_lookup:
                branch_addresses[link.link_name].append(address_lookup[link.parent])
        
        # Analyze each branch
        analysis = []
        for branch in sub_branches:
            linked_addrs = branch_addresses.get(branch.name, [])
            billing = [a for a in linked_addrs if a.address_type == 'Billing']
            shipping = [a for a in linked_addrs if a.address_type == 'Shipping']
            
            # Check if branch has shipping address field (it may not exist in current structure)
            current_shipping = getattr(branch, 'custom_shipping_address', None)
            
            branch_analysis = {
                'name': branch.name,
                'title': branch.sub_branch_name,
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
    # If there's a current address set in the Sub Branch, it's linked
    if current_address:
        return 'linked'
    
    # If no current address but there are addresses of this type available via Dynamic Links
    if available_addresses and len(available_addresses) > 0:
        return 'available'
    
    # No current address and no available addresses of this type
    return 'missing'

@frappe.whitelist()
def auto_link_single_branch(branch_name):
    """Auto-link addresses for a single Sub Branch"""
    try:
        # Get Sub Branch
        branch = frappe.get_doc('Sub Branch', branch_name)
        
        # Get addresses linked to this Sub Branch via Dynamic Links
        dynamic_links = frappe.get_all('Dynamic Link',
            filters={
                'parenttype': 'Address',
                'link_doctype': 'Sub Branch',
                'link_name': branch_name
            },
            fields=['parent'],
            limit=0
        )
        
        if not dynamic_links:
            return {
                "status": "info",
                "message": "No addresses found linked to this Sub Branch"
            }
        
        # Get address details
        address_names = [link.parent for link in dynamic_links]
        addresses = frappe.get_all('Address',
            filters={'name': ['in', address_names]},
            fields=['name', 'address_type', 'address_line1', 'city', 'state', 'country', 'gstin', 'gst_state', 'gst_category', 'tax_category'],
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
            frappe.db.set_value('Sub Branch', branch_name, updates)
            frappe.db.commit()
            
            return {
                "status": "success",
                "message": f"Successfully linked {linked_count} address(es) and updated GST details",
                "updates": updates
            }
        else:
            return {
                "status": "info",
                "message": "No updates needed - addresses already linked"
            }
            
    except Exception as e:
        frappe.log_error(f"Auto-linking error for {branch_name}: {str(e)}", "Sub Branch Auto-Linking")
        return {
            "status": "error",
            "message": str(e)
        }

@frappe.whitelist()
def get_branch_address_details(branch_name):
    """Get detailed address information for a specific Sub Branch"""
    try:
        # Get Sub Branch
        branch = frappe.get_doc('Sub Branch', branch_name)
        
        # Get addresses linked to this Sub Branch via Dynamic Links
        dynamic_links = frappe.get_all('Dynamic Link',
            filters={
                'parenttype': 'Address',
                'link_doctype': 'Sub Branch',
                'link_name': branch_name
            },
            fields=['parent'],
            limit=0
        )
        
        # Get address details
        available_billing = []
        available_shipping = []
        
        if dynamic_links:
            address_names = [link.parent for link in dynamic_links]
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
            'branch_name': branch.sub_branch_name
        }
        
    except Exception as e:
        frappe.log_error(f"Branch address details error: {str(e)}", "Branch Address Details")
        return {
            'error': str(e)
        }

@frappe.whitelist()
def link_single_address(branch_name, address_name, address_type):
    """Link a single address to a Sub Branch"""
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
        branch = frappe.get_doc('Sub Branch', branch_name)
        gst_updates = get_gst_updates(address, branch)
        if gst_updates:
            updates.update(gst_updates)
        
        # Apply updates
        frappe.db.set_value('Sub Branch', branch_name, updates)
        frappe.db.commit()
        
        return {
            'status': 'success',
            'message': f'{address_type.title()} address linked successfully'
        }
        
    except Exception as e:
        frappe.log_error(f"Single address linking error: {str(e)}", "Single Address Linking")
        return {
            'status': 'error',
            'message': str(e)
        }

@frappe.whitelist()
def create_address_for_branch(branch_name, address_type, address_data):
    """Create a new address and link it to a Sub Branch"""
    try:
        # Parse address data if it's a string
        if isinstance(address_data, str):
            address_data = json.loads(address_data)
        
        # Get Sub Branch details
        branch = frappe.get_doc('Sub Branch', branch_name)
        
        # Create new address
        address_doc = frappe.new_doc('Address')
        address_doc.address_type = address_type
        address_doc.address_title = f"{branch.sub_branch_name} - {address_type}"
        
        # Set address fields
        for field in ['address_line1', 'address_line2', 'city', 'state', 'country', 'pincode', 'gstin', 'gst_category', 'tax_category']:
            if field in address_data and address_data[field]:
                setattr(address_doc, field, address_data[field])
        
        # Add link to Sub Branch
        address_doc.append('links', {
            'link_doctype': 'Sub Branch',
            'link_name': branch_name
        })
        
        # Also link to supplier if available
        if branch.custom_supplier:
            address_doc.append('links', {
                'link_doctype': 'Supplier',
                'link_name': branch.custom_supplier
            })
        
        address_doc.insert()
        
        # Update Sub Branch with new address
        updates = {}
        address_details = format_address_details(address_doc)
        
        if address_type == 'Billing':
            updates['address'] = address_doc.name
            updates['custom_billing_address_details'] = address_details
        else:
            updates['custom_shipping_address'] = address_doc.name
            updates['custom_shipping_address_details'] = address_details
        
        frappe.db.set_value('Sub Branch', branch_name, updates)
        frappe.db.commit()
        
        return {
            'status': 'success',
            'message': f'{address_type} address created and linked successfully',
            'address_name': address_doc.name
        }
        
    except Exception as e:
        frappe.log_error(f"Address creation error: {str(e)}", "Address Creation")
        return {
            'status': 'error',
            'message': str(e)
        }
