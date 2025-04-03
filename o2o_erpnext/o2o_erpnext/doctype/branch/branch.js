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
        
        // Check if addresses exist
        let billing_exists = frm.doc.address ? true : false;
        let shipping_exists = frm.doc.custom_shipping_address ? true : false;
        
        // Always show the Create Address button
        frm.add_custom_button(__('Create Address'), function() {
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
                            reqd: 1
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
                
                // Set up state change event to check tax category
                d.fields_dict.state.df.onchange = function() {
                    let state = d.get_value('state');
                    if (!state) return;
                    
                    // If supplier has custom_vendor_state field, compare and set tax category
                    if (frm.doc.custom_supplier) {
                        frappe.db.get_value('Supplier', frm.doc.custom_supplier, 'custom_vendor_state')
                            .then(r => {
                                if (r && r.message && r.message.custom_vendor_state) {
                                    let vendor_state = r.message.custom_vendor_state;
                                    
                                    // Compare states and set tax category
                                    let tax_category = (state.toLowerCase() === vendor_state.toLowerCase()) 
                                        ? 'In-State' 
                                        : 'Out-State';
                                    
                                    d.set_value('tax_category', tax_category);
                                }
                            });
                    }
                };
                
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
        }).addClass('btn-primary');
        
        // Show Delete Address button only if addresses exist
        if (billing_exists || shipping_exists) {
            frm.add_custom_button(__('Delete Address'), function() {
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
            }).addClass('btn-primary');
        }
    }
});