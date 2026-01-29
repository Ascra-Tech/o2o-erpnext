// Patch Frappe's check_if_latest method to always return true for Purchase Orders
// and protect address fields from being overridden
(function() {
    if (typeof frappe !== 'undefined' && frappe.model) {
        // Store the original check_if_latest method
        const original_check_if_latest = frappe.model.check_if_latest;
        
        // Override the method
        frappe.model.check_if_latest = function(doctype, doc, frm) {
            // Skip timestamp check for Purchase Orders
            if (doctype === "Purchase Order") {
                return true;
            }
            // For other doctypes, use the original method
            return original_check_if_latest.apply(this, arguments);
        };
        
        console.log("Timestamp check disabled for Purchase Orders");
    }
    
    // Patch Frappe's set_value method for shipping_address and supplier_address
   
    //////
})();

// Store capexTotal and opexTotal globally for budget updates
let storedCapexTotal = 0;
let storedOpexTotal = 0;

frappe.ui.form.on('Purchase Order', {
    setup: function(frm) {
        // Set up custom validation
        frm.custom_validate = function() {
            return validate_purchase_order(frm);
        };
    },

    refresh: function(frm) {
        // Set vendor filters based on supplier
        if(frm.doc.supplier) {
            set_vendor_filters(frm);
        }

        // Only for new documents, call branch address
        if (frm.doc.__islocal && (frm.doc.custom_branch || frm.doc.custom_sub_branch)) {
            call_check_and_apply_branch_addresses(frm);
        }
        
        // Protect address display on form load for all documents
        if (frm.doc.custom_sub_branch || frm.doc.custom_branch) {
            setTimeout(() => {
                protect_address_display_fields(frm);
            }, 1500);
        }

        // For NEW documents: Role-based sub-branch requirement
        if (frm.doc.__islocal) {
            frappe.call({
                method: 'o2o_erpnext.api.purchase_order.is_branch_level_user',
                callback: function(r) {
                    const isBranchUser = r.message;
                    
                    if (isBranchUser) {
                        // Person Raising Request Branch - sub-branch optional
                        frm.set_df_property('custom_sub_branch', 'reqd', 0);
                    } else {
                        // Person Raising Request - sub-branch mandatory
                        frm.set_df_property('custom_sub_branch', 'reqd', 1);
                    }
                }
            });
        } else {
            // For EXISTING documents: Always optional (server handles validation)
            frm.set_df_property('custom_sub_branch', 'reqd', 0);
            
            // Add budget display section for existing documents
            try {
                frm.dashboard.add_section(
                    `<div class="row">
                        <div class="col-xs-6">
                            <div style="border: 1px solid #d1d8dd; border-radius: 4px; padding: 10px; text-align: center; background-color: #f5f7fa; margin: 5px;">
                                <div style="font-weight: bold; color: #8d99a6;">CAPEX Budget Used</div>
                                <div style="font-size: 16px; font-weight: bold;">${frappe.format(frm.doc.custom_last_capex_total || 0, {fieldtype: "Currency"})}</div>
                            </div>
                        </div>
                        <div class="col-xs-6">
                            <div style="border: 1px solid #d1d8dd; border-radius: 4px; padding: 10px; text-align: center; background-color: #f5f7fa; margin: 5px;">
                                <div style="font-weight: bold; color: #8d99a6;">OPEX Budget Used</div>
                                <div style="font-size: 16px; font-weight: bold;">${frappe.format(frm.doc.custom_last_opex_total || 0, {fieldtype: "Currency"})}</div>
                            </div>
                        </div>
                    </div>`
                );
                
                // Add button to view budget transactions
                if (frm.doc.custom_budget_transactions) {
                    frm.add_custom_button(__('View Budget Transactions'), function() {
                        frappe.route_options = {
                            "reference_doctype": "Purchase Order",
                            "reference_name": frm.doc.name
                        };
                        frappe.set_route("List", "Budget Transaction");
                    }, __("Budget"));
                }
            } catch (e) {
                console.error("Error rendering budget dashboard:", e);
            }
            
            return;
        }
        
        // Get defaults for new document
        frappe.call({
            method: 'o2o_erpnext.api.purchase_order.validate_and_set_purchase_order_defaults',
            freeze: true,
            freeze_message: __('Setting defaults...'),
            callback: function(r) {
                if (r.exc) return;
                
                if (r.message && r.message.status === 'success' && r.message.data) {
                    // Set the default values in a batch to minimize DOM updates
                    const updates = {};
                    
                    if (r.message.data.supplier) updates.supplier = r.message.data.supplier;
                    if (r.message.data.custom_branch) updates.custom_branch = r.message.data.custom_branch;
                    if (r.message.data.custom__approver_name_and_email) updates.custom__approver_name_and_email = r.message.data.custom__approver_name_and_email;
                    if (r.message.data.custom_sub_branch) updates.custom_sub_branch = r.message.data.custom_sub_branch;
                    if (r.message.data.custom_supplier_code) updates.custom_supplier_code = r.message.data.custom_supplier_code;
                    if (r.message.data.custom_order_code) updates.custom_order_code = r.message.data.custom_order_code;
                    
                    // Add the combined name+email fields
                    if (r.message.data.custom_requisition_approver_name_and_email) 
                        updates.custom_requisition_approver_name_and_email = r.message.data.custom_requisition_approver_name_and_email;
                    
                    // Add the separate email-only fields
                    if (r.message.data.custom_po_approver_email)
                        updates.custom_po_approver_email = r.message.data.custom_po_approver_email;
                    if (r.message.data.custom_requisition_approver_email)
                        updates.custom_requisition_approver_email = r.message.data.custom_requisition_approver_email;
                    
                    // Apply all updates at once
                    frm.set_value(updates);
                }
            }
        });

        // Hide UI elements
        $('.form-attachments, .form-tags, .form-share').hide();

        // Remove standard buttons
        setTimeout(() => {
            const buttonsToRemove = [
                'Get Items From', 'Update Items', 'Payment', 'Payment Request',
                'Purchase Invoice', 'Link to Material Request', 'Update Rate as per Last Purchase',
                'Print', 'Download', 'Hold', 'Close'
            ];

            buttonsToRemove.forEach(btn => frm.remove_custom_button(btn));
            
            // Remove menu items
            const menuItemsToRemove = [
                'Print', 'Email', 'Links', 'Duplicate', 'Send SMS',
                'Copy to Clipboard', 'Reload', 'Remind Me', 'Undo',
                'Redo', 'Repeat', 'New Purchase Order'
            ];

            menuItemsToRemove.forEach(item => {
                const selector = `[data-label="${encodeURIComponent(item)}"]`;
                frm.page.menu.find(selector).parent().parent().remove();
            });
        }, 10);
        
        // Add custom buttons
        frm.add_custom_button(__('Calculate GST'), function() {
            if (!frm.doc.__islocal) {
                call_calculate_gst_server(frm);
            } else {
                calculate_gst_preview(frm);
            }
        });
        
        // Add button to validate without saving
        frm.add_custom_button(__('Validate'), function() {
            validate_purchase_order(frm);
        });
        
        // Add button to manually trigger date calculation
        frm.add_custom_button(__('Set Schedule Date'), function() {
            set_schedule_date(frm);
        });
        
        // Clear shipping address filter to show all addresses
        clearShippingAddressFilter(frm);
    },
    
    onload: function(frm) {
        // Set schedule_date when form is first loaded
        set_schedule_date(frm);
        
        // Clear shipping address filter to show all addresses
        clearShippingAddressFilter(frm);
    },

    validate: function(frm) {
        frm.set_value("custom_created_user", frm.doc.owner);
        
        console.log(frm.doc.name)
        if (frappe.user_roles.includes("Person Raising Request")) {
            frm.clear_table('custom_purchasing_details_original');

            if (frm.doc.items && frm.doc.items.length > 0) {
                frm.doc.items.forEach(function(item) {
                    const original_item = frm.add_child('custom_purchasing_details_original');

                    // Custom field mapping
                    // original_item.product_name = item.item_name;
                    original_item.date = item.schedule_date;
                    original_item.po_no = frm.doc.name;

                    original_item.quantity = item.qty;
                    original_item.item_code=item.item_code;
                    original_item.item_name = item.item_name;
                    original_item.amount = item.amount || (item.qty * item.rate);
                });

                frm.refresh_field('custom_purchasing_details_original');

                frappe.show_alert({
                    message: __('Original items snapshot updated'),
                    indicator: 'green'
                }, 3);
            }
            
            
        }
        
        return validate_purchase_order(frm, true);
    },

    before_save: function(frm) {
        // Ensure schedule_date is set before saving
        set_schedule_date(frm);
        
        // Tell the system to ignore version conflicts
        frm.doc.__save_with_options = true;
        frm.doc.ignore_version = true;
    },

    // Consolidated after_save handler
    after_save: function(frm) {
        // First calculate GST
        frappe.call({
            method: "o2o_erpnext.api.purchase_order.calculate_gst_values",
            args: {
                "doc_name": frm.doc.name
            },
            callback: function(r) {
                // Then update budgets after GST calculation is complete
                frappe.call({
                    method: 'o2o_erpnext.api.purchase_order.update_budgets_for_po',
                    args: {
                        doc_name: frm.doc.name,
                        is_new: frm.doc.__islocal || frm.doc.__unsaved
                    },
                    callback: function(budget_r) {
                        if (budget_r.message) {
                            if (budget_r.message.status === 'success') {
                                if (budget_r.message.updates && budget_r.message.updates.length > 0) {
                                    budget_r.message.updates.forEach(update => {
                                        frappe.show_alert({
                                            message: __(update),
                                            indicator: 'green'
                                        }, 5);
                                    });
                                } else {
                                    // Show message even if no updates
                                    frappe.show_alert({
                                        message: __("Budget check completed"),
                                        indicator: 'blue'
                                    }, 3);
                                }
                            } else if (budget_r.message.status === 'error') {
                                frappe.show_alert({
                                    title: __('Budget Update Error'),
                                    message: __(budget_r.message.message),
                                    indicator: 'red'
                                });
                            }
                        }
                        
                        // Reload the document to show all changes
                        // frm.reload_doc();
                    }
                });
            }
        });
    },

    supplier: function(frm) {
        if(frm.doc.supplier) {
            // Clear vendor when supplier changes
            frm.set_value('custom_vendor', '');
            
            // Set new vendor filters
            set_vendor_filters(frm);
            
            // Check approval flow and clear requisition approver if needed
            frappe.db.get_value('Supplier', frm.doc.supplier, 'custom_approval_flow', (r) => {
                if (r && r.custom_approval_flow !== '3 way') {
                    // Clear requisition approver fields for non-3-way approval flow
                    frm.set_value('custom_requisition_approver_name_and_email', '');
                    frm.set_value('custom_requisition_approver_email', '');
                }
            });
        }
    },
    
    custom_branch: function(frm) {
        // Apply branch/sub-branch addresses when branch changes
        call_check_and_apply_branch_addresses(frm);
        
        // Protect address display after branch change
        setTimeout(() => {
            protect_address_display_fields(frm);
        }, 1000);
        
        if(frm.doc.custom_branch && !frm.doc.__islocal) {
            // Set branch approver
            frappe.call({
                method: 'o2o_erpnext.api.purchase_order.set_branch_approver_for_purchase_order',
                args: {
                    purchase_order_name: frm.doc.name
                },
                freeze: true,
                freeze_message: __('Finding Branch Approver...'),
                callback: function(r) {
                    if (r.message) {
                        if (r.message.status === 'success') {
                            frappe.show_alert({
                                message: __('Branch Approver set successfully'),
                                indicator: 'green'
                            }, 5);
                            // Refresh both the combined field and email-only field
                            frm.refresh_field('custom__approver_name_and_email');
                            frm.refresh_field('custom_po_approver_email');
                        } else if (r.message.status === 'warning') {
                            frappe.show_alert({
                                message: __(r.message.message),
                                indicator: 'orange'
                            }, 5);
                        } else if (r.message.status === 'error') {
                            frappe.throw(__(r.message.message));
                        }
                    }
                }
            });
            
            // Re-validate only for new documents
            if (frm.doc.__islocal) {
                validate_purchase_order(frm);
            }
        }
    },
    
    custom_sub_branch: function(frm) {
        // Apply branch/sub-branch addresses when sub-branch changes
        call_check_and_apply_branch_addresses(frm);
        
        // Protect address display after sub-branch change
        setTimeout(() => {
            protect_address_display_fields(frm);
        }, 1000);
        
        // Set requisition approver when sub-branch changes (for saved documents)
        if(frm.doc.custom_sub_branch && !frm.doc.__islocal && frm.doc.supplier) {
            // First check supplier's approval flow
            frappe.db.get_value('Supplier', frm.doc.supplier, 'custom_approval_flow', (r) => {
                if (r && r.custom_approval_flow === '3 way') {
                    // Only set requisition approver for 3-way approval flow
                    frappe.call({
                        method: 'o2o_erpnext.api.purchase_order.set_requisition_approver_for_purchase_order',
                        args: {
                            purchase_order_name: frm.doc.name
                        },
                        freeze: true,
                        freeze_message: __('Finding Requisition Approver...'),
                        callback: function(r) {
                            if (r.message) {
                                if (r.message.status === 'success') {
                                    frappe.show_alert({
                                        message: __('Requisition Approver set successfully'),
                                        indicator: 'green'
                                    }, 5);
                                    // Refresh both the combined field and email-only field
                                    frm.refresh_field('custom_requisition_approver_name_and_email');
                                    frm.refresh_field('custom_requisition_approver_email');
                                } else if (r.message.status === 'warning') {
                                    frappe.show_alert({
                                        message: __(r.message.message),
                                        indicator: 'orange'
                                    }, 5);
                                } else if (r.message.status === 'error') {
                                    frappe.throw(__(r.message.message));
                                }
                            }
                        }
                    });
                } else {
                    // For non-3-way approval, clear any existing requisition approver
                    frm.set_value('custom_requisition_approver_name_and_email', '');
                    frm.set_value('custom_requisition_approver_email', '');
                }
            });
        }
        
        // Re-validate only for new documents
        if (frm.doc.__islocal) {
            validate_purchase_order(frm);
        }
    },
    
    transaction_date: function(frm) {
        // Automatically set schedule_date when transaction_date changes
        set_schedule_date(frm);
        
        // Only validate for new documents
        if (frm.doc.__islocal) {
            validate_purchase_order(frm);
        }
    },
    
    company: function(frm) {
        // Clear shipping address filter when company changes
        clearShippingAddressFilter(frm);
    }
});

// Child table event handlers
frappe.ui.form.on('Purchase Order Item', {
    items_add: function(frm, cdt, cdn) {
        // Set schedule_date for newly added item from parent PO schedule_date
        let item = frappe.get_doc(cdt, cdn);
        if (frm.doc.schedule_date && !item.schedule_date) {
            frappe.model.set_value(cdt, cdn, 'schedule_date', frm.doc.schedule_date);
        }
        
        // Only validate for new documents
        if (frm.doc.__islocal) {
            validate_purchase_order(frm);
        }
    },
    
    items_remove: function(frm, cdt, cdn) {
        // Only validate for new documents
        if (frm.doc.__islocal) {
            validate_purchase_order(frm);
        }
    },
    
    custom_product_type: function(frm, cdt, cdn) {
        // Only validate for new documents
        if (frm.doc.__islocal) {
            validate_purchase_order(frm);
        }
    },
    
    amount: function(frm, cdt, cdn) {
        // Only validate for new documents - skip for quantity changes on existing POs
        if (frm.doc.__islocal) {
            validate_purchase_order(frm);
        }
    }
});

// Helper function to apply branch addresses server-side
function call_check_and_apply_branch_addresses(frm, async_false = false) {
    const sub_branch = frm.doc.custom_sub_branch;
    const branch = frm.doc.custom_branch;
    
    // Only proceed if we have either branch or sub-branch
    if (!sub_branch && !branch) return;
    
    frappe.call({
        method: 'o2o_erpnext.api.purchase_order.fetch_branch_or_sub_branch_addresses',
        args: {
            'purchase_order_name': frm.doc.__islocal ? null : frm.docname,
            'sub_branch': sub_branch,
            'branch': branch
        },
        async: !async_false, // Make synchronous if needed (for validation)
        callback: function(response) {
            if (response.message && response.message.status === 'success') {
                // If this is a new document, we'll set the values directly
                if (frm.doc.__islocal) {
                    if (response.message.billing_address) {
                        frm.set_value('supplier_address', response.message.billing_address);
                    }
                    if (response.message.shipping_address) {
                        frm.set_value('shipping_address', response.message.shipping_address);
                    }
                } else {
                    // For existing documents, the server has already updated the values
                    // We need to refresh both the address links and display fields
                    frm.refresh_fields(['supplier_address', 'shipping_address', 'address_display', 'shipping_address_display']);
                    
                    // Force protect our address display values from being overridden
                    setTimeout(() => {
                        protect_address_display_fields(frm);
                    }, 500);
                }
            }
        }
    });
}

// Function to protect address display fields from being overridden
function protect_address_display_fields(frm) {
    if (!frm.doc.custom_sub_branch && !frm.doc.custom_branch) {
        return;
    }
    
    // Get the correct address display content from server
    frappe.call({
        method: 'o2o_erpnext.api.purchase_order.get_correct_address_display',
        args: {
            sub_branch: frm.doc.custom_sub_branch,
            branch: frm.doc.custom_branch
        },
        callback: function(response) {
            if (response.message && response.message.status === 'success') {
                // Force set the correct address display values
                if (response.message.billing_display && frm.doc.address_display !== response.message.billing_display) {
                    frm.set_value('address_display', response.message.billing_display);
                }
                if (response.message.shipping_display && frm.doc.shipping_address_display !== response.message.shipping_display) {
                    frm.set_value('shipping_address_display', response.message.shipping_display);
                }
            }
        }
    });
}

// Simplified helper function - only for field change calculations
// All validation is now handled server-side in the validate hook
function validate_purchase_order(frm, is_save_attempt = false) {
    // Only show soft alerts during save attempts, not field changes
    if (!is_save_attempt) {
        return true; // Skip client-side validation for field changes
    }
    
    // For save attempts, let server-side validation handle everything
    // The validate hook will show proper error messages
    return true;
}

// Helper function to call server-side GST calculation
function call_calculate_gst_server(frm) {
    frappe.call({
        method: 'o2o_erpnext.api.purchase_order.calculate_gst_values',
        args: {
            doc_name: frm.doc.name
        },
        freeze: true,
        freeze_message: __('Calculating GST...'),
        callback: function(r) {
            if (r.message && r.message.status === 'success') {
                frappe.show_alert({
                    indicator: 'green'
                }, 5);
                frm.refresh();
            } else {
                frappe.show_alert({
                    message: __('Error calculating GST values'),
                    indicator: 'red'
                }, 5);
            }
        }
    });
}

// For new documents, preview GST calculation without saving
function calculate_gst_preview(frm) {
    // First prepare item data to send to server
    const items = frm.doc.items || [];
    if (items.length === 0) {
        frappe.show_alert({
            message: __('No items to calculate GST for'),
            indicator: 'orange'
        }, 5);
        return;
    }
    
    const items_data = items.map(item => ({
        name: item.name,
        sgst_amount: item.sgst_amount || 0,
        cgst_amount: item.cgst_amount || 0,
        igst_amount: item.igst_amount || 0,
        net_amount: item.net_amount || 0
    }));
    
    frappe.call({
        method: 'o2o_erpnext.api.purchase_order.calculate_item_gst_values',
        args: {
            items_json: JSON.stringify(items_data)
        },
        freeze: true,
        freeze_message: __('Calculating GST...'),
        callback: function(r) {
            if (r.message && r.message.status === 'success' && r.message.data) {
                // Update the local doc with calculated values
                for (const calc_item of r.message.data) {
                    const local_item = frm.doc.items.find(i => i.name === calc_item.name);
                    if (local_item) {
                        local_item.custom_gstn_value = calc_item.custom_gstn_value;
                        local_item.custom_grand_total = calc_item.custom_grand_total;
                    }
                }
                frm.refresh_field('items');
                frappe.show_alert({
                    message: __('GST values calculated'),
                    indicator: 'green'
                }, 5);
            } else {
                frappe.show_alert({
                    message: __('Error calculating GST values'),
                    indicator: 'red'
                }, 5);
            }
        }
    });
}

// Function to set vendor filters
function set_vendor_filters(frm) {
    frappe.call({
        method: 'o2o_erpnext.api.purchase_order.get_supplier_vendors',
        args: {
            supplier: frm.doc.supplier
        },
        callback: function(r) {
            if(r.message) {
                let allowed_vendors = r.message;
                
                // Set filters on vendor field
                frm.set_query('custom_vendor', function() {
                    return {
                        filters: {
                            'name': ['in', allowed_vendors.length ? allowed_vendors : ['NONE']]
                        }
                    };
                });
            }
        }
    });
}

// Budget Transaction functionality for Purchase Order
frappe.ui.form.on('Purchase Order', {
    refresh: function(frm) {
        // Only add dashboard for existing documents
        if (!frm.doc.__islocal) {
            // Add budget display section
            try {
                frm.dashboard.add_section(
                    `<div class="row">
                        <div class="col-xs-6">
                            <div style="border: 1px solid #d1d8dd; border-radius: 4px; padding: 10px; text-align: center; background-color: #f5f7fa; margin: 5px;">
                                <div style="font-weight: bold; color: #8d99a6;">CAPEX Budget Used</div>
                                <div style="font-size: 16px; font-weight: bold;">${frappe.format(frm.doc.custom_last_capex_total || 0, {fieldtype: "Currency"})}</div>
                            </div>
                        </div>
                        <div class="col-xs-6">
                            <div style="border: 1px solid #d1d8dd; border-radius: 4px; padding: 10px; text-align: center; background-color: #f5f7fa; margin: 5px;">
                                <div style="font-weight: bold; color: #8d99a6;">OPEX Budget Used</div>
                                <div style="font-size: 16px; font-weight: bold;">${frappe.format(frm.doc.custom_last_opex_total || 0, {fieldtype: "Currency"})}</div>
                            </div>
                        </div>
                    </div>`
                );
                
                // Add button to view budget transactions
                if (frm.doc.custom_budget_transactions) {
                    frm.add_custom_button(__('View Budget Transactions'), function() {
                        frappe.route_options = {
                            "reference_doctype": "Purchase Order",
                            "reference_name": frm.doc.name
                        };
                        frappe.set_route("List", "Budget Transaction");
                    }, __("Budget"));
                }
            } catch (e) {
                console.error("Error rendering budget dashboard:", e);
            }
        }
    },

    after_save: function(frm) {
        // Call the budget update function
        frappe.call({
            method: 'o2o_erpnext.api.purchase_order.update_budgets_for_po',
            args: {
                doc_name: frm.doc.name,
                is_new: frm.doc.__islocal
            },
            callback: function(r) {
                if (r.message && r.message.status === 'success') {
                    // Display budget updates
                    if (r.message.updates && r.message.updates.length > 0) {
                        r.message.updates.forEach(update => {
                            frappe.show_alert({
                                message: __(update),
                                indicator: 'green'
                            }, 5);
                        });
                    }
                    
                    // Refresh the form
                    // frm.reload_doc();
                }
            }
        });
    }
});

function set_schedule_date(frm) {
    // For new documents, if transaction_date is not set, set it to today
    if(frm.doc.__islocal && !frm.doc.transaction_date) {
        let today = frappe.datetime.get_today();
        frm.set_value('transaction_date', today);
    }
    
    if(frm.doc.transaction_date) {
        // Calculate schedule_date as transaction_date + 20 days
        let transaction_date = frappe.datetime.str_to_obj(frm.doc.transaction_date);
        let schedule_date = new Date(transaction_date);
        schedule_date.setDate(schedule_date.getDate() + 20);
        
        // Format date to yyyy-mm-dd
        let formatted_date = frappe.datetime.obj_to_str(schedule_date);
        
        // Only set if different to avoid triggering unnecessary events
        if(frm.doc.schedule_date != formatted_date) {
            frm.set_value('schedule_date', formatted_date);
            frappe.show_alert(__('Schedule Date set to {0} (Transaction Date + 20 days)', [formatted_date]));
            
            // Also update schedule_date for all items
            if(frm.doc.items && frm.doc.items.length > 0) {
                frm.doc.items.forEach(function(item) {
                    frappe.model.set_value(item.doctype, item.name, 'schedule_date', formatted_date);
                });
                frm.refresh_field('items');
            }
        }
    }
}

function clearShippingAddressFilter(frm) {
    // Method to override only the shipping_address filtering

    // For shipping_address only
    frm.set_query("shipping_address", function() {
        return {
            query: "frappe.contacts.doctype.address.address.address_query",
            filters: {} // Empty filters to show all addresses
        };
    });

    // Clear any cached queries for shipping_address
    if(frm.fields_dict.shipping_address) {
        frm.fields_dict.shipping_address.get_query = function() {
            return {
                query: "frappe.contacts.doctype.address.address.address_query",
                filters: {}
            };
        };
    }

    // Force UI refresh of the shipping_address field
    frm.refresh_field("shipping_address");
}