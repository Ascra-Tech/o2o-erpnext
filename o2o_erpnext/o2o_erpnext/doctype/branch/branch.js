frappe.ui.form.on('Branch', {
    setup: function(frm) {
        // Add query filter for supplier field
        frm.set_query('custom_supplier', function() {
            return {
                filters: {
                    'custom_user': frappe.session.user
                }
            };
        });
    },
    
    custom_supplier: function(frm) {
        if (!frm.doc.custom_supplier) return;
        
        if (frm.supplier_check_timeout) {
            clearTimeout(frm.supplier_check_timeout);
        }
        
        frm.supplier_check_timeout = setTimeout(() => {
            frappe.call({
                method: 'o2o_erpnext.o2o_erpnext.doctype.branch.branch.get_supplier_branch_info',
                args: {
                    supplier: frm.doc.custom_supplier
                },
                callback: function(response) {
                    const branch = response.message;
                    
                    if (branch && branch.name && branch.name !== frm.doc.name) {
                        frm.set_value('custom_supplier', '');
                        frappe.show_alert({
                            message: __('This supplier already has a branch (created on {0}). Please select a different supplier.',
                                [frappe.datetime.str_to_user(branch.creation)]),
                            indicator: 'red'
                        });
                    }
                }
            });
        }, 300);
    },
    
    refresh: function(frm) {
        if (frm.supplier_check_timeout) {
            clearTimeout(frm.supplier_check_timeout);
        }
        
        // Clear existing custom buttons
        frm.remove_custom_button('Create Address');
        frm.remove_custom_button('Delete Address');
        frm.remove_custom_button('Update Address');
        
        // Check if addresses exist
        let billing_exists = frm.doc.address ? true : false;
        let shipping_exists = frm.doc.custom_shipping_address ? true : false;
        
        // Set up Address menu with options
        let has_any_address_action = false;
        
        // Always add Create option
        frm.add_custom_button(__('Create'), function() {
            // Show dialog to select address type
            frappe.prompt([
                {
                    fieldname: 'address_type',
                    label: __('Address Type'),
                    fieldtype: 'Select',
                    options: 'Billing\nShipping',
                    reqd: 1
                }
            ], function(values) {
                // After selecting address type, create a dialog matching the address form
                let address_type = values.address_type;
                
                let d = new frappe.ui.Dialog({
                    title: __('New Address'),
                    fields: [
                        // Section 1: Address Details
                        {
                            fieldname: 'address_section',
                            fieldtype: 'Section Break',
                            label: __('Address Details')
                        },
                        {
                            fieldname: 'address_line1',
                            label: __('Address Line 1'),
                            fieldtype: 'Data',
                            reqd: 1
                        },
                        {
                            fieldname: 'address_line2',
                            label: __('Address Line 2'),
                            fieldtype: 'Data'
                        },
                        {
                            fieldname: 'city',
                            label: __('City/Town'),
                            fieldtype: 'Data',
                            reqd: 1
                        },
                        {
                            fieldname: 'state',
                            label: __('State/Province'),
                            fieldtype: 'Select',
                            options: '\nAndaman and Nicobar Islands\nAndhra Pradesh\nArunachal Pradesh\nAssam\nBihar\nChandigarh\nChhattisgarh\nDadra and Nagar Haveli and Daman and Diu\nDelhi\nGoa\nGujarat\nHaryana\nHimachal Pradesh\nJammu and Kashmir\nJharkhand\nKarnataka\nKerala\nLadakh\nLakshadweep\nMadhya Pradesh\nMaharashtra\nManipur\nMeghalaya\nMizoram\nNagaland\nOdisha\nPuducherry\nPunjab\nRajasthan\nSikkim\nTamil Nadu\nTelangana\nTripura\nUttar Pradesh\nUttarakhand\nWest Bengal',
                            reqd: 1,
                            change: function() {
                                let state = d.get_value('state');
                                if (!state) return;
                                
                                // Default tax category
                                let tax_category = 'In-State';
                                
                                // If we have supplier information, check state directly from supplier
                                if (frm.doc.custom_supplier) {
                                    frappe.db.get_value('Supplier', frm.doc.custom_supplier, 'custom_vendor_state')
                                        .then(supplier_data => {
                                            if (supplier_data && supplier_data.message && supplier_data.message.custom_vendor_state) {
                                                let vendor_state = supplier_data.message.custom_vendor_state;
                                                
                                                // Compare states
                                                if (state.toLowerCase() === vendor_state.toLowerCase()) {
                                                    tax_category = 'In-State';
                                                } else {
                                                    tax_category = 'Out-State';
                                                }
                                                
                                                // Set the tax category
                                                d.set_value('tax_category', tax_category);
                                            }
                                        })
                                        .catch(err => {
                                            console.error("Error fetching supplier state:", err);
                                            // Set default tax category on error
                                            d.set_value('tax_category', tax_category);
                                        });
                                } else {
                                    // Set default tax category if no supplier
                                    d.set_value('tax_category', tax_category);
                                }
                            }
                        },
                        {
                            fieldname: 'country',
                            label: __('Country'),
                            fieldtype: 'Link',
                            options: 'Country',
                            default: 'India',
                            reqd: 1
                        },
                        {
                            fieldname: 'pincode',
                            label: __('Postal Code'),
                            fieldtype: 'Data',
                            reqd: 1
                        },
                        // Column Break
                        {
                            fieldname: 'col_break1',
                            fieldtype: 'Column Break'
                        },
                        {
                            fieldname: 'is_primary_address',
                            label: __('Preferred Billing Address'),
                            fieldtype: 'Check',
                            default: address_type === 'Billing' ? 1 : 0
                        },
                        {
                            fieldname: 'is_shipping_address',
                            label: __('Preferred Shipping Address'),
                            fieldtype: 'Check',
                            default: address_type === 'Shipping' ? 1 : 0
                        },
                        {
                            fieldname: 'disabled',
                            label: __('Disabled'),
                            fieldtype: 'Check',
                            default: 0
                        },
                        // Section 2: Tax Details
                        {
                            fieldname: 'tax_section',
                            fieldtype: 'Section Break',
                            label: __('Tax Details')
                        },
                        {
                            fieldname: 'gstin',
                            label: __('GSTIN / UIN'),
                            fieldtype: 'Data'
                        },
                        {
                            fieldname: 'tax_category',
                            label: __('Tax Category'),
                            fieldtype: 'Link',
                            options: 'Tax Category',
                            default: 'In-State',
                            reqd: 1
                        },
                        {
                            fieldname: 'col_break2',
                            fieldtype: 'Column Break'
                        },
                        {
                            fieldname: 'gst_category',
                            label: __('GST Category'),
                            fieldtype: 'Select',
                            options: 'Registered Regular\nRegistered Composition\nUnregistered\nOverseas\nUIN Holders\nSEZ\nDeemed Export',
                            default: 'Unregistered'
                        }
                    ],
                    primary_action_label: __('Save'),
                    primary_action: function() {
                        let values = d.get_values();
                        
                        // Call server-side method to create address
                        frappe.call({
                            method: "create_address",
                            doc: frm.doc,
                            args: {
                                address_type: address_type,
                                address_data: values
                            },
                            callback: function(r) {
                                if (r.message && r.message.status === "success") {
                                    frm.reload_doc();
                                    d.hide();
                                }
                            }
                        });
                    }
                });
                
                d.show();
                
                // Add "Edit Full Form" button
                d.$wrapper.find('.modal-footer').prepend(`
                    <button class="btn btn-default edit-full-form">
                        ${__('Edit Full Form')}
                    </button>
                `);
                
                // Handle Edit Full Form button click
                d.$wrapper.find('.edit-full-form').on('click', function() {
                    d.hide();
                    
                    // Create temporary address and open in full form
                    let tmp_address = frappe.model.get_new_doc("Address");
                    frappe.set_route("Form", "Address", tmp_address.name);
                });
            }, __('Select Address Type'), __('Next'));
        }, __('Address'));
        has_any_address_action = true;
        
        // Add Update option if supplier exists
        if (frm.doc.custom_supplier) {
            frm.add_custom_button(__('Update'), function() {
                // Show a loading indicator
                frappe.show_alert({
                    message: __("Searching for available addresses..."),
                    indicator: 'blue'
                });
                
                // Find addresses linked to this supplier and this branch
                frappe.call({
                    method: "frappe.client.get_list",
                    args: {
                        doctype: "Address",
                        filters: [
                            ["Dynamic Link", "link_doctype", "=", "Supplier"],
                            ["Dynamic Link", "link_name", "=", frm.doc.custom_supplier]
                        ],
                        fields: ["name", "address_type", "address_line1", "city", "state", "country"]
                    },
                    callback: function(r) {
                        if (r.message && r.message.length) {
                            // Get all addresses linked to supplier
                            let all_addresses = r.message;
                            
                            // Now check which ones are linked to this specific branch
                            let address_promises = all_addresses.map(addr => {
                                return new Promise((resolve) => {
                                    frappe.call({
                                        method: "frappe.client.get",
                                        args: {
                                            doctype: "Address",
                                            name: addr.name
                                        },
                                        callback: function(result) {
                                            if (result.message && result.message.links) {
                                                // Check if this address is linked to this branch
                                                let linked_to_branch = false;
                                                
                                                for (let link of result.message.links) {
                                                    if (link.link_doctype === 'Branch' && link.link_name === frm.doc.name) {
                                                        linked_to_branch = true;
                                                        break;
                                                    }
                                                }
                                                
                                                // Add a flag to indicate if it's linked to this branch
                                                addr.linked_to_branch = linked_to_branch;
                                                resolve(addr);
                                            } else {
                                                addr.linked_to_branch = false;
                                                resolve(addr);
                                            }
                                        }
                                    });
                                });
                            });
                            
                            Promise.all(address_promises).then(addresses => {
                                // Create dialog to select addresses
                                let billing_addresses = addresses.filter(addr => addr.address_type === 'Billing');
                                let shipping_addresses = addresses.filter(addr => addr.address_type === 'Shipping');
                                
                                let fields = [];
                                
                                // Billing address field
                                if (billing_addresses.length) {
                                    fields.push({
                                        fieldname: 'billing_address_section',
                                        fieldtype: 'Section Break',
                                        label: __('Billing Address')
                                    });
                                    
                                    let billing_options = billing_addresses.map(addr => {
                                        let addr_display = `${addr.name}: ${addr.address_line1}, ${addr.city}, ${addr.state}, ${addr.country}`;
                                        if (addr.linked_to_branch) {
                                            addr_display += ` (${__('Already linked to this Branch')})`;
                                        }
                                        return {
                                            value: addr.name,
                                            label: addr_display
                                        };
                                    });
                                    
                                    fields.push({
                                        fieldname: 'billing_address',
                                        label: __('Select Billing Address'),
                                        fieldtype: 'Select',
                                        options: billing_options,
                                        default: ""
                                    });
                                } else {
                                    fields.push({
                                        fieldname: 'no_billing_address',
                                        fieldtype: 'HTML',
                                        options: `<div class="alert alert-warning">
                                                    ${__("No billing addresses found for this supplier")}
                                                  </div>`
                                    });
                                }
                                
                                // Shipping address field
                                if (shipping_addresses.length) {
                                    fields.push({
                                        fieldname: 'shipping_address_section',
                                        fieldtype: 'Section Break',
                                        label: __('Shipping Address')
                                    });
                                    
                                    let shipping_options = shipping_addresses.map(addr => {
                                        let addr_display = `${addr.name}: ${addr.address_line1}, ${addr.city}, ${addr.state}, ${addr.country}`;
                                        if (addr.linked_to_branch) {
                                            addr_display += ` (${__('Already linked to this Branch')})`;
                                        }
                                        return {
                                            value: addr.name,
                                            label: addr_display
                                        };
                                    });
                                    
                                    fields.push({
                                        fieldname: 'shipping_address',
                                        label: __('Select Shipping Address'),
                                        fieldtype: 'Select',
                                        options: shipping_options,
                                        default: ""
                                    });
                                } else {
                                    fields.push({
                                        fieldname: 'no_shipping_address',
                                        fieldtype: 'HTML',
                                        options: `<div class="alert alert-warning">
                                                    ${__("No shipping addresses found for this supplier")}
                                                  </div>`
                                    });
                                }
                                
                                let d = new frappe.ui.Dialog({
                                    title: __('Select Addresses to Link'),
                                    fields: fields,
                                    primary_action_label: __('Link Addresses'),
                                    primary_action: function() {
                                        let values = d.get_values();
                                        let updates = {};
                                        let address_updates = [];
                                        
                                        if (values.billing_address) {
                                            updates.address = values.billing_address;
                                            address_updates.push({
                                                address: values.billing_address,
                                                type: 'Billing'
                                            });
                                        }
                                        
                                        if (values.shipping_address) {
                                            updates.custom_shipping_address = values.shipping_address;
                                            address_updates.push({
                                                address: values.shipping_address,
                                                type: 'Shipping'
                                            });
                                        }
                                        
                                        if (Object.keys(updates).length === 0) {
                                            frappe.msgprint(__('No addresses selected'));
                                            return;
                                        }
                                        
                                        // First, update the branch document
                                        frappe.model.set_value(frm.doctype, frm.docname, updates);
                                        
                                        // Then, fetch address details and update branch address details fields
                                        let promises = address_updates.map(addr_update => {
                                            return frappe.call({
                                                method: "frappe.client.get",
                                                args: {
                                                    doctype: "Address",
                                                    name: addr_update.address
                                                },
                                                callback: function(result) {
                                                    if (result.message) {
                                                        let addr = result.message;
                                                        
                                                        // Create address summary
                                                        let address_summary = [];
                                                        if (addr.address_line1) address_summary.push(addr.address_line1);
                                                        if (addr.address_line2) address_summary.push(addr.address_line2);
                                                        if (addr.city) address_summary.push(addr.city);
                                                        if (addr.state) address_summary.push(addr.state);
                                                        if (addr.country) address_summary.push(addr.country);
                                                        if (addr.pincode) address_summary.push("PIN: " + addr.pincode);
                                                        
                                                        let addr_text = address_summary.join(", ");
                                                        
                                                        // Update the corresponding address details field
                                                        if (addr_update.type === 'Billing') {
                                                            frm.set_value('custom_billing_address_details', addr_text);
                                                        } else {
                                                            frm.set_value('custom_shipping_address_details', addr_text);
                                                        }
                                                        
                                                        // Also ensure the address has a link to the branch
                                                        let has_link = false;
                                                        if (addr.links) {
                                                            for (let link of addr.links) {
                                                                if (link.link_doctype === 'Branch' && link.link_name === frm.doc.name) {
                                                                    has_link = true;
                                                                    break;
                                                                }
                                                            }
                                                        }
                                                        
                                                        if (!has_link) {
                                                            // Add link to branch if not exists
                                                            frappe.call({
                                                                method: "frappe.client.insert",
                                                                args: {
                                                                    doc: {
                                                                        doctype: "Dynamic Link",
                                                                        parenttype: "Address",
                                                                        parentfield: "links",
                                                                        parent: addr_update.address,
                                                                        link_doctype: "Branch",
                                                                        link_name: frm.doc.name
                                                                    }
                                                                }
                                                            });
                                                        }
                                                    }
                                                }
                                            });
                                        });
                                        
                                        Promise.all(promises).then(() => {
                                            frm.save().then(() => {
                                                frappe.show_alert({
                                                    message: __("Addresses linked successfully"),
                                                    indicator: 'green'
                                                });
                                                d.hide();
                                            });
                                        });
                                    }
                                });
                                
                                d.show();
                            });
                        } else {
                            frappe.msgprint(__("No addresses found for supplier ") + frm.doc.custom_supplier);
                        }
                    }
                });
            }, __('Address'));
            has_any_address_action = true;
        }
        
        // Add Delete option if addresses exist
        if (billing_exists || shipping_exists) {
            frm.add_custom_button(__('Delete'), function() {
                // Show a dialog with checkboxes for addresses
                let fields = [];
                
                if (billing_exists) {
                    fields.push({
                        fieldname: 'delete_billing',
                        label: __('Delete Billing Address'),
                        fieldtype: 'Check',
                        default: 0
                    });
                }
                
                if (shipping_exists) {
                    fields.push({
                        fieldname: 'delete_shipping',
                        label: __('Delete Shipping Address'),
                        fieldtype: 'Check',
                        default: 0
                    });
                }
                
                frappe.prompt(
                    fields,
                    function(values) {
                        let addresses_to_delete = [];
                        
                        // Prepare for update
                        let update_fields = {};
                        
                        if (billing_exists && values.delete_billing) {
                            addresses_to_delete.push(frm.doc.address);
                            update_fields.address = '';
                            update_fields.custom_billing_address_details = '';
                        }
                        
                        if (shipping_exists && values.delete_shipping) {
                            addresses_to_delete.push(frm.doc.custom_shipping_address);
                            update_fields.custom_shipping_address = '';
                            update_fields.custom_shipping_address_details = '';
                        }
                        
                        if (addresses_to_delete.length === 0) {
                            frappe.msgprint(__('No addresses selected for deletion'));
                            return;
                        }
                        
                        // First update branch to remove references
                        frappe.model.set_value(frm.doctype, frm.docname, update_fields);
                        frm.save().then(() => {
                            // After saving Branch, delete addresses one by one
                            let deletion_promises = addresses_to_delete.map(addr => {
                                return frappe.call({
                                    method: 'frappe.client.delete',
                                    args: {
                                        doctype: 'Address',
                                        name: addr
                                    }
                                });
                            });
                            
                            Promise.all(deletion_promises).then(() => {
                                frappe.msgprint(__('Selected addresses deleted'));
                                frm.refresh();
                            }).catch(err => {
                                console.error("Error deleting addresses:", err);
                                frappe.msgprint(__('Error deleting some addresses. Please refresh and try again.'));
                                frm.refresh();
                            });
                        });
                    },
                    __('Select Addresses to Delete'),
                    __('Delete')
                );
            }, __('Address'));
            has_any_address_action = true;
        }
        
        // Make the Address dropdown primary if any actions exist
        if (has_any_address_action) {
            frm.page.set_inner_btn_group_as_primary('Address');
        }
        
        // Modify Tax Actions section - remove Copy Tax Details button
        if (frm.doc.address) {
            // Remove the "Copy Tax Details from Address" button if it exists
            frm.remove_custom_button(__('Copy Tax Details from Address'), __('Tax Actions'));
            
            // Keep the Update Address with Tax Details button
            frm.add_custom_button(__('Update Address with Tax Details'), function() {
                frm.call({
                    doc: frm.doc,
                    method: 'sync_tax_details_with_address',
                    callback: function(r) {
                        if (r.message && r.message.status === "success") {
                            frappe.show_alert({
                                message: __("Tax details synced successfully"),
                                indicator: 'green'
                            });
                        }
                    }
                });
            }, __('Tax Actions'));
        }
    },
    
    // Auto-fetch tax details when address is changed
    address: function(frm) {
        if (frm.doc.address) {
            // Fetch tax details from address
            fetch_tax_details_from_address(frm);
        }
    },
    
    // Update GST State Number when GST State changes
    gst_state: function(frm) {
        frm.trigger('update_gst_state_number');
        frm.trigger('update_tax_category');
    },
    
    update_gst_state_number: function(frm) {
        if (frm.doc.gst_state) {
            const state_code_map = {
                "Andaman and Nicobar Islands": "35",
                "Andhra Pradesh": "37",
                "Arunachal Pradesh": "12",
                "Assam": "18",
                "Bihar": "10",
                "Chandigarh": "04",
                "Chhattisgarh": "22",
                "Dadra and Nagar Haveli and Daman and Diu": "26",
                "Delhi": "07",
                "Goa": "30",
                "Gujarat": "24",
                "Haryana": "06",
                "Himachal Pradesh": "02",
                "Jammu and Kashmir": "01",
                "Jharkhand": "20",
                "Karnataka": "29",
                "Kerala": "32",
                "Ladakh": "38",
                "Lakshadweep Islands": "31",
                "Madhya Pradesh": "23",
                "Maharashtra": "27",
                "Manipur": "14",
                "Meghalaya": "17",
                "Mizoram": "15",
                "Nagaland": "13",
                "Odisha": "21",
                "Other Countries": "96",
                "Other Territory": "97",
                "Puducherry": "34",
                "Punjab": "03",
                "Rajasthan": "08",
                "Sikkim": "11",
                "Tamil Nadu": "33",
                "Telangana": "36",
                "Tripura": "16",
                "Uttar Pradesh": "09",
                "Uttarakhand": "05",
                "West Bengal": "19"
            };
            frm.set_value('gst_state_number', state_code_map[frm.doc.gst_state] || "");
        }
    },
    
    // Add function to update tax category based on state
    update_tax_category: function(frm) {
        let state = frm.doc.gst_state;
        if (!state) return;
        
        // Default tax category
        let tax_category = 'In-State';
        
        // If we have supplier information, check state directly from supplier
        if (frm.doc.custom_supplier) {
            frappe.db.get_value('Supplier', frm.doc.custom_supplier, 'custom_vendor_state')
                .then(supplier_data => {
                    if (supplier_data && supplier_data.message && supplier_data.message.custom_vendor_state) {
                        let vendor_state = supplier_data.message.custom_vendor_state;
                        
                        // Compare states
                        if (state.toLowerCase() === vendor_state.toLowerCase()) {
                            tax_category = 'In-State';
                        } else {
                            tax_category = 'Out-State';
                        }
                        
                        // Set the tax category
                        frm.set_value('tax_category', tax_category);
                    }
                })
                .catch(err => {
                    console.error("Error fetching supplier state:", err);
                    // Set default tax category on error
                    frm.set_value('tax_category', tax_category);
                });
        } else {
            // Set default tax category if no supplier
            frm.set_value('tax_category', tax_category);
        }
    },
    
    // GSTIN validation
    gstin: function(frm) {
        if (frm.doc.gstin) {
            frm.doc.gstin = frm.doc.gstin.toUpperCase();
            frm.refresh_field('gstin');
            
            // Basic GSTIN validation - 15 characters 
            if (frm.doc.gstin.length !== 15) {
                frappe.show_alert({
                    message: __("GSTIN should be 15 characters long"),
                    indicator: 'orange'
                });
            }
        }
    }
});

// Function to fetch tax details from address
function fetch_tax_details_from_address(frm) {
    frappe.call({
        method: "frappe.client.get",
        args: {
            doctype: "Address",
            name: frm.doc.address
        },
        callback: function(response) {
            if (response.message) {
                const address_doc = response.message;
                
                // Update tax fields from address
                frm.set_value('gstin', address_doc.gstin);
                frm.set_value('gst_state', address_doc.gst_state);
                frm.set_value('gst_state_number', address_doc.gst_state_number);
                frm.set_value('tax_category', address_doc.tax_category);
                frm.set_value('gst_category', address_doc.gst_category);
                
                frappe.show_alert({
                    message: __('Tax details fetched automatically from address'),
                    indicator: 'green'
                });
            }
        }
    });
}