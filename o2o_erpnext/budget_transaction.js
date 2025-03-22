// Budget Management Module
var o2o_erpnext = o2o_erpnext || {};
o2o_erpnext.budget = {
    // Process budget updates for Purchase Order
    updatePOBudget: function(doc_name, is_new, callback) {
        frappe.call({
            method: 'o2o_erpnext.api.purchase_order.update_budgets_for_po',
            args: {
                doc_name: doc_name,
                is_new: is_new
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
                    
                    // Show transaction information
                    if (r.message.transactions && r.message.transactions.length > 0) {
                        // Show a summary notification
                        frappe.show_alert({
                            message: __(`${r.message.transactions.length} budget transactions recorded`),
                            indicator: 'blue'
                        }, 5);
                    }
                    
                    // Call the callback if provided
                    if (callback && typeof callback === 'function') {
                        callback(r);
                    }
                } else if (r.message && r.message.status === 'error') {
                    frappe.msgprint({
                        title: __('Budget Update Error'),
                        message: __(r.message.message),
                        indicator: 'red'
                    });
                }
            }
        });
    },
    
    // Show budget dashboard for Purchase Order
    showBudgetDashboard: function(frm) {
        if (!frm.doc.__islocal) {
            // Add budget indicators to the form
            frm.dashboard.add_section(
                `<div style="margin-bottom: 20px;">
                    <div class="dashboard-section">
                        <div class="section-head">Budget Information</div>
                        <div class="row" style="margin-top: 10px;">
                            <div class="col-xs-6">
                                <div style="border: 1px solid #d1d8dd; border-radius: 4px; padding: 10px; text-align: center; background-color: #f5f7fa;">
                                    <div style="font-weight: bold; color: #8d99a6; margin-bottom: 5px;">CAPEX Budget Used</div>
                                    <div style="font-size: 16px; font-weight: bold;">${frappe.format(frm.doc.custom_last_capex_total || 0, {fieldtype: "Currency"})}</div>
                                </div>
                            </div>
                            <div class="col-xs-6">
                                <div style="border: 1px solid #d1d8dd; border-radius: 4px; padding: 10px; text-align: center; background-color: #f5f7fa;">
                                    <div style="font-weight: bold; color: #8d99a6; margin-bottom: 5px;">OPEX Budget Used</div>
                                    <div style="font-size: 16px; font-weight: bold;">${frappe.format(frm.doc.custom_last_opex_total || 0, {fieldtype: "Currency"})}</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>`
            );
            
            // Add button to view budget transactions if this is a saved document
            if (frm.doc.custom_budget_transactions) {
                frm.add_custom_button(__('View Budget Transactions'), function() {
                    frappe.route_options = {
                        "reference_doctype": "Purchase Order",
                        "reference_name": frm.doc.name
                    };
                    frappe.set_route("List", "Budget Transaction");
                }, __("Budget"));
            }
        }
    },
    
    // View budget transactions for a specific document
    viewTransactions: function(doctype, docname) {
        frappe.route_options = {
            "reference_doctype": doctype,
            "reference_name": docname
        };
        frappe.set_route("List", "Budget Transaction");
    }
};

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

        // Only run defaults for new documents
        if (!frm.doc.__islocal) {
            // Set form fields based on role
            frappe.call({
                method: 'o2o_erpnext.api.purchase_order.is_branch_level_user',
                callback: function(r) {
                    const isBranchUser = r.message;
                    
                    if (isBranchUser) {
                        frm.set_df_property('custom_sub_branch', 'reqd', 0);
                    } else {
                        frm.set_df_property('custom_sub_branch', 'reqd', 1);
                    }
                }
            });
            
            // Show budget dashboard for existing documents
            o2o_erpnext.budget.showBudgetDashboard(frm);
            
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
    },

    validate: function(frm) {
        frm.set_value("custom_created_user", frm.doc.owner);
        return validate_purchase_order(frm);
    },

    before_save: function(frm) {
        // Tell the system to ignore version conflicts
        frm.doc.__save_with_options = true;
        frm.doc.ignore_version = true;
    },

    after_save: function(frm) {
        // Call the budget update function from the module
        o2o_erpnext.budget.updatePOBudget(frm.doc.name, frm.doc.__islocal, function() {
            // Call GST calculation after budget update
            frappe.call({
                method: "o2o_erpnext.api.purchase_order.calculate_gst_values",
                args: {
                    "doc_name": frm.doc.name
                },
                callback: function(r) {
                    if (r.message && r.message.status === "success") {
                        // Refresh the form to show the updated values
                        frm.reload_doc();
                    } else if (r.message && r.message.status === "error") {
                        frappe.msgprint({
                            title: __("Error"),
                            indicator: 'red',
                            message: r.message.message
                        });
                    }
                }
            });
        });
    },

    supplier: function(frm) {
        if(frm.doc.supplier) {
            // Clear vendor when supplier changes
            frm.set_value('custom_vendor', '');
            
            // Set new vendor filters
            set_vendor_filters(frm);
        }
    },
    
    custom_branch: function(frm) {
        // Apply branch/sub-branch addresses when branch changes
        call_check_and_apply_branch_addresses(frm);
        
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
                            frm.refresh_field('custom__approver_name_and_email');
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
            
            // Re-validate
            validate_purchase_order(frm);
        }
    },
    
    custom_sub_branch: function(frm) {
        // Apply branch/sub-branch addresses when sub-branch changes
        call_check_and_apply_branch_addresses(frm);
        
        // Re-validate
        validate_purchase_order(frm);
    },
    
    transaction_date: function(frm) {
        validate_purchase_order(frm);
    }
});

// Child table event handlers
frappe.ui.form.on('Purchase Order Item', {
    items_add: function(frm, cdt, cdn) {
        validate_purchase_order(frm);
    },
    
    items_remove: function(frm, cdt, cdn) {
        validate_purchase_order(frm);
    },
    
    custom_product_type: function(frm, cdt, cdn) {
        validate_purchase_order(frm);
    },
    
    amount: function(frm, cdt, cdn) {
        validate_purchase_order(frm);
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
                    // We just need to refresh the form fields silently
                    frm.refresh_fields(['supplier_address', 'shipping_address']);
                }
            }
        }
    });
}

// Helper function to validate purchase order
function validate_purchase_order(frm) {
    if (frm.doc.__islocal) {
        // For unsaved documents, validate client-side
        frappe.call({
            method: 'o2o_erpnext.api.purchase_order.validate_purchase_order',
            args: {
                doc_json: JSON.stringify(frm.doc)
            },
            async: false,
            callback: function(r) {
                if (r.message) {
                    if (r.message.status === 'error') {
                        if (r.message.message) {
                            frappe.msgprint({
                                title: __('Validation Error'),
                                message: __(r.message.message),
                                indicator: 'red'
                            });
                            frappe.validated = false;
                            return false;
                        }
                    }
                    
                    // Check individual validations
                    if (r.message.validations) {
                        for (const key in r.message.validations) {
                            const validation = r.message.validations[key];
                            if (validation.status === 'error') {
                                frappe.msgprint({
                                    title: __('Validation Error'),
                                    message: __(validation.message),
                                    indicator: 'red'
                                });
                                frappe.validated = false;
                                return false;
                            }
                        }
                    }
                    
                    // Store CAPEX/OPEX totals for budget updates
                    storedCapexTotal = r.message.capex_total || 0;
                    storedOpexTotal = r.message.opex_total || 0;
                }
            }
        });
    } else {
        // For saved documents, validate on server
        frappe.call({
            method: 'o2o_erpnext.api.purchase_order.validate_purchase_order',
            args: {
                doc_name: frm.doc.name
            },
            async: false,
            callback: function(r) {
                if (r.message) {
                    if (r.message.status === 'error') {
                        if (r.message.message) {
                            frappe.msgprint({
                                title: __('Validation Error'),
                                message: __(r.message.message),
                                indicator: 'red'
                            });
                            frappe.validated = false;
                            return false;
                        }
                    }
                    
                    // Check individual validations
                    if (r.message.validations) {
                        for (const key in r.message.validations) {
                            const validation = r.message.validations[key];
                            if (validation.status === 'error') {
                                frappe.msgprint({
                                    title: __('Validation Error'),
                                    message: __(validation.message),
                                    indicator: 'red'
                                });
                                frappe.validated = false;
                                return false;
                            }
                        }
                    }
                    
                    // Store CAPEX/OPEX totals for budget updates
                    storedCapexTotal = r.message.capex_total || 0;
                    storedOpexTotal = r.message.opex_total || 0;
                }
            }
        });
    }
    
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
                   // message: __('GST values calculated successfully'),
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