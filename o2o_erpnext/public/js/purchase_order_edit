frappe.ui.form.on('Purchase Order', {
    refresh: function(frm) {
        // Only show the button if the document is submitted
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__('Edit Submitted Items'), function() {
                show_edit_items_dialog(frm);
            }, __('Actions'));
        }
    }
});

function show_edit_items_dialog(frm) {
    // Create a dialog with a dashboard-like interface
    let dialog = new frappe.ui.Dialog({
        title: __('Edit Purchase Order Items - {0}', [frm.doc.name]),
        size: 'extra-large',
        fields: [
            {
                fieldname: 'items_html',
                fieldtype: 'HTML'
            }
        ],
        primary_action_label: __('Save Changes'),
        primary_action: function(values) {
            save_item_changes(frm, dialog);
        },
        secondary_action_label: __('Cancel'),
        secondary_action: function() {
            dialog.hide();
        }
    });

    // Build the dashboard HTML
    build_items_dashboard(frm, dialog);
    
    dialog.show();
}

function build_items_dashboard(frm, dialog) {
    let html = `
        <div class="po-items-dashboard">
            <style>
                .po-items-dashboard {
                    padding: 15px;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                }
                .po-item-card {
                    border: 1px solid #d1d8dd;
                    border-radius: 8px;
                    padding: 15px;
                    margin-bottom: 15px;
                    background: #f8f9fa;
                    transition: all 0.3s ease;
                }
                .po-item-card:hover {
                    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                    transform: translateY(-2px);
                }
                .po-item-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 15px;
                    padding-bottom: 10px;
                    border-bottom: 2px solid #e0e0e0;
                }
                .po-item-title {
                    font-size: 16px;
                    font-weight: 600;
                    color: #2c3e50;
                }
                .po-item-code {
                    font-size: 12px;
                    color: #7f8c8d;
                    margin-top: 3px;
                }
                .po-item-fields {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 15px;
                }
                .po-field-group {
                    display: flex;
                    flex-direction: column;
                }
                .po-field-label {
                    font-size: 12px;
                    color: #6c757d;
                    margin-bottom: 5px;
                    font-weight: 500;
                }
                .po-field-input {
                    padding: 8px 10px;
                    border: 1px solid #ced4da;
                    border-radius: 4px;
                    font-size: 14px;
                    transition: border-color 0.3s ease;
                }
                .po-field-input:focus {
                    outline: none;
                    border-color: #4e73df;
                    box-shadow: 0 0 0 0.2rem rgba(78, 115, 223, 0.25);
                }
                .po-field-input:disabled {
                    background-color: #e9ecef;
                    cursor: not-allowed;
                }
                .po-item-stats {
                    display: flex;
                    gap: 20px;
                    margin-top: 15px;
                    padding-top: 10px;
                    border-top: 1px solid #e0e0e0;
                }
                .po-stat {
                    display: flex;
                    flex-direction: column;
                }
                .po-stat-label {
                    font-size: 11px;
                    color: #95a5a6;
                    margin-bottom: 3px;
                }
                .po-stat-value {
                    font-size: 14px;
                    font-weight: 600;
                    color: #2c3e50;
                }
                .po-amount-value {
                    color: #27ae60;
                }
                .po-search-box {
                    margin-bottom: 20px;
                    padding: 15px;
                    background: #fff;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                .po-search-input {
                    width: 100%;
                    padding: 12px 15px;
                    border: 1px solid #ced4da;
                    border-radius: 6px;
                    font-size: 14px;
                }
                .po-no-items {
                    text-align: center;
                    padding: 40px;
                    color: #95a5a6;
                    font-size: 16px;
                }
                .po-changed {
                    background-color: #fff3cd;
                    border-left: 4px solid #ffc107;
                }
                .po-deleted {
                    background-color: #f8d7da;
                    border-left: 4px solid #dc3545;
                    opacity: 0.6;
                }
                .po-delete-btn {
                    font-size: 12px;
                    padding: 4px 8px;
                }
                .po-summary-box {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    border-radius: 8px;
                    padding: 20px;
                    margin-bottom: 20px;
                }
                .po-summary-title {
                    font-weight: 600;
                    font-size: 18px;
                    margin-bottom: 15px;
                }
                .po-summary-stats {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                    gap: 20px;
                }
                .po-summary-stat {
                    text-align: center;
                }
                .po-summary-stat-value {
                    font-size: 24px;
                    font-weight: bold;
                    display: block;
                }
                .po-summary-stat-label {
                    font-size: 12px;
                    opacity: 0.9;
                }
            </style>
            
            <div class="po-summary-box">
                <div class="po-summary-title">📋 Purchase Order: ${frm.doc.name}</div>
                <div class="po-summary-stats">
                    <div class="po-summary-stat">
                        <span class="po-summary-stat-value">${frm.doc.items ? frm.doc.items.length : 0}</span>
                        <span class="po-summary-stat-label">Total Items</span>
                    </div>
                    <div class="po-summary-stat">
                        <span class="po-summary-stat-value">${frm.doc.total_qty || 0}</span>
                        <span class="po-summary-stat-label">Total Quantity</span>
                    </div>
                    <div class="po-summary-stat">
                        <span class="po-summary-stat-value">${format_currency(frm.doc.grand_total || 0, frm.doc.currency)}</span>
                        <span class="po-summary-stat-label">Grand Total</span>
                    </div>
                    <div class="po-summary-stat">
                        <span class="po-summary-stat-value">${frm.doc.status || 'Draft'}</span>
                        <span class="po-summary-stat-label">Status</span>
                    </div>
                </div>
            </div>
            
            <div class="po-search-box">
                <input type="text" class="po-search-input" placeholder="🔍 Search items by name, code, or category..." id="po-search-input">
            </div>
            
            <div id="po-items-container">
    `;

    if (!frm.doc.items || frm.doc.items.length === 0) {
        html += `<div class="po-no-items">📦 No items found in this purchase order.</div>`;
    } else {
        frm.doc.items.forEach((item, idx) => {
            html += build_item_card(item, idx, frm);
        });
    }

    html += `
            </div>
        </div>
    `;

    dialog.fields_dict.items_html.$wrapper.html(html);

    // Add search functionality
    setTimeout(() => {
        $('#po-search-input').on('keyup', function() {
            let search_value = $(this).val().toLowerCase();
            $('.po-item-card').each(function() {
                let item_text = $(this).text().toLowerCase();
                if (item_text.indexOf(search_value) > -1) {
                    $(this).show();
                } else {
                    $(this).hide();
                }
            });
        });

        // Add change detection
        $('.po-field-input').on('change', function() {
            $(this).closest('.po-item-card').addClass('po-changed');
        });

        // Add real-time calculation on rate/qty change with percentage-wise GST logic (same as Purchase Invoice)
        $('.po-field-input[data-fieldname="qty"], .po-field-input[data-fieldname="rate"]').on('input', function() {
            let $card = $(this).closest('.po-item-card');
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
            $card.find('.po-amount-display').val(format_currency(amount, frm.doc.currency));
            $card.find('.po-gstn-display').val(format_currency(gstn_value, frm.doc.currency));
            $card.find('.po-grand-total-display').val(format_currency(grand_total, frm.doc.currency));
            $card.addClass('po-changed');
        });

        // Add delete button functionality
        $('.po-delete-btn').on('click', function() {
            let $card = $(this).closest('.po-item-card');
            let item_name = $(this).data('item-name');
            let item_title = $card.find('.po-item-title').text();
            
            frappe.confirm(
                __('Are you sure you want to delete item "{0}"?', [item_title]),
                function() {
                    // Mark card as deleted
                    $card.addClass('po-deleted').hide();
                    $card.attr('data-deleted', 'true');
                }
            );
        });
    }, 100);
}

function build_item_card(item, idx, frm) {
    // Calculate derived values
    let amount = (item.qty || 0) * (item.rate || 0);
    
    return `
        <div class="po-item-card" data-idx="${idx}" data-item-name="${item.name}">
            <div class="po-item-header">
                <div>
                    <div class="po-item-title">${item.item_name || item.item_code}</div>
                    <div class="po-item-code">📦 ${item.item_code || 'N/A'} | 📏 ${item.uom || 'N/A'}</div>
                </div>
                <div>
                    <button type="button" class="btn btn-danger btn-sm po-delete-btn" data-item-name="${item.name}" data-idx="${idx}">
                        🗑️ Delete
                    </button>
                </div>
            </div>
            
            <div class="po-item-fields">
                <!-- Quantity -->
                <div class="po-field-group">
                    <label class="po-field-label">� Quantity</label>
                    <input type="number" 
                           class="po-field-input" 
                           data-fieldname="qty" 
                           data-idx="${idx}"
                           value="${item.qty || 0}"
                           step="0.01"
                           min="0">
                </div>
                
                <!-- Unit Rate -->
                <div class="po-field-group">
                    <label class="po-field-label">💰 Unit Rate</label>
                    <input type="number" 
                           class="po-field-input" 
                           data-fieldname="rate" 
                           data-idx="${idx}"
                           value="${item.rate || 0}"
                           step="0.01"
                           min="0">
                </div>
                
                <!-- Calculated Amount (Read-only) -->
                <div class="po-field-group">
                    <label class="po-field-label">💵 Amount</label>
                    <input type="text" 
                           class="po-field-input po-amount-display" 
                           value="${format_currency(amount, frm.doc.currency)}"
                           disabled>
                </div>
                
                <!-- GSTN Value (Read-only) -->
                <div class="po-field-group">
                    <label class="po-field-label">🏷️ GSTN Value</label>
                    <input type="text" 
                           class="po-field-input po-gstn-display" 
                           value="${format_currency(item.custom_gstn_value || 0, frm.doc.currency)}"
                           disabled>
                </div>
                
                <!-- Grand Total (Read-only) -->
                <div class="po-field-group">
                    <label class="po-field-label">💎 Grand Total</label>
                    <input type="text" 
                           class="po-field-input po-grand-total-display" 
                           value="${format_currency(item.custom_grand_total || amount, frm.doc.currency)}"
                           disabled>
                </div>
            </div>
            
            <div class="po-item-stats">
                <div class="po-stat">
                    <span class="po-stat-label">📦 Received Qty</span>
                    <span class="po-stat-value">${item.received_qty || 0}</span>
                </div>
                <div class="po-stat">
                    <span class="po-stat-label">🧾 Billed Amount</span>
                    <span class="po-stat-value">${format_currency(item.billed_amt || 0, frm.doc.currency)}</span>
                </div>
                <div class="po-stat">
                    <span class="po-stat-label">📋 Item Group</span>
                    <span class="po-stat-value">${item.item_group || 'N/A'}</span>
                </div>
            </div>
        </div>
    `;
}

function save_item_changes(frm, dialog) {
    let changes = [];
    let deleted_items = [];
    
    // Collect deleted items
    $('.po-item-card[data-deleted="true"]').each(function() {
        let item_name = $(this).data('item-name');
        deleted_items.push(item_name);
    });
    
    // Collect all changes from the dialog (excluding deleted items)
    $('.po-field-input').each(function() {
        let $input = $(this);
        let $card = $input.closest('.po-item-card');
        
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
        message = __('You are about to update {0} item(s) and delete {1} item(s) in Purchase Order {2}. Do you want to continue?', 
                    [changes.length, deleted_items.length, frm.doc.name]);
    } else if (changes.length > 0) {
        message = __('You are about to update {0} item(s) in Purchase Order {1}. Do you want to continue?', 
                    [changes.length, frm.doc.name]);
    } else {
        message = __('You are about to delete {0} item(s) from Purchase Order {1}. Do you want to continue?', 
                    [deleted_items.length, frm.doc.name]);
    }
    
    frappe.confirm(message, function() {
        // User confirmed, proceed with update
        update_po_items(frm, changes, deleted_items, dialog);
    });
}

function update_po_items(frm, changes, deleted_items, dialog) {
    // Call the API method from your custom app
    frappe.call({
        method: 'o2o_erpnext.api.purchase_order.update_submitted_po_items',
        freeze: true,
        freeze_message: __('Updating Purchase Order Items...'),
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

function format_currency(value, currency) {
    return frappe.format(value, {fieldtype: 'Currency', options: currency || 'INR'});
}