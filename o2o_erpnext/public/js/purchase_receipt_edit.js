frappe.ui.form.on('Purchase Receipt', {
    refresh: function(frm) {
        // Add the "Edit Submitted Items" button only for submitted Purchase Receipts
        if (frm.doc.docstatus === 1 && frm.doc.items && frm.doc.items.length > 0) {
            frm.add_custom_button(__('Edit Submitted Items'), function() {
                show_pr_items_editor(frm);
            }, __('Actions'));
        }
    }
});

function show_pr_items_editor(frm) {
    // Create dialog with dashboard UI
    let dialog = new frappe.ui.Dialog({
        title: __('Edit Purchase Receipt Items - {0}', [frm.doc.name]),
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
            <p class="mt-3">${__('Loading Purchase Receipt items...')}</p>
        </div>
    `);

    // Load items after dialog is shown
    dialog.show();
    load_pr_items(frm, dialog);

    // Add save and cancel buttons
    dialog.set_primary_action(__('Save Changes'), function() {
        save_pr_item_changes(frm, dialog);
    });

    dialog.add_custom_action(__('Cancel'), function() {
        dialog.hide();
    });

    return dialog;
}

function load_pr_items(frm, dialog) {
    try {
        let items_html = `
            <style>
                .pr-items-container {
                    max-height: 500px;
                    overflow-y: auto;
                    padding: 10px;
                }
                .pr-item-card {
                    border: 1px solid #d1d8dd;
                    border-radius: 8px;
                    margin-bottom: 15px;
                    padding: 15px;
                    background: #f8f9fa;
                    transition: all 0.3s ease;
                }
                .pr-item-card:hover {
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                }
                .pr-item-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 10px;
                }
                .pr-item-title {
                    font-weight: 600;
                    font-size: 14px;
                    color: #36414c;
                }
                .pr-item-code {
                    font-size: 12px;
                    color: #8492a6;
                    margin-top: 2px;
                }
                .pr-item-fields {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 10px;
                    margin-bottom: 10px;
                }
                .pr-field-group {
                    display: flex;
                    flex-direction: column;
                }
                .pr-field-label {
                    font-size: 11px;
                    color: #8492a6;
                    margin-bottom: 4px;
                    font-weight: 500;
                }
                .pr-field-input {
                    padding: 6px 8px;
                    border: 1px solid #d1d8dd;
                    border-radius: 4px;
                    font-size: 12px;
                    transition: border-color 0.2s;
                }
                .pr-field-input:focus {
                    outline: none;
                    border-color: #5e64ff;
                    box-shadow: 0 0 0 2px rgba(94, 100, 255, 0.1);
                }
                .pr-field-input:disabled {
                    background: #f7f7f7;
                    cursor: not-allowed;
                }
                .pr-item-stats {
                    display: flex;
                    gap: 15px;
                    flex-wrap: wrap;
                    font-size: 11px;
                }
                .pr-stat {
                    display: flex;
                    flex-direction: column;
                }
                .pr-stat-label {
                    color: #8492a6;
                    margin-bottom: 2px;
                }
                .pr-stat-value {
                    font-weight: 600;
                    color: #36414c;
                }
                .pr-no-items {
                    text-align: center;
                    padding: 40px;
                    color: #95a5a6;
                    font-size: 16px;
                }
                .pr-changed {
                    background-color: #fff3cd;
                    border-left: 4px solid #ffc107;
                }
                .pr-deleted {
                    background-color: #f8d7da;
                    border-left: 4px solid #dc3545;
                    opacity: 0.6;
                }
                .pr-delete-btn {
                    font-size: 12px;
                    padding: 4px 8px;
                }
                .pr-summary-box {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    border-radius: 8px;
                    padding: 20px;
                    margin-bottom: 20px;
                }
                .pr-summary-title {
                    font-weight: 600;
                    font-size: 18px;
                    margin-bottom: 15px;
                }
                .pr-summary-stats {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                    gap: 15px;
                }
                .pr-summary-stat {
                    text-align: center;
                }
                .pr-summary-value {
                    font-size: 24px;
                    font-weight: 700;
                    margin-bottom: 5px;
                }
                .pr-summary-label {
                    font-size: 12px;
                    opacity: 0.9;
                }
            </style>
            <div class="pr-items-container">
        `;

        // Add summary section
        items_html += `
            <div class="pr-summary-box">
                <div class="pr-summary-title">📊 Purchase Receipt Summary</div>
                <div class="pr-summary-stats">
                    <div class="pr-summary-stat">
                        <div class="pr-summary-value">${frm.doc.items ? frm.doc.items.length : 0}</div>
                        <div class="pr-summary-label">Total Items</div>
                    </div>
                    <div class="pr-summary-stat">
                        <div class="pr-summary-value">${format_currency(frm.doc.total || 0, frm.doc.currency)}</div>
                        <div class="pr-summary-label">Total Amount</div>
                    </div>
                    <div class="pr-summary-stat">
                        <div class="pr-summary-value">${format_currency(frm.doc.grand_total || 0, frm.doc.currency)}</div>
                        <div class="pr-summary-label">Grand Total</div>
                    </div>
                    <div class="pr-summary-stat">
                        <div class="pr-summary-value">${frm.doc.supplier || 'N/A'}</div>
                        <div class="pr-summary-label">Supplier</div>
                    </div>
                </div>
            </div>
        `;

        if (!frm.doc.items || frm.doc.items.length === 0) {
            items_html += `
                <div class="pr-no-items">
                    <div class="text-muted">
                        <i class="fa fa-inbox fa-3x mb-3"></i>
                        <p>${__('No items found in this Purchase Receipt')}</p>
                    </div>
                </div>
            `;
        } else {
            frm.doc.items.forEach((item, idx) => {
                items_html += build_pr_item_card(item, idx, frm);
            });
        }

        items_html += `</div>`;
        
        dialog.fields_dict.items_html.$wrapper.html(items_html);
        
        // Add event handlers after HTML is rendered
        setTimeout(function() {
            add_pr_event_handlers(frm, dialog);
        }, 100);
        
    } catch (error) {
        console.error('Error loading PR items:', error);
        dialog.fields_dict.items_html.$wrapper.html(`
            <div class="alert alert-danger">
                <strong>${__('Error')}</strong>: ${__('Failed to load Purchase Receipt items')}
                <br><small>${error.message}</small>
            </div>
        `);
    }
}

function build_pr_item_card(item, idx, frm) {
    // Calculate derived values
    let amount = (item.qty || 0) * (item.rate || 0);
    
    return `
        <div class="pr-item-card" data-idx="${idx}" data-item-name="${item.name}">
            <div class="pr-item-header">
                <div>
                    <div class="pr-item-title">${item.item_name || item.item_code}</div>
                    <div class="pr-item-code">📦 ${item.item_code || 'N/A'} | 📏 ${item.uom || 'N/A'}</div>
                </div>
                <div>
                    <button type="button" class="btn btn-danger btn-sm pr-delete-btn" data-item-name="${item.name}" data-idx="${idx}">
                        🗑️ Delete
                    </button>
                </div>
            </div>
            
            <div class="pr-item-fields">
                <!-- Quantity -->
                <div class="pr-field-group">
                    <label class="pr-field-label">📊 Quantity</label>
                    <input type="number" 
                           class="pr-field-input" 
                           data-fieldname="qty" 
                           data-idx="${idx}"
                           value="${item.qty || 0}"
                           step="0.01"
                           min="0">
                </div>
                
                <!-- Received Quantity -->
                <div class="pr-field-group">
                    <label class="pr-field-label">📥 Received Qty</label>
                    <input type="number" 
                           class="pr-field-input" 
                           data-fieldname="received_qty" 
                           data-idx="${idx}"
                           value="${item.received_qty || 0}"
                           step="0.01"
                           min="0">
                </div>
                
                <!-- Unit Rate -->
                <div class="pr-field-group">
                    <label class="pr-field-label">💰 Unit Rate</label>
                    <input type="number" 
                           class="pr-field-input" 
                           data-fieldname="rate" 
                           data-idx="${idx}"
                           value="${item.rate || 0}"
                           step="0.01"
                           min="0">
                </div>
                
                <!-- Calculated Amount (Read-only) -->
                <div class="pr-field-group">
                    <label class="pr-field-label">💵 Amount</label>
                    <input type="text" 
                           class="pr-field-input pr-amount-display" 
                           value="${format_currency(amount, frm.doc.currency)}"
                           disabled>
                </div>
                
                <!-- GSTN Value (Read-only) -->
                <div class="pr-field-group">
                    <label class="pr-field-label">🏷️ GSTN Value</label>
                    <input type="text" 
                           class="pr-field-input pr-gstn-display" 
                           value="${format_currency(item.custom_gstn_value || 0, frm.doc.currency)}"
                           disabled>
                </div>
                
                <!-- Grand Total (Read-only) -->
                <div class="pr-field-group">
                    <label class="pr-field-label">💎 Grand Total</label>
                    <input type="text" 
                           class="pr-field-input pr-grand-total-display" 
                           value="${format_currency(item.custom_grand_total || amount, frm.doc.currency)}"
                           disabled>
                </div>
            </div>
            
            <div class="pr-item-stats">
                <div class="pr-stat">
                    <span class="pr-stat-label">📋 Item Group</span>
                    <span class="pr-stat-value">${item.item_group || 'N/A'}</span>
                </div>
                <div class="pr-stat">
                    <span class="pr-stat-label">🏪 Warehouse</span>
                    <span class="pr-stat-value">${item.warehouse || 'N/A'}</span>
                </div>
                <div class="pr-stat">
                    <span class="pr-stat-label">📄 Purchase Order</span>
                    <span class="pr-stat-value">${item.purchase_order || 'N/A'}</span>
                </div>
            </div>
        </div>
    `;
}

function add_pr_event_handlers(frm, dialog) {
    // Add change detection
    $('.pr-field-input').on('change', function() {
        $(this).closest('.pr-item-card').addClass('pr-changed');
    });

    // Add real-time calculation on rate/qty change with percentage-wise GST logic
    $('.pr-field-input[data-fieldname="qty"], .pr-field-input[data-fieldname="rate"]').on('input', function() {
        let $card = $(this).closest('.pr-item-card');
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
        $card.find('.pr-amount-display').val(format_currency(amount, frm.doc.currency));
        $card.find('.pr-gstn-display').val(format_currency(gstn_value, frm.doc.currency));
        $card.find('.pr-grand-total-display').val(format_currency(grand_total, frm.doc.currency));
        $card.addClass('pr-changed');
    });

    // Add delete button functionality
    $('.pr-delete-btn').on('click', function() {
        let $card = $(this).closest('.pr-item-card');
        let item_name = $(this).data('item-name');
        let item_title = $card.find('.pr-item-title').text();
        
        frappe.confirm(
            __('Are you sure you want to delete item "{0}"?', [item_title]),
            function() {
                // Mark card as deleted
                $card.addClass('pr-deleted').hide();
                $card.attr('data-deleted', 'true');
            }
        );
    });
}

function save_pr_item_changes(frm, dialog) {
    let changes = [];
    let deleted_items = [];
    
    // Collect deleted items
    $('.pr-item-card[data-deleted="true"]').each(function() {
        let item_name = $(this).data('item-name');
        deleted_items.push(item_name);
    });
    
    // Collect all changes from the dialog (excluding deleted items)
    $('.pr-field-input').each(function() {
        let $input = $(this);
        let $card = $input.closest('.pr-item-card');
        
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
        message = __('You are about to update {0} item(s) and delete {1} item(s) in Purchase Receipt {2}. Do you want to continue?', 
                    [changes.length, deleted_items.length, frm.doc.name]);
    } else if (changes.length > 0) {
        message = __('You are about to update {0} item(s) in Purchase Receipt {1}. Do you want to continue?', 
                    [changes.length, frm.doc.name]);
    } else {
        message = __('You are about to delete {0} item(s) from Purchase Receipt {1}. Do you want to continue?', 
                    [deleted_items.length, frm.doc.name]);
    }
    
    frappe.confirm(message, function() {
        // User confirmed, proceed with update
        update_pr_items(frm, changes, deleted_items, dialog);
    });
}

function update_pr_items(frm, changes, deleted_items, dialog) {
    // Call the API method from your custom app
    frappe.call({
        method: 'o2o_erpnext.api.purchase_receipt.update_submitted_pr_items',
        freeze: true,
        freeze_message: __('Updating Purchase Receipt Items...'),
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
        $('.pr-item-card').show();
        return;
    }
    
    search_term = search_term.toLowerCase();
    
    $('.pr-item-card').each(function() {
        let $card = $(this);
        let item_name = $card.find('.pr-item-title').text().toLowerCase();
        let item_code = $card.find('.pr-item-code').text().toLowerCase();
        
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