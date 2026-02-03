frappe.ui.form.on('Purchase Invoice', {
    refresh: function(frm) {
        // Add the "Edit Submitted Items" button only for submitted Purchase Invoices
        if (frm.doc.docstatus === 1 && frm.doc.items && frm.doc.items.length > 0) {
            frm.add_custom_button(__('Edit Submitted Items'), function() {
                show_pi_items_editor(frm);
            }, __('Actions'));
        }
    }
});

function show_pi_items_editor(frm) {
    // Create dialog with dashboard UI
    let dialog = new frappe.ui.Dialog({
        title: __('Edit Purchase Invoice Items - {0}', [frm.doc.name]),
        size: 'large',
        fields: [
            {
                fieldname: 'search_items',
                fieldtype: 'Data',
                label: __('Search Items'),
                description: __('Search by item name, code, or description'),
                change: function() {
                    filter_items(dialog, frm);
                }
            },
            {
                fieldname: 'items_section',
                fieldtype: 'Section Break',
                label: __('Items ({0})', [frm.doc.items ? frm.doc.items.length : 0])
            },
            {
                fieldname: 'items_html',
                fieldtype: 'HTML'
            }
        ]
    });

    // Show loading message
    dialog.fields_dict.items_html.$wrapper.html(`
        <div class="text-center" style="padding: 40px;">
            <div class="spinner-border text-primary" role="status">
                <span class="sr-only">Loading...</span>
            </div>
            <p class="mt-3">${__('Loading Purchase Invoice items...')}</p>
        </div>
    `);

    // Load items after dialog is shown
    dialog.show();
    load_pi_items(frm, dialog);

    // Add save and cancel buttons
    dialog.set_primary_action(__('Save Changes'), function() {
        save_pi_item_changes(frm, dialog);
    });

    dialog.add_custom_action(__('Cancel'), function() {
        dialog.hide();
    });

    return dialog;
}

function load_pi_items(frm, dialog) {
    try {
        let items_html = `
            <style>
                .pi-items-container {
                    max-height: 500px;
                    overflow-y: auto;
                    padding: 10px;
                }
                .pi-item-card {
                    border: 1px solid #d1d8dd;
                    border-radius: 8px;
                    margin-bottom: 15px;
                    padding: 15px;
                    background: #f8f9fa;
                    transition: all 0.3s ease;
                }
                .pi-item-card:hover {
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                }
                .pi-item-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 10px;
                }
                .pi-item-title {
                    font-weight: 600;
                    font-size: 14px;
                    color: #36414c;
                }
                .pi-item-code {
                    font-size: 12px;
                    color: #8492a6;
                    margin-top: 2px;
                }
                .pi-item-fields {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 10px;
                    margin-bottom: 10px;
                }
                .pi-field-group {
                    display: flex;
                    flex-direction: column;
                }
                .pi-field-label {
                    font-size: 11px;
                    color: #8492a6;
                    margin-bottom: 4px;
                    font-weight: 500;
                }
                .pi-field-input {
                    padding: 6px 8px;
                    border: 1px solid #d1d8dd;
                    border-radius: 4px;
                    font-size: 12px;
                    transition: border-color 0.2s;
                }
                .pi-field-input:focus {
                    outline: none;
                    border-color: #5e64ff;
                    box-shadow: 0 0 0 2px rgba(94, 100, 255, 0.1);
                }
                .pi-field-input:disabled {
                    background: #f7f7f7;
                    cursor: not-allowed;
                }
                .pi-item-stats {
                    display: flex;
                    gap: 15px;
                    flex-wrap: wrap;
                    font-size: 11px;
                }
                .pi-stat {
                    display: flex;
                    flex-direction: column;
                }
                .pi-stat-label {
                    color: #8492a6;
                    margin-bottom: 2px;
                }
                .pi-stat-value {
                    font-weight: 600;
                    color: #36414c;
                }
                .pi-no-items {
                    text-align: center;
                    padding: 40px;
                    color: #95a5a6;
                    font-size: 16px;
                }
                .pi-changed {
                    background-color: #fff3cd;
                    border-left: 4px solid #ffc107;
                }
                .pi-deleted {
                    background-color: #f8d7da;
                    border-left: 4px solid #dc3545;
                    opacity: 0.6;
                }
                .pi-delete-btn {
                    font-size: 12px;
                    padding: 4px 8px;
                }
                .pi-summary-box {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    border-radius: 8px;
                    padding: 20px;
                    margin-bottom: 20px;
                }
                .pi-summary-title {
                    font-weight: 600;
                    font-size: 18px;
                    margin-bottom: 15px;
                }
                .pi-summary-stats {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                    gap: 15px;
                }
                .pi-summary-stat {
                    text-align: center;
                }
                .pi-summary-value {
                    font-size: 24px;
                    font-weight: 700;
                    margin-bottom: 5px;
                }
                .pi-summary-label {
                    font-size: 12px;
                    opacity: 0.9;
                }
            </style>
            <div class="pi-items-container">
        `;

        // Add summary section
        items_html += `
            <div class="pi-summary-box">
                <div class="pi-summary-title">📊 Purchase Invoice Summary</div>
                <div class="pi-summary-stats">
                    <div class="pi-summary-stat">
                        <div class="pi-summary-value">${frm.doc.items ? frm.doc.items.length : 0}</div>
                        <div class="pi-summary-label">Total Items</div>
                    </div>
                    <div class="pi-summary-stat">
                        <div class="pi-summary-value">${format_currency(frm.doc.total || 0, frm.doc.currency)}</div>
                        <div class="pi-summary-label">Total Amount</div>
                    </div>
                    <div class="pi-summary-stat">
                        <div class="pi-summary-value">${format_currency(frm.doc.grand_total || 0, frm.doc.currency)}</div>
                        <div class="pi-summary-label">Grand Total</div>
                    </div>
                    <div class="pi-summary-stat">
                        <div class="pi-summary-value">${frm.doc.supplier || 'N/A'}</div>
                        <div class="pi-summary-label">Supplier</div>
                    </div>
                </div>
            </div>
        `;

        if (!frm.doc.items || frm.doc.items.length === 0) {
            items_html += `
                <div class="pi-no-items">
                    <div class="text-muted">
                        <i class="fa fa-inbox fa-3x mb-3"></i>
                        <p>${__('No items found in this Purchase Invoice')}</p>
                    </div>
                </div>
            `;
        } else {
            frm.doc.items.forEach((item, idx) => {
                items_html += build_pi_item_card(item, idx, frm);
            });
        }

        items_html += `</div>`;
        
        dialog.fields_dict.items_html.$wrapper.html(items_html);
        
        // Add event handlers after HTML is rendered
        setTimeout(function() {
            add_pi_event_handlers(frm, dialog);
        }, 100);
        
    } catch (error) {
        console.error('Error loading PI items:', error);
        dialog.fields_dict.items_html.$wrapper.html(`
            <div class="alert alert-danger">
                <strong>${__('Error')}</strong>: ${__('Failed to load Purchase Invoice items')}
                <br><small>${error.message}</small>
            </div>
        `);
    }
}

function build_pi_item_card(item, idx, frm) {
    // Calculate derived values
    let amount = (item.qty || 0) * (item.rate || 0);
    
    return `
        <div class="pi-item-card" data-idx="${idx}" data-item-name="${item.name}">
            <div class="pi-item-header">
                <div>
                    <div class="pi-item-title">${item.item_name || item.item_code}</div>
                    <div class="pi-item-code">📦 ${item.item_code || 'N/A'} | 📏 ${item.uom || 'N/A'}</div>
                </div>
                <div>
                    <button type="button" class="btn btn-danger btn-sm pi-delete-btn" data-item-name="${item.name}" data-idx="${idx}">
                        🗑️ Delete
                    </button>
                </div>
            </div>
            
            <div class="pi-item-fields">
                <!-- Quantity -->
                <div class="pi-field-group">
                    <label class="pi-field-label">📊 Quantity</label>
                    <input type="number" 
                           class="pi-field-input" 
                           data-fieldname="qty" 
                           data-idx="${idx}"
                           value="${item.qty || 0}"
                           step="0.01"
                           min="0">
                </div>
                
                <!-- Unit Rate -->
                <div class="pi-field-group">
                    <label class="pi-field-label">💰 Unit Rate</label>
                    <input type="number" 
                           class="pi-field-input" 
                           data-fieldname="rate" 
                           data-idx="${idx}"
                           value="${item.rate || 0}"
                           step="0.01"
                           min="0">
                </div>
                
                <!-- Calculated Amount (Read-only) -->
                <div class="pi-field-group">
                    <label class="pi-field-label">💵 Amount</label>
                    <input type="text" 
                           class="pi-field-input pi-amount-display" 
                           value="${format_currency(amount, frm.doc.currency)}"
                           disabled>
                </div>
                
                <!-- GSTN Value (Read-only) -->
                <div class="pi-field-group">
                    <label class="pi-field-label">🏷️ GSTN Value</label>
                    <input type="text" 
                           class="pi-field-input pi-gstn-display" 
                           value="${format_currency(item.custom_gstn_value || 0, frm.doc.currency)}"
                           disabled>
                </div>
                
                <!-- Grand Total (Read-only) -->
                <div class="pi-field-group">
                    <label class="pi-field-label">💎 Grand Total</label>
                    <input type="text" 
                           class="pi-field-input pi-grand-total-display" 
                           value="${format_currency(item.custom_grand_total || amount, frm.doc.currency)}"
                           disabled>
                </div>
            </div>
            
            <div class="pi-item-stats">
                <div class="pi-stat">
                    <span class="pi-stat-label">📦 Received Qty</span>
                    <span class="pi-stat-value">${item.received_qty || 0}</span>
                </div>
                <div class="pi-stat">
                    <span class="pi-stat-label">🧾 Billed Amount</span>
                    <span class="pi-stat-value">${format_currency(item.billed_amt || 0, frm.doc.currency)}</span>
                </div>
                <div class="pi-stat">
                    <span class="pi-stat-label">📋 Item Group</span>
                    <span class="pi-stat-value">${item.item_group || 'N/A'}</span>
                </div>
            </div>
        </div>
    `;
}

function add_pi_event_handlers(frm, dialog) {
    // Add change detection
    $('.pi-field-input').on('change', function() {
        $(this).closest('.pi-item-card').addClass('pi-changed');
    });

    // Add real-time calculation on rate/qty change with percentage-wise GST logic
    $('.pi-field-input[data-fieldname="qty"], .pi-field-input[data-fieldname="rate"]').on('input', function() {
        let $card = $(this).closest('.pi-item-card');
        let qty = parseFloat($card.find('[data-fieldname="qty"]').val()) || 0;
        let rate = parseFloat($card.find('[data-fieldname="rate"]').val()) || 0;
        let amount = qty * rate;
        
        // Get the item index to fetch tax template
        let idx = $card.data('idx');
        let item = frm.doc.items[idx];
        let template = item ? (item.item_tax_template || "") : "";
        
        // Extract GST rate from template name (same logic as server-side)
        let gst_rate = 0;
        if (template.includes("GST 5%")) {
            gst_rate = 5;
        } else if (template.includes("GST 12%")) {
            gst_rate = 12;
        } else if (template.includes("GST 18%")) {
            gst_rate = 18;
        } else if (template.includes("GST 28%")) {
            gst_rate = 28;
        }
        
        // Calculate GST value if applicable
        let gstn_value = 0;
        if (gst_rate > 0) {
            gstn_value = Math.round(amount * gst_rate / 100 * 100) / 100; // Round to 2 decimal places
        }
        
        let grand_total = amount + gstn_value;
        
        // Update the displays
        $card.find('.pi-amount-display').val(format_currency(amount, frm.doc.currency));
        $card.find('.pi-gstn-display').val(format_currency(gstn_value, frm.doc.currency));
        $card.find('.pi-grand-total-display').val(format_currency(grand_total, frm.doc.currency));
        $card.addClass('pi-changed');
    });

    // Add delete button functionality
    $('.pi-delete-btn').on('click', function() {
        let $card = $(this).closest('.pi-item-card');
        let item_name = $(this).data('item-name');
        let item_title = $card.find('.pi-item-title').text();
        
        frappe.confirm(
            __('Are you sure you want to delete item "{0}"?', [item_title]),
            function() {
                // Mark card as deleted
                $card.addClass('pi-deleted').hide();
                $card.attr('data-deleted', 'true');
            }
        );
    });
}

function save_pi_item_changes(frm, dialog) {
    let changes = [];
    let deleted_items = [];
    
    // Collect deleted items
    $('.pi-item-card[data-deleted="true"]').each(function() {
        let item_name = $(this).data('item-name');
        deleted_items.push(item_name);
    });
    
    // Collect all changes from the dialog (excluding deleted items)
    $('.pi-field-input').each(function() {
        let $input = $(this);
        let $card = $input.closest('.pi-item-card');
        
        // Skip deleted items
        if ($card.attr('data-deleted') === 'true') return;
        
        let idx = $input.data('idx');
        let fieldname = $input.data('fieldname');
        
        // Skip if no fieldname (like amount display which is disabled)
        if (!fieldname) return;
        
        let new_value = $input.val();
        
        // Get the original value
        let original_value = frm.doc.items[idx][fieldname];
        
        // Convert to appropriate type
        if ($input.attr('type') === 'number') {
            new_value = parseFloat(new_value) || 0;
            original_value = parseFloat(original_value) || 0;
        }
        
        // Check if value has changed
        if (new_value != original_value) {
            if (!changes[idx]) {
                changes[idx] = {
                    name: frm.doc.items[idx].name,
                    changes: {}
                };
            }
            changes[idx].changes[fieldname] = new_value;
        }
    });
    
    // Filter out empty entries
    changes = changes.filter(item => item !== undefined);
    
    if (changes.length === 0 && deleted_items.length === 0) {
        frappe.msgprint({
            title: __('No Changes'),
            message: __('No changes detected. Please modify quantities/rates or delete items to save.'),
            indicator: 'blue'
        });
        return;
    }
    
    // Show confirmation dialog
    let message = '';
    if (changes.length > 0 && deleted_items.length > 0) {
        message = __('You are about to update {0} item(s) and delete {1} item(s) in Purchase Invoice {2}. Do you want to continue?', 
                    [changes.length, deleted_items.length, frm.doc.name]);
    } else if (changes.length > 0) {
        message = __('You are about to update {0} item(s) in Purchase Invoice {1}. Do you want to continue?', 
                    [changes.length, frm.doc.name]);
    } else {
        message = __('You are about to delete {0} item(s) from Purchase Invoice {1}. Do you want to continue?', 
                    [deleted_items.length, frm.doc.name]);
    }
    
    frappe.confirm(message, function() {
        // User confirmed, proceed with update
        update_pi_items(frm, changes, deleted_items, dialog);
    });
}

function update_pi_items(frm, changes, deleted_items, dialog) {
    // Call the API method from your custom app
    frappe.call({
        method: 'o2o_erpnext.api.purchase_invoice.update_submitted_pi_items',
        freeze: true,
        freeze_message: __('Updating Purchase Invoice Items...'),
        args: {
            items_data: changes,
            deleted_items: deleted_items
        },
        callback: function(r) {
            if (!r.exc && r.message) {
                if (r.message.status === 'success') {
                    frappe.show_alert({
                        message: `✅ ${r.message.message}`,
                        indicator: 'green'
                    }, 7);
                    
                    dialog.hide();
                    
                    // Reload document after short delay
                    setTimeout(function() {
                        frm.reload_doc();
                    }, 500);
                } else {
                    frappe.msgprint({
                        title: __('Update Failed'),
                        message: r.message.message || __('Unknown error occurred'),
                        indicator: 'red'
                    });
                }
            } else if (r.exc) {
                frappe.msgprint({
                    title: __('Error'),
                    message: r.exc || __('Failed to update items'),
                    indicator: 'red'
                });
            } else {
                frappe.msgprint({
                    title: __('Error'),
                    message: __('No response from server'),
                    indicator: 'red'
                });
            }
        },
        error: function(r) {
            console.error('Error updating items:', r);
            let error_message = __('Failed to update items. Please check console for details.');
            
            if (r.responseText) {
                try {
                    let error_data = JSON.parse(r.responseText);
                    if (error_data.message) {
                        error_message = error_data.message;
                    }
                } catch (e) {
                    // Keep default message
                }
            }
            
            frappe.msgprint({
                title: __('Error'),
                message: error_message,
                indicator: 'red'
            });
        }
    });
}

function filter_items(dialog, frm) {
    let search_term = dialog.get_value('search_items');
    if (!search_term) {
        // Show all items
        $('.pi-item-card').show();
        return;
    }
    
    search_term = search_term.toLowerCase();
    
    $('.pi-item-card').each(function() {
        let $card = $(this);
        let item_name = $card.find('.pi-item-title').text().toLowerCase();
        let item_code = $card.find('.pi-item-code').text().toLowerCase();
        
        if (item_name.includes(search_term) || item_code.includes(search_term)) {
            $card.show();
        } else {
            $card.hide();
        }
    });
}

// Utility function for currency formatting
function format_currency(value, currency) {
    if (!value) value = 0;
    return frappe.format(value, {fieldtype: 'Currency', options: currency || 'INR'});
}