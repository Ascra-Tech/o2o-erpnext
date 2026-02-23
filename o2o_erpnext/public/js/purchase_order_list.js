// ========================================
// Purchase Order List - PO Scanner & Statistics
// ========================================
// This file adds PO Scanner functionality to Purchase Order list view
// Using doctype_list_js pattern - Following purchase_invoice_list.js approach
// ========================================

// Store listview reference globally for use in other functions
window.purchase_order_listview = null;

// Extend existing listview settings instead of overriding
if (!frappe.listview_settings['Purchase Order']) {
    frappe.listview_settings['Purchase Order'] = {};
}

// Store original onload if it exists
const original_onload = frappe.listview_settings['Purchase Order'].onload;
const original_refresh = frappe.listview_settings['Purchase Order'].refresh;

// Extend the settings
Object.assign(frappe.listview_settings['Purchase Order'], {
    onload: function(listview) {
        console.log("Purchase Order List View onload called");
        
        // Call original onload first if it exists
        if (original_onload && typeof original_onload === 'function') {
            original_onload.call(this, listview);
        }
        
        // Store listview reference globally
        window.purchase_order_listview = listview;
        
        // Add existing print functionality
        add_print_buttons(listview);
        
        // Add PO Scanner functionality
        setTimeout(function() {
            add_po_scanner_buttons(listview);
        }, 500);
        
        // Hide UI elements (from client script)
        setTimeout(function() {
            hide_ui_elements(listview);
        }, 600);
        
        console.log("All Purchase Order list functionality setup complete");
    },
    refresh: function(listview) {
        // Call original refresh first if it exists
        if (original_refresh && typeof original_refresh === 'function') {
            original_refresh.call(this, listview);
        }
        
        // Hide like icons (from client script)
        $("use.like-icon").hide();
    }
});

function add_print_buttons(listview) {
    console.log("🖨️ Adding Print functionality buttons");
    
    if (!listview || !listview.page) {
        console.error("❌ Invalid listview for print buttons");
        return;
    }
    
    // Add Print PO button
    listview.page.add_button(__('Print PO'), function() {
        let selected = listview.get_checked_items();
        if (!selected.length || selected.length > 1) {
            frappe.msgprint('Please select one Purchase Order');
            return;
        }
        let pdfUrl = frappe.urllib.get_full_url("/api/method/frappe.utils.print_format.download_pdf?"
            + "doctype=" + encodeURIComponent("Purchase Order")
            + "&name=" + encodeURIComponent(selected[0].name)
            + "&trigger_print=0"
            + "&format=Purchase Order"
            + "&no_letterhead=0"
            + "&_lang=en"
        );
        window.open(pdfUrl);
    }, true).addClass('btn-primary');

    // Add Print PI button
    listview.page.add_button(__('Print PI'), function() {
        let selected = listview.get_checked_items();
        if (!selected.length || selected.length > 1) {
            frappe.msgprint('Please select one Purchase Order');
            return;
        }

        frappe.call({
            method: 'o2o_erpnext.api.purchase_order_linking.get_linked_purchase_invoices',
            args: {
                purchase_order_name: selected[0].name
            },
            callback: function(r) {
                if (!r.message?.success || !r.message?.purchase_invoices?.length) {
                    frappe.msgprint('No Purchase Invoices found');
                    return;
                }

                // Since our API returns only one Purchase Invoice, directly open it for printing
                let pi_name = r.message.purchase_invoices[0];
                let pdfUrl = "/api/method/frappe.utils.print_format.download_pdf?"
                    + "doctype=" + encodeURIComponent("Purchase Invoice")
                    + "&name=" + encodeURIComponent(pi_name)
                    + "&format=" + encodeURIComponent("Standard")
                    + "&no_letterhead=0"
                    + "&_lang=en";
                window.open(pdfUrl);
            }
        });
    }, true).addClass('btn-secondary');

    // Add Export PO button
    listview.page.add_button(__('Export PO'), function() {
        export_po_dialog(window.purchase_order_listview || listview);
    }, true).addClass('btn-primary');

    // Add Link PR button for bulk linking Purchase Orders with Purchase Receipts
    listview.page.add_button(__('Link PR'), function() {
        bulk_link_purchase_receipts(listview);
    }, true).addClass('btn-success');

    // Add Overview button for workflow state dashboard
    listview.page.add_button(__('Overview'), function() {
        show_po_overview_dashboard(listview);
    }, true).addClass('btn-info');
    
    console.log("✅ Print, Export, Link PR, and Overview buttons added successfully");
}

function hide_ui_elements(listview) {
    console.log("🔧 Hiding UI elements");
    
    if (!listview || !listview.page) {
        console.error("❌ Invalid listview for hiding UI elements");
        return;
    }
    
    // Hide specific action buttons (from client script) - but keep our custom buttons
    listview.page.actions.find('[data-label="Edit"],[data-label="Assign%20To"],[data-label="Apply%20Assignment%20Rule"],[data-label="Add%20Tags"]').parent().parent().remove();
    
    // Hide the default Export and Print buttons but not our custom ones
    listview.page.actions.find('[data-label="Export"]:not([data-label*="Export PO"])').parent().parent().remove();
    listview.page.actions.find('[data-label="Print"]:not([data-label*="Print P"])').parent().parent().remove();
    
    console.log("✅ UI elements hidden successfully");
}

function add_po_scanner_buttons(listview) {
    console.log("🔧 Adding PO Scanner menu items");
    
    if (!listview || !listview.page) {
        console.error("❌ Invalid listview");
        return;
    }
    
    // Check role-based access first
    check_po_scanner_access(function(has_access) {
        if (!has_access) {
            console.log("❌ User does not have access to PO Scanner functionality");
            return;
        }
        
        console.log("✅ User has access to PO Scanner functionality");
        
        // Add menu items (dropdown style like client script)
        listview.page.add_menu_item(__('🔍 Scan Partial Orders'), function() {
            window.scan_partial_purchase_orders();
        });
        
        listview.page.add_menu_item(__('📊 PO Statistics'), function() {
            window.show_po_statistics();
        });
        
        
        console.log("✅ PO Scanner menu items added successfully");
    });
}

function check_po_scanner_access(callback) {
    console.log("🔐 Checking PO Scanner access permissions...");
    
    // Check user roles client-side first (quick check)
    let user_roles = frappe.user_roles || [];
    let allowed_roles = ['Vendor User', 'Supplier', 'System Manager'];
    let has_role_access = allowed_roles.some(role => user_roles.includes(role));
    
    if (!has_role_access) {
        console.log("❌ User roles:", user_roles, "- No access to PO Scanner");
        callback(false);
        return;
    }
    
    // Server-side verification for additional security
    frappe.call({
        method: 'o2o_erpnext.po_scanner.check_vendor_access',
        callback: function(r) {
            console.log("Server access check result:", r);
            
            if (r.message && r.message.status === 'success' && r.message.has_access) {
                console.log("✅ Server confirmed access for user");
                callback(true);
            } else {
                console.log("❌ Server denied access for user");
                callback(false);
            }
        },
        error: function(r) {
            console.error("❌ Error checking access:", r);
            callback(false);
        }
    });
}

// Make functions globally accessible (following purchase_invoice_list.js pattern)
window.scan_partial_purchase_orders = function() {
    console.log("🔍 Scanning for partial POs...");
    
    // Check access before proceeding
    check_po_scanner_access(function(has_access) {
        if (!has_access) {
            frappe.msgprint({
                title: __('Access Denied'),
                message: __('You do not have permission to access PO Scanner functionality. Required roles: Vendor User, Supplier, or System Manager.'),
                indicator: 'red'
            });
            return;
        }
        
        frappe.show_alert({
            message: __('🔍 Scanning Purchase Orders for partial receipts...'),
            indicator: 'blue'
        });
        
        frappe.call({
            method: 'o2o_erpnext.po_scanner.get_partial_purchase_orders',
            callback: function(r) {
                console.log("Scan result:", r);
                
                if (r.message && r.message.status === 'success') {
                    if (r.message.data && r.message.data.length > 0) {
                        show_partial_orders_results(r.message.data);
                    } else {
                        frappe.show_alert({
                            message: __('✅ No partial Purchase Orders found!'),
                            indicator: 'green'
                        });
                    }
                } else {
                    frappe.msgprint({
                        title: __('Error'),
                        message: r.message?.message || __('Failed to scan Purchase Orders'),
                        indicator: 'red'
                    });
                }
            },
            error: function(r) {
                console.error("Scan error:", r);
                frappe.msgprint({
                    title: __('Error'),
                    message: __('Unable to scan. Please check server method exists'),
                    indicator: 'red'
                });
            }
        });
    });
};

window.show_po_statistics = function() {
    console.log("📊 Getting PO statistics...");
    
    // Check access before proceeding
    check_po_scanner_access(function(has_access) {
        if (!has_access) {
            frappe.msgprint({
                title: __('Access Denied'),
                message: __('You do not have permission to access PO Scanner functionality. Required roles: Vendor User, Supplier, or System Manager.'),
                indicator: 'red'
            });
            return;
        }
        
        frappe.call({
            method: 'o2o_erpnext.po_scanner.get_po_statistics',
            callback: function(r) {
                console.log("Stats result:", r);
                
                if (r.message && r.message.status === 'success') {
                    let stats = r.message.data;
                    
                    let html = `
                        <div class="po-statistics" style="padding: 20px;">
                            <div class="stats-container" style="text-align: center;">
                                <h3 style="margin-bottom: 20px;">📊 Purchase Order Statistics</h3>
                                <p style="margin-bottom: 30px;">Overview of your Purchase Order status</p>
                                
                                <div class="stats-grid" style="display: flex; justify-content: space-around; gap: 20px;">
                                    <div class="stat-card" style="background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; min-width: 120px;">
                                        <div class="stat-number" style="font-size: 24px; font-weight: bold; color: #2c3e50;">${stats.total_pos || 0}</div>
                                        <div class="stat-label" style="font-size: 12px; color: #6c757d; margin-top: 5px;">Total POs</div>
                                    </div>
                                    <div class="stat-card" style="background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; min-width: 120px;">
                                        <div class="stat-number" style="font-size: 24px; font-weight: bold; color: #e74c3c;">${stats.partial_pos || 0}</div>
                                        <div class="stat-label" style="font-size: 12px; color: #6c757d; margin-top: 5px;">Partial POs</div>
                                    </div>
                                    <div class="stat-card" style="background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; min-width: 120px;">
                                        <div class="stat-number" style="font-size: 24px; font-weight: bold; color: #f39c12;">${stats.partial_percentage || 0}%</div>
                                        <div class="stat-label" style="font-size: 12px; color: #6c757d; margin-top: 5px;">Partial Rate</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    `;
                    
                    frappe.msgprint({
                        title: __('📊 PO Statistics'),
                        message: html,
                        wide: true
                    });
                } else {
                    frappe.msgprint({
                        title: __('Error'),
                        message: r.message?.message || __('Failed to get statistics'),
                        indicator: 'red'
                    });
                }
            },
            error: function(r) {
                console.error("Stats error:", r);
                frappe.msgprint({
                    title: __('Error'),
                    message: __('Failed to get statistics'),
                    indicator: 'red'
                });
            }
        });
    });
};

window.show_po_item_details = function(po_name) {
    frappe.show_alert({
        message: __('Loading item details...'),
        indicator: 'blue'
    });
    
    frappe.call({
        method: 'o2o_erpnext.po_scanner.get_po_item_status',
        args: {
            po_name: po_name
        },
        callback: function(r) {
            if (r.message && r.message.status === 'success') {
                display_po_item_details(r.message.data);
            } else {
                frappe.msgprint({
                    title: __('Error'),
                    message: r.message?.message || __('Failed to get item details'),
                    indicator: 'red'
                });
            }
        }
    });
};

function show_partial_orders_results(partial_pos) {
    let html = `
        <div class="partial-orders-results">
            <style>
                .partial-orders-results {
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                }
                .summary-card {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 20px;
                    border-radius: 12px;
                    margin-bottom: 24px;
                    text-align: center;
                }
                .po-card {
                    border: 1px solid #e1e5e9;
                    border-radius: 12px;
                    margin-bottom: 16px;
                    padding: 20px;
                    background: #ffffff;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
                    border-left: 4px solid #ff9800;
                    transition: all 0.3s ease;
                }
                .po-card:hover {
                    box-shadow: 0 4px 16px rgba(0,0,0,0.12);
                    transform: translateY(-2px);
                }
                .po-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 16px;
                }
                .po-title {
                    font-size: 18px;
                    font-weight: 600;
                    color: #2c3e50;
                }
                .po-title a {
                    text-decoration: none;
                    color: #3498db;
                }
                .po-title a:hover {
                    color: #2980b9;
                }
                .po-details-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
                    gap: 16px;
                    margin-bottom: 16px;
                }
                .detail-item {
                    text-align: center;
                    padding: 12px;
                    background: #f8f9fa;
                    border-radius: 8px;
                    border: 1px solid #e9ecef;
                }
                .detail-value {
                    font-size: 16px;
                    font-weight: 600;
                    color: #2c3e50;
                    margin-bottom: 4px;
                }
                .detail-label {
                    font-size: 12px;
                    color: #6c757d;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }
                .progress-section {
                    margin-top: 16px;
                }
                .progress-bar {
                    width: 100%;
                    height: 12px;
                    background-color: #e9ecef;
                    border-radius: 6px;
                    overflow: hidden;
                    margin: 8px 0;
                }
                .progress-fill {
                    height: 100%;
                    background: linear-gradient(90deg, #ff9800 0%, #ffb74d 100%);
                    border-radius: 6px;
                    transition: width 0.5s ease;
                }
                .btn-view-details {
                    background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 8px;
                    cursor: pointer;
                    font-size: 14px;
                    font-weight: 500;
                    transition: all 0.3s ease;
                }
                .btn-view-details:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 4px 12px rgba(52, 152, 219, 0.3);
                }
                .status-badge {
                    padding: 6px 12px;
                    border-radius: 20px;
                    font-size: 12px;
                    font-weight: 500;
                    background: #fff3cd;
                    color: #856404;
                    border: 1px solid #ffeaa7;
                }
            </style>
            
            <div class="summary-card">
                <h3 style="margin: 0 0 8px 0; font-size: 24px;">📊 Partial Orders Summary</h3>
                <p style="margin: 0; font-size: 16px; opacity: 0.9;">
                    Found <strong>${partial_pos.length}</strong> Purchase Orders with partial receipts
                </p>
            </div>
    `;
    
    partial_pos.forEach(function(po) {
        html += `
            <div class="po-card">
                <div class="po-header">
                    <div class="po-title">
                        <a href="/app/purchase-order/${po.name}" target="_blank">
                            📄 ${po.name}
                        </a>
                    </div>
                    <div>
                        <span class="status-badge">${po.status}</span>
                    </div>
                </div>
                
                <div class="po-details-grid">
                    <div class="detail-item">
                        <div class="detail-value">${po.supplier}</div>
                        <div class="detail-label">Supplier</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-value">${frappe.datetime.str_to_user(po.transaction_date)}</div>
                        <div class="detail-label">Date</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-value">${format_currency(po.grand_total)}</div>
                        <div class="detail-label">Total Amount</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-value">${po.total_items}</div>
                        <div class="detail-label">Total Items</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-value" style="color: #e74c3c;">${po.pending_items}</div>
                        <div class="detail-label">Pending Items</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-value" style="color: #27ae60;">${po.completion_percentage}%</div>
                        <div class="detail-label">Completed</div>
                    </div>
                </div>
                
                <div class="progress-section">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <span style="font-size: 14px; color: #6c757d;">
                            Progress: ${po.received_items}/${po.total_items} items received
                        </span>
                        <button class="btn-view-details" onclick="show_po_item_details('${po.name}')">
                            🔍 View Item Details
                        </button>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${po.completion_percentage}%"></div>
                    </div>
                </div>
            </div>
        `;
    });
    
    html += `</div>`;
    
    let dialog = new frappe.ui.Dialog({
        title: __(`📋 Partial Purchase Orders (${partial_pos.length} found)`),
        fields: [{
            fieldtype: 'HTML',
            fieldname: 'partial_orders',
            options: html
        }],
        size: 'extra-large',
        primary_action_label: __('Export CSV'),
        primary_action: function() {
            export_to_csv(partial_pos);
        }
    });
    
    dialog.show();
}

function display_po_item_details(data) {
    let html = `
        <div class="po-item-details">
            <style>
                .po-summary-section {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 24px;
                    border-radius: 12px;
                    margin-bottom: 24px;
                }
                .summary-stats {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
                    gap: 16px;
                    margin-top: 16px;
                }
                .stat-box {
                    text-align: center;
                    background: rgba(255, 255, 255, 0.15);
                    padding: 16px;
                    border-radius: 8px;
                    backdrop-filter: blur(10px);
                }
                .stat-number {
                    font-size: 20px;
                    font-weight: 700;
                    margin-bottom: 4px;
                }
                .stat-label {
                    font-size: 12px;
                    opacity: 0.9;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }
                .items-table {
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 20px;
                    border-radius: 8px;
                    overflow: hidden;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                }
                .items-table th {
                    background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                    padding: 16px 12px;
                    text-align: left;
                    font-weight: 600;
                    color: #495057;
                    border-bottom: 2px solid #dee2e6;
                }
                .items-table td {
                    padding: 14px 12px;
                    border-bottom: 1px solid #f1f3f4;
                    vertical-align: middle;
                }
                .items-table tr:hover {
                    background: #f8f9fa;
                }
                .status-badge {
                    padding: 6px 12px;
                    border-radius: 20px;
                    font-size: 11px;
                    font-weight: 600;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }
                .status-received { background: #d4edda; color: #155724; }
                .status-partial { background: #fff3cd; color: #856404; }
                .status-pending { background: #f8d7da; color: #721c24; }
                .item-code {
                    font-weight: 600;
                    color: #2c3e50;
                }
            </style>
            
            <div class="po-summary-section">
                <h4 style="margin: 0 0 8px 0; font-size: 22px;">📋 ${data.po_name}</h4>
                <p style="margin: 0; font-size: 16px; opacity: 0.9;">
                    <strong>Supplier:</strong> ${data.supplier} | 
                    <strong>Date:</strong> ${frappe.datetime.str_to_user(data.transaction_date)} | 
                    <strong>Status:</strong> ${data.po_status}
                </p>
                
                <div class="summary-stats">
                    <div class="stat-box">
                        <div class="stat-number">${data.summary.total_items}</div>
                        <div class="stat-label">Total Items</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number">${format_currency(data.summary.total_ordered_amount)}</div>
                        <div class="stat-label">Total Ordered</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number">${format_currency(data.summary.total_received_amount)}</div>
                        <div class="stat-label">Total Received</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number">${format_currency(data.summary.total_pending_amount)}</div>
                        <div class="stat-label">Total Pending</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number">${data.summary.overall_completion_percentage}%</div>
                        <div class="stat-label">Completion</div>
                    </div>
                </div>
            </div>
            
            <table class="items-table">
                <thead>
                    <tr>
                        <th>Item Code</th>
                        <th>Item Name</th>
                        <th>UOM</th>
                        <th>Ordered</th>
                        <th>Received</th>
                        <th>Pending</th>
                        <th>Rate</th>
                        <th>Pending Amount</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    data.items.forEach(function(item) {
        let status_class = '';
        if (item.status === 'Fully Received') {
            status_class = 'status-received';
        } else if (item.status === 'Partially Received') {
            status_class = 'status-partial';
        } else {
            status_class = 'status-pending';
        }
        
        html += `
            <tr>
                <td><span class="item-code">${item.item_code}</span></td>
                <td>${item.item_name}</td>
                <td>${item.uom}</td>
                <td>${item.ordered_qty}</td>
                <td>${item.received_qty}</td>
                <td><strong>${item.pending_qty}</strong></td>
                <td>${format_currency(item.rate)}</td>
                <td><strong>${format_currency(item.pending_amount)}</strong></td>
                <td>
                    <span class="status-badge ${status_class}">
                        ${item.status}
                    </span>
                </td>
            </tr>
        `;
    });
    
    html += `
                </tbody>
            </table>
        </div>
    `;
    
    let dialog = new frappe.ui.Dialog({
        title: __(`📦 Item Details - ${data.po_name}`),
        fields: [{
            fieldtype: 'HTML',
            fieldname: 'item_details',
            options: html
        }],
        size: 'extra-large'
    });
    
    dialog.show();
}

function export_to_csv(partial_pos) {
    let csv_content = "Purchase Order,Supplier,Date,Amount,Status,Total Items,Pending Items,Completion %\n";
    
    partial_pos.forEach(function(po) {
        csv_content += `"${po.name}","${po.supplier}","${po.transaction_date}","${po.grand_total}","${po.status}","${po.total_items}","${po.pending_items}","${po.completion_percentage}"\n`;
    });
    
    let blob = new Blob([csv_content], { type: 'text/csv;charset=utf-8;' });
    let link = document.createElement("a");
    let url = URL.createObjectURL(blob);
    link.setAttribute("href", url);
    link.setAttribute("download", `partial_purchase_orders_${frappe.datetime.now_date()}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    frappe.show_alert({
        message: __('CSV file downloaded successfully!'),
        indicator: 'green'
    });
}


/**
 * Open dialog for selecting fields to export
 */
function export_po_dialog(listview) {
    // Ensure we have a valid listview reference
    if (!listview) {
        listview = window.purchase_order_listview;
    }
    
    if (!listview) {
        frappe.msgprint(__('Unable to access list view. Please refresh the page.'));
        return;
    }
    
    // Get selected purchase orders
    const selected_pos = listview.get_checked_items();
    
    if (!selected_pos || selected_pos.length === 0) {
        frappe.throw(__('Please select Purchase Orders first to export'));
        return;
    }
    
    // Direct export with predefined fields - no dialog needed
    perform_po_export(selected_pos);
}

/**
 * Show the field selection dialog for Purchase Orders
 */
function show_po_field_selection_dialog(selected_pos, fields_data) {
    // Track selected fields
    let selected_fields = new Set();
    
    // Create dialog HTML
    let html = `
        <div style="padding: 15px;">
            <div style="margin-bottom: 15px;">
                <h6 style="margin: 10px 0;">Quick Actions:</h6>
                <button class="btn btn-sm btn-default select-all-btn" style="margin: 5px 5px 5px 0;">
                    <i class="fa fa-check"></i> Select All Fields
                </button>
                <button class="btn btn-sm btn-default select-mandatory-btn" style="margin: 5px 5px 5px 0;">
                    <i class="fa fa-star"></i> Select Mandatory Fields
                </button>
                <button class="btn btn-sm btn-default unselect-all-btn" style="margin: 5px 5px 5px 0;">
                    <i class="fa fa-times"></i> Unselect All
                </button>
            </div>
            
            <hr>
            
            <div style="margin-bottom: 15px;">
                <input type="text" class="field-search form-control" placeholder="Search fields..." style="margin-bottom: 10px;">
            </div>
            
            <div class="field-selection-container" style="max-height: 400px; overflow-y: auto; border: 1px solid #ddd; padding: 10px; border-radius: 4px;">
                <h6 style="margin-top: 0; margin-bottom: 10px; background: #f8f9fa; padding: 8px; margin: -10px -10px 10px -10px;">
                    <strong>Mandatory Fields</strong>
                </h6>
                <div id="mandatory-fields">
    `;
    
    // Add mandatory fields
    fields_data.mandatory_fields.forEach(field => {
        html += create_po_field_checkbox(field, true);
    });
    
    html += `
                </div>
                
                <h6 style="margin-top: 15px; margin-bottom: 10px; background: #f8f9fa; padding: 8px; margin: -10px -10px 10px -10px;">
                    <strong>Optional Fields</strong>
                </h6>
                <div id="optional-fields">
    `;
    
    // Add optional fields
    fields_data.optional_fields.forEach(field => {
        html += create_po_field_checkbox(field, false);
    });
    
    html += `
                </div>
            </div>
            
            <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #ddd;">
                <p style="color: #666; font-size: 12px;">
                    <strong>Purchase Orders to export:</strong> ${selected_pos.length} selected
                </p>
            </div>
        </div>
    `;
    
    // Create the dialog
    let dialog = new frappe.ui.Dialog({
        title: __('Export Purchase Orders to Excel'),
        fields: [
            {
                fieldtype: 'HTML',
                fieldname: 'export_html',
                options: html
            }
        ],
        primary_action_label: __('Export'),
        primary_action(d) {
            if (selected_fields.size === 0) {
                frappe.msgprint({
                    title: __('No Fields Selected'),
                    indicator: 'red',
                    message: __('Please select at least one field to export.')
                });
                return;
            }
            
            // Perform export
            perform_po_export(selected_pos, Array.from(selected_fields));
            d.hide();
        },
        secondary_action_label: __('Cancel'),
        secondary_action(d) {
            d.hide();
        }
    });
    
    dialog.show();
    
    // Setup event handlers after dialog is shown
    setTimeout(() => {
        const container = dialog.$wrapper.find('.field-selection-container');
        const search_input = dialog.$wrapper.find('.field-search');
        
        // Select All button
        dialog.$wrapper.find('.select-all-btn').click(function() {
            container.find('input[type="checkbox"]').prop('checked', true);
            container.find('input[type="checkbox"]').each(function() {
                selected_fields.add($(this).data('fieldname'));
            });
        });
        
        // Select Mandatory button
        dialog.$wrapper.find('.select-mandatory-btn').click(function() {
            container.find('input[type="checkbox"]').prop('checked', false);
            selected_fields.clear();
            $('#mandatory-fields input[type="checkbox"]').prop('checked', true);
            $('#mandatory-fields input[type="checkbox"]').each(function() {
                selected_fields.add($(this).data('fieldname'));
            });
        });
        
        // Unselect All button
        dialog.$wrapper.find('.unselect-all-btn').click(function() {
            container.find('input[type="checkbox"]').prop('checked', false);
            selected_fields.clear();
        });
        
        // Field checkbox change handler
        container.find('input[type="checkbox"]').change(function() {
            const fieldname = $(this).data('fieldname');
            if ($(this).is(':checked')) {
                selected_fields.add(fieldname);
            } else {
                selected_fields.delete(fieldname);
            }
        });
        
        // Search functionality
        search_input.on('keyup', function() {
            const search_term = $(this).val().toLowerCase();
            container.find('.field-checkbox-wrapper').each(function() {
                const label = $(this).find('label').text().toLowerCase();
                const fieldname = $(this).find('input').data('fieldname').toLowerCase();
                
                if (label.includes(search_term) || fieldname.includes(search_term)) {
                    $(this).show();
                } else {
                    $(this).hide();
                }
            });
        });
        
    }, 100);
}

/**
 * Create HTML for a single field checkbox for Purchase Orders
 */
function create_po_field_checkbox(field, is_mandatory) {
    const mandatory_badge = field.mandatory ? ' <span class="badge badge-warning" style="margin-left: 5px; font-size: 10px;">MANDATORY</span>' : '';
    const is_custom = field.is_custom ? ' <span class="badge" style="margin-left: 5px; font-size: 10px; background: #6c757d;">CUSTOM</span>' : '';
    
    return `
        <div class="field-checkbox-wrapper" style="padding: 8px; border-bottom: 1px solid #e9ecef;">
            <div style="display: flex; align-items: center;">
                <input type="checkbox" data-fieldname="${field.fieldname}" style="margin-right: 10px;">
                <div style="flex: 1;">
                    <label style="margin: 0; cursor: pointer; display: inline;">
                        <strong>${field.label}</strong>
                        <span style="color: #666; font-size: 11px;">(${field.fieldname})</span>
                        ${mandatory_badge}
                        ${is_custom}
                    </label>
                    <div style="color: #999; font-size: 11px; margin-top: 2px;">
                        Field Type: ${field.fieldtype}
                    </div>
                </div>
            </div>
        </div>
    `;
}

/**
 * Perform the actual Purchase Order export
 */
function perform_po_export(selected_pos) {
    frappe.call({
        method: 'o2o_erpnext.api.purchase_order_export.export_pos_to_excel',
        args: {
            po_ids: JSON.stringify(selected_pos)
        },
        freeze: true,
        freeze_message: __('Generating Excel file...'),
        callback: function(r) {
            if (r.message && r.message.status === 'success') {
                frappe.msgprint({
                    title: __('Success'),
                    indicator: 'green',
                    message: __('Purchase Orders exported successfully. Downloading file...')
                });
                
                // Trigger file download
                let download_url = frappe.urllib.get_full_url(
                    "/api/method/o2o_erpnext.api.purchase_order_export.download_exported_file?" +
                    "filename=" + encodeURIComponent(r.message.filename)
                );
                window.open(download_url);
            }
        },
        error: function(r) {
            console.log('Export error:', r);
        }
    });
}

/**
 * Bulk link Purchase Orders with their Purchase Receipts
 */
function bulk_link_purchase_receipts(listview) {
    console.log("🔗 Starting bulk Purchase Receipt linking...");
    
    if (!listview || !listview.page) {
        console.error("❌ Invalid listview for bulk linking");
        return;
    }

    // Show confirmation dialog
    frappe.confirm(
        __('This will link all submitted Purchase Orders with their corresponding Purchase Receipts. This may take some time for large datasets. Continue?'),
        function() {
            // User confirmed, proceed with bulk linking
            frappe.show_alert({
                message: __('🔗 Starting bulk Purchase Receipt linking...'),
                indicator: 'blue'
            }, 3);

            frappe.call({
                method: 'o2o_erpnext.api.purchase_order_linking.bulk_link_all_purchase_orders',
                freeze: true,
                freeze_message: __('Linking Purchase Orders with Purchase Receipts...'),
                callback: function(r) {
                    console.log("Bulk linking result:", r);
                    
                    if (r.message && r.message.status === 'success') {
                        let data = r.message.data;
                        
                        // Show detailed results
                        let message = `
                            <div style="padding: 15px;">
                                <h4>🔗 Bulk Linking Results</h4>
                                <div style="margin: 15px 0;">
                                    <div style="margin: 8px 0;"><strong>Total Processed:</strong> ${data.total_processed || 0}</div>
                                    <div style="margin: 8px 0; color: #28a745;"><strong>Successfully Linked:</strong> ${data.successfully_linked || 0}</div>
                                    <div style="margin: 8px 0; color: #ffc107;"><strong>Already Linked:</strong> ${data.already_linked || 0}</div>
                                    <div style="margin: 8px 0; color: #dc3545;"><strong>No Receipt Found:</strong> ${data.no_receipt_found || 0}</div>
                                    <div style="margin: 8px 0; color: #6c757d;"><strong>Errors:</strong> ${data.errors || 0}</div>
                                </div>
                                ${data.processing_time ? `<div style="margin-top: 15px; font-size: 12px; color: #666;">Processing time: ${data.processing_time}</div>` : ''}
                            </div>
                        `;
                        
                        frappe.msgprint({
                            title: __('Bulk Linking Complete'),
                            message: message,
                            indicator: 'green',
                            wide: true
                        });

                        // Refresh the list view to show updated data
                        if (listview && listview.refresh) {
                            setTimeout(function() {
                                listview.refresh();
                            }, 1000);
                        }
                        
                    } else {
                        frappe.msgprint({
                            title: __('Error'),
                            message: r.message?.message || __('Failed to perform bulk linking'),
                            indicator: 'red'
                        });
                    }
                },
                error: function(r) {
                    console.error("Bulk linking error:", r);
                    frappe.msgprint({
                        title: __('Error'),
                        message: __('Unable to perform bulk linking. Please check server logs.'),
                        indicator: 'red'
                    });
                }
            });
        },
        function() {
            // User cancelled
            frappe.show_alert({
                message: __('Bulk linking cancelled'),
                indicator: 'orange'
            }, 2);
        }
    );
}

// Debug function to check if script is loaded
console.log("✅ Purchase Order List Script Loaded Successfully");

// ===== MERGED CONTENT FROM purchase_order_view.js =====
// Note: List view enhancement removed to prevent filter issues

// ===== FORM FUNCTIONALITY REMOVED =====
// Purchase Receipt form functionality removed to prevent display issues
// Automatic linking now handled purely server-side via Purchase Receipt hooks

// ===== OVERVIEW DASHBOARD FUNCTIONALITY =====

function show_po_overview_dashboard(listview) {
    console.log("🔍 Opening PO Overview Dashboard");
    
    // Get available workflow states from backend
    frappe.call({
        method: 'o2o_erpnext.dashboard.get_workflow_states',
        callback: function(r) {
            if (r.message && r.message.length > 0) {
                show_workflow_state_dialog(r.message, listview);
            } else {
                frappe.msgprint(__('No Purchase Orders found with workflow states'));
            }
        }
    });
}

function show_workflow_state_dialog(workflow_states, listview) {
    let d = new frappe.ui.Dialog({
        title: __('Select Workflow State for Overview'),
        fields: [
            {
                label: __('Workflow State'),
                fieldname: 'workflow_state',
                fieldtype: 'Select',
                options: workflow_states.join('\n'),
                reqd: 1,
                description: __('Select the workflow state to view Purchase Orders dashboard')
            }
        ],
        primary_action_label: __('Show Dashboard'),
        primary_action(values) {
            if (values.workflow_state) {
                d.hide();
                show_po_dashboard(values.workflow_state, listview);
            }
        }
    });
    
    d.show();
}

function show_po_dashboard(workflow_state, listview) {
    console.log(`📊 Loading dashboard for workflow state: ${workflow_state}`);
    
    // Directly create dialog-based dashboard
    create_dashboard_dialog(workflow_state, listview);
}

function create_dashboard_dialog(workflow_state, listview) {
    // Fetch Purchase Orders dashboard data from backend
    frappe.call({
        method: 'o2o_erpnext.dashboard.get_po_dashboard_data',
        args: {
            workflow_state: workflow_state
        },
        callback: function(r) {
            if (r.message && r.message.success) {
                show_advanced_dashboard(workflow_state, r.message.data);
                if (r.message.message && r.message.message.includes('No Purchase Orders found')) {
                    frappe.show_alert({
                        message: r.message.message,
                        indicator: 'blue'
                    });
                }
            } else {
                frappe.msgprint(__(r.message.message || `Error loading dashboard data for workflow state: ${workflow_state}`));
            }
        }
    });
}

function show_advanced_dashboard(workflow_state, dashboard_data) {
    // Extract data from backend response
    let summary = dashboard_data.summary;
    let purchase_orders = dashboard_data.purchase_orders;
    let supplier_stats = dashboard_data.supplier_stats;
    
    // Create advanced dashboard HTML with filters and actions
    let dashboard_html = `
        <div class="po-overview-dashboard" style="padding: 20px;">
            <div class="dashboard-header" style="margin-bottom: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                    <div>
                        <h2 style="color: #2c3e50; margin: 0;">Purchase Orders Overview</h2>
                        <h3 style="color: #7f8c8d; font-weight: normal; margin: 5px 0 0 0;">Workflow State: <span style="color: #3498db;">${workflow_state}</span></h3>
                    </div>
                    <div class="dashboard-actions" style="display: flex; gap: 10px;">
                        <button class="btn btn-primary btn-sm" onclick="refresh_dashboard('${workflow_state}')">
                            <i class="fa fa-refresh"></i> Refresh
                        </button>
                        <button class="btn btn-success btn-sm" onclick="show_filters_dialog('${workflow_state}')">
                            <i class="fa fa-filter"></i> Filters
                        </button>
                        <button class="btn btn-info btn-sm" onclick="export_dashboard_data('${workflow_state}')">
                            <i class="fa fa-download"></i> Export
                        </button>
                    </div>
                </div>
                
                <!-- Advanced Filters Bar -->
                <div id="filters-bar" style="background: #f8f9fa; padding: 10px; border-radius: 5px; margin-bottom: 15px; display: none;">
                    <div style="display: flex; gap: 15px; align-items: center; flex-wrap: wrap;">
                        <div>
                            <label style="font-size: 0.85em; color: #666;">Supplier:</label>
                            <input type="text" id="supplier-filter" placeholder="Search supplier..." style="padding: 4px 8px; border: 1px solid #ddd; border-radius: 3px; width: 150px;">
                        </div>
                        <div>
                            <label style="font-size: 0.85em; color: #666;">Branch:</label>
                            <select id="branch-filter" style="padding: 4px 8px; border: 1px solid #ddd; border-radius: 3px; width: 120px;">
                                <option value="">All Branches</option>
                            </select>
                        </div>
                        <div>
                            <label style="font-size: 0.85em; color: #666;">Date Range:</label>
                            <input type="date" id="from-date" style="padding: 4px 8px; border: 1px solid #ddd; border-radius: 3px; width: 130px;">
                            <span style="margin: 0 5px;">to</span>
                            <input type="date" id="to-date" style="padding: 4px 8px; border: 1px solid #ddd; border-radius: 3px; width: 130px;">
                        </div>
                        <div>
                            <button class="btn btn-primary btn-xs" onclick="apply_filters('${workflow_state}')">Apply</button>
                            <button class="btn btn-default btn-xs" onclick="clear_filters('${workflow_state}')">Clear</button>
                        </div>
                    </div>
                </div>
                
                <!-- Bulk Actions Bar -->
                <div id="bulk-actions-bar" style="background: #e8f4fd; padding: 10px; border-radius: 5px; margin-bottom: 15px; display: none;">
                    <div style="display: flex; gap: 10px; align-items: center;">
                        <span style="font-weight: 500; color: #2c3e50;">
                            <span id="selected-count">0</span> items selected
                        </span>
                        <div class="bulk-action-buttons" style="display: flex; gap: 8px;">
                            <button class="btn btn-success btn-xs" onclick="bulk_approve_pos()">
                                <i class="fa fa-check"></i> Approve
                            </button>
                            <button class="btn btn-danger btn-xs" onclick="bulk_reject_pos()">
                                <i class="fa fa-times"></i> Reject
                            </button>
                            <button class="btn btn-info btn-xs" onclick="bulk_create_pr()">
                                <i class="fa fa-plus"></i> Create PR
                            </button>
                            <button class="btn btn-warning btn-xs" onclick="bulk_create_pi()">
                                <i class="fa fa-file-text"></i> Create PI
                            </button>
                        </div>
                        <button class="btn btn-default btn-xs" onclick="clear_selection()">Clear Selection</button>
                    </div>
                </div>
            </div>
            
            <div class="dashboard-stats" style="display: flex; justify-content: space-around; margin-bottom: 30px; flex-wrap: wrap;">
                <div class="stat-card" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; text-align: center; min-width: 200px; margin: 10px;">
                    <h3 style="margin: 0; font-size: 2em;">${summary.total_orders}</h3>
                    <p style="margin: 5px 0 0 0; opacity: 0.9;">Total Orders</p>
                </div>
                <div class="stat-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; padding: 20px; border-radius: 10px; text-align: center; min-width: 200px; margin: 10px;">
                    <h3 style="margin: 0; font-size: 2em;">${format_currency(summary.total_amount)}</h3>
                    <p style="margin: 5px 0 0 0; opacity: 0.9;">Total Value</p>
                </div>
                <div class="stat-card" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white; padding: 20px; border-radius: 10px; text-align: center; min-width: 200px; margin: 10px;">
                    <h3 style="margin: 0; font-size: 2em;">${format_currency(summary.avg_amount)}</h3>
                    <p style="margin: 5px 0 0 0; opacity: 0.9;">Average Value</p>
                </div>
                <div class="stat-card" style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); color: white; padding: 20px; border-radius: 10px; text-align: center; min-width: 200px; margin: 10px;">
                    <h3 style="margin: 0; font-size: 2em;">${summary.unique_suppliers}</h3>
                    <p style="margin: 5px 0 0 0; opacity: 0.9;">Unique Suppliers</p>
                </div>
            </div>
            
            <div class="dashboard-content" style="display: block;">
                <div class="po-list-section" style="width: 100%; margin-bottom: 30px;">
                    <h4 style="color: #2c3e50; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 2px solid #ecf0f1;">📋 Purchase Orders List</h4>
                    <div class="po-table-container" style="max-height: 400px; overflow-y: auto; border: 1px solid #ddd; border-radius: 5px;">
                        ${generate_po_table(purchase_orders)}
                    </div>
                </div>
                
                <div class="supplier-stats-section" style="width: 100%;">
                    <h4 style="color: #2c3e50; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 2px solid #ecf0f1;">👥 Supplier Statistics</h4>
                    <div class="supplier-stats" style="max-height: 300px; overflow-y: auto;">
                        ${generate_supplier_stats(supplier_stats)}
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Create and show the dashboard dialog
    let dashboard_dialog = new frappe.ui.Dialog({
        title: __(`Purchase Orders Overview - ${workflow_state}`),
        fields: [{
            fieldtype: 'HTML',
            fieldname: 'dashboard_html',
            options: dashboard_html
        }],
        size: 'extra-large'
    });
    
    // Set custom width to accommodate all columns
    dashboard_dialog.$wrapper.find('.modal-dialog').css({
        'max-width': '95vw',
        'width': '95vw'
    });
    
    dashboard_dialog.show();
    
    // Add click handlers for PO links
    setTimeout(() => {
        dashboard_dialog.$wrapper.find('.po-link').on('click', function(e) {
            e.preventDefault();
            let po_name = $(this).data('po-name');
            frappe.set_route('Form', 'Purchase Order', po_name);
            dashboard_dialog.hide();
        });
    }, 100);
}

function generate_po_table(purchase_orders) {
    if (!purchase_orders || purchase_orders.length === 0) {
        return `
            <div style="text-align: center; padding: 40px; color: #6c757d;">
                <i class="fa fa-inbox" style="font-size: 3em; margin-bottom: 15px; display: block;"></i>
                <h4>No Purchase Orders Found</h4>
                <p>There are no Purchase Orders in this workflow state.</p>
            </div>
        `;
    }
    
    let table_html = `
        <table class="table table-striped table-bordered" style="margin: 0; font-size: 0.8em; width: 100%; table-layout: fixed;">
            <thead style="background: #f8f9fa;">
                <tr>
                    <th style="padding: 5px; border: 1px solid #dee2e6; width: 3%;">
                        <input type="checkbox" id="select-all-pos" onchange="toggle_all_selection()" style="transform: scale(0.9);">
                    </th>
                    <th style="padding: 5px; border: 1px solid #dee2e6; width: 11%;">PO No (FULL)</th>
                    <th style="padding: 5px; border: 1px solid #dee2e6; width: 13%;">Supplier</th>
                    <th style="padding: 5px; border: 1px solid #dee2e6; width: 10%;">Approved At</th>
                    <th style="padding: 5px; border: 1px solid #dee2e6; width: 8%;">Branch</th>
                    <th style="padding: 5px; border: 1px solid #dee2e6; width: 8%;">Sub Branch</th>
                    <th style="padding: 5px; border: 1px solid #dee2e6; width: 10%;">Created By</th>
                    <th style="padding: 5px; border: 1px solid #dee2e6; width: 7%;">Status</th>
                    <th style="padding: 5px; border: 1px solid #dee2e6; width: 11%;">Purchase Receipt</th>
                    <th style="padding: 5px; border: 1px solid #dee2e6; width: 7%;">Grand Total</th>
                    <th style="padding: 5px; border: 1px solid #dee2e6; width: 12%;">Actions</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    purchase_orders.forEach(po => {
        let status_color = get_status_color(po.status);
        let approved_at = po.custom__approved_at ? frappe.datetime.str_to_user(po.custom__approved_at) : '';
        
        table_html += `
            <tr class="po-row" data-po-name="${po.name}">
                <td style="padding: 5px; border: 1px solid #dee2e6; text-align: center;">
                    <input type="checkbox" class="po-checkbox" value="${po.name}" onchange="update_selection_count()" style="transform: scale(0.9);">
                </td>
                <td style="padding: 5px; border: 1px solid #dee2e6; word-wrap: break-word; overflow: hidden;">
                    <a href="#Form/Purchase Order/${po.name}" style="color: #007bff; text-decoration: none; font-weight: 500;" onclick="event.stopPropagation();">
                        ${po.name}
                    </a>
                </td>
                <td style="padding: 5px; border: 1px solid #dee2e6; word-wrap: break-word; overflow: hidden;" title="${po.supplier || ''}">${po.supplier || ''}</td>
                <td style="padding: 5px; border: 1px solid #dee2e6; word-wrap: break-word; overflow: hidden;">${approved_at}</td>
                <td style="padding: 5px; border: 1px solid #dee2e6; word-wrap: break-word; overflow: hidden;" title="${po.custom_branch || ''}">${po.custom_branch || ''}</td>
                <td style="padding: 5px; border: 1px solid #dee2e6; word-wrap: break-word; overflow: hidden;" title="${po.custom_sub_branch || ''}">${po.custom_sub_branch || ''}</td>
                <td style="padding: 5px; border: 1px solid #dee2e6; word-wrap: break-word; overflow: hidden;" title="${po.custom_created_by || po.owner || ''}">${po.custom_created_by || po.owner || ''}</td>
                <td style="padding: 5px; border: 1px solid #dee2e6; text-align: center;">
                    <span style="background: ${status_color}; color: white; padding: 2px 4px; border-radius: 8px; font-size: 0.7em; font-weight: 500;">
                        ${po.status || ''}
                    </span>
                </td>
                <td style="padding: 5px; border: 1px solid #dee2e6; word-wrap: break-word; overflow: hidden;">
                    ${po.custom_purchase_receipt ? 
                        `<a href="#Form/Purchase Receipt/${po.custom_purchase_receipt}" style="color: #007bff; text-decoration: none; font-weight: 500;" title="${po.custom_purchase_receipt}" onclick="event.stopPropagation();">
                            ${po.custom_purchase_receipt}
                        </a>` : 
                        '<span style="color: #6c757d;">Not Created</span>'
                    }
                </td>
                <td style="padding: 5px; border: 1px solid #dee2e6; text-align: right; font-weight: 500;">
                    ${format_currency(po.grand_total || 0)}
                </td>
                <td style="padding: 5px; border: 1px solid #dee2e6; text-align: center;">
                    <div class="btn-group" style="display: flex; gap: 2px;">
                        <button class="btn btn-xs btn-success" onclick="approve_po('${po.name}')" title="Approve">
                            <i class="fa fa-check" style="font-size: 0.7em;"></i>
                        </button>
                        <button class="btn btn-xs btn-danger" onclick="reject_po('${po.name}')" title="Reject">
                            <i class="fa fa-times" style="font-size: 0.7em;"></i>
                        </button>
                        <button class="btn btn-xs btn-info" onclick="create_pr_from_po('${po.name}')" title="Create PR">
                            <i class="fa fa-plus" style="font-size: 0.7em;"></i>
                        </button>
                        <button class="btn btn-xs btn-warning" onclick="create_pi_from_po('${po.name}')" title="Create PI">
                            <i class="fa fa-file-text" style="font-size: 0.7em;"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    });
    
    table_html += `
            </tbody>
        </table>
    `;
    
    return table_html;
}

function generate_supplier_stats(supplier_stats) {
    let stats_html = '';
    
    // Convert supplier_stats object to array and sort by total amount
    let sorted_suppliers = Object.entries(supplier_stats)
        .sort((a, b) => b[1].total - a[1].total)
        .slice(0, 10); // Top 10 suppliers
    
    let total_all_suppliers = Object.values(supplier_stats).reduce((sum, s) => sum + s.total, 0);
    
    sorted_suppliers.forEach(([supplier, stats]) => {
        let percentage = total_all_suppliers > 0 ? ((stats.total / total_all_suppliers) * 100).toFixed(1) : 0;
        stats_html += `
            <div class="supplier-card" style="background: white; border: 1px solid #e1e8ed; border-radius: 8px; padding: 15px; margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <h5 style="margin: 0 0 8px 0; color: #2c3e50; font-size: 0.95em;">${supplier}</h5>
                <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                    <span style="color: #7f8c8d; font-size: 0.85em;">Orders:</span>
                    <span style="font-weight: 500;">${stats.count}</span>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <span style="color: #7f8c8d; font-size: 0.85em;">Total:</span>
                    <span style="font-weight: 500; color: #27ae60;">${format_currency(stats.total)}</span>
                </div>
                <div style="background-color: #ecf0f1; border-radius: 10px; height: 6px; overflow: hidden;">
                    <div style="background: linear-gradient(90deg, #3498db, #2ecc71); height: 100%; width: ${percentage}%; transition: width 0.3s ease;"></div>
                </div>
                <div style="text-align: right; margin-top: 5px;">
                    <span style="font-size: 0.8em; color: #7f8c8d;">${percentage}%</span>
                </div>
            </div>
        `;
    });
    
    return stats_html;
}

function get_status_color(status) {
    const status_colors = {
        'Draft': '#6c757d',
        'To Receive and Bill': '#17a2b8',
        'To Bill': '#ffc107',
        'To Receive': '#28a745',
        'Completed': '#28a745',
        'Cancelled': '#dc3545',
        'Closed': '#6f42c1',
        'On Hold': '#fd7e14'
    };
    return status_colors[status] || '#6c757d';
}

// ===== ADVANCED DASHBOARD FUNCTIONS =====

window.refresh_dashboard = function(workflow_state) {
    console.log(`🔄 Refreshing dashboard for workflow state: ${workflow_state}`);
    create_dashboard_dialog(workflow_state, null);
}

window.show_filters_dialog = function(workflow_state) {
    let filters_bar = document.getElementById('filters-bar');
    if (filters_bar.style.display === 'none') {
        filters_bar.style.display = 'block';
        load_filter_options();
    } else {
        filters_bar.style.display = 'none';
    }
}

window.load_filter_options = function() {
    frappe.call({
        method: 'o2o_erpnext.dashboard.get_dashboard_filters',
        callback: function(r) {
            if (r.message && r.message.success) {
                let branch_select = document.getElementById('branch-filter');
                branch_select.innerHTML = '<option value="">All Branches</option>';
                
                r.message.data.branches.forEach(branch => {
                    branch_select.innerHTML += `<option value="${branch}">${branch}</option>`;
                });
            }
        }
    });
}

window.apply_filters = function(workflow_state) {
    let filters = {
        supplier: document.getElementById('supplier-filter').value,
        branch: document.getElementById('branch-filter').value,
        date_range: {
            from_date: document.getElementById('from-date').value,
            to_date: document.getElementById('to-date').value
        }
    };
    
    frappe.call({
        method: 'o2o_erpnext.dashboard.get_po_dashboard_data',
        args: {
            workflow_state: workflow_state,
            filters: JSON.stringify(filters)
        },
        callback: function(r) {
            if (r.message && r.message.success) {
                // Update the dashboard with filtered data
                let dashboard_content = document.querySelector('.po-overview-dashboard');
                if (dashboard_content) {
                    show_advanced_dashboard(workflow_state, r.message.data);
                }
            }
        }
    });
}

window.clear_filters = function(workflow_state) {
    document.getElementById('supplier-filter').value = '';
    document.getElementById('branch-filter').value = '';
    document.getElementById('from-date').value = '';
    document.getElementById('to-date').value = '';
    apply_filters(workflow_state);
}

window.export_dashboard_data = function(workflow_state) {
    frappe.msgprint('Export functionality will be implemented soon!');
}

window.toggle_all_selection = function() {
    let select_all = document.getElementById('select-all-pos');
    let checkboxes = document.querySelectorAll('.po-checkbox');
    
    checkboxes.forEach(checkbox => {
        checkbox.checked = select_all.checked;
    });
    
    update_selection_count();
}

window.update_selection_count = function() {
    let selected_checkboxes = document.querySelectorAll('.po-checkbox:checked');
    let count = selected_checkboxes.length;
    
    document.getElementById('selected-count').textContent = count;
    
    let bulk_actions_bar = document.getElementById('bulk-actions-bar');
    if (count > 0) {
        bulk_actions_bar.style.display = 'block';
    } else {
        bulk_actions_bar.style.display = 'none';
    }
}

window.clear_selection = function() {
    document.getElementById('select-all-pos').checked = false;
    document.querySelectorAll('.po-checkbox').forEach(checkbox => {
        checkbox.checked = false;
    });
    update_selection_count();
}

window.get_selected_pos = function() {
    let selected_pos = [];
    document.querySelectorAll('.po-checkbox:checked').forEach(checkbox => {
        selected_pos.push(checkbox.value);
    });
    return selected_pos;
}

// ===== WORKFLOW ACTION FUNCTIONS =====

window.approve_po = function(po_name) {
    // First get available workflow actions for this PO
    frappe.call({
        method: 'o2o_erpnext.dashboard.get_workflow_actions',
        args: {
            po_name: po_name
        },
        callback: function(r) {
            if (r.message && r.message.success) {
                let transitions = r.message.data.transitions;
                let approve_actions = transitions.filter(t => 
                    t.action.toLowerCase().includes('approve') || 
                    t.action === 'PO Approve' || 
                    t.action === 'Requisition Approve'
                );
                
                if (approve_actions.length === 0) {
                    frappe.show_alert({
                        message: 'No approval actions available for this Purchase Order',
                        indicator: 'orange'
                    });
                    return;
                }
                
                // If multiple approval actions, show dialog to choose
                if (approve_actions.length > 1) {
                    let d = new frappe.ui.Dialog({
                        title: 'Select Approval Action',
                        fields: [{
                            label: 'Action',
                            fieldname: 'action',
                            fieldtype: 'Select',
                            options: approve_actions.map(a => a.action).join('\n'),
                            reqd: 1
                        }],
                        primary_action_label: 'Approve',
                        primary_action(values) {
                            apply_workflow_action_to_po(po_name, values.action, 'approve');
                            d.hide();
                        }
                    });
                    d.show();
                } else {
                    // Single approval action available
                    frappe.confirm(
                        `Are you sure you want to approve Purchase Order ${po_name}?`,
                        () => {
                            apply_workflow_action_to_po(po_name, approve_actions[0].action, 'approve');
                        }
                    );
                }
            } else {
                frappe.show_alert({
                    message: r.message.message || 'Error getting workflow actions',
                    indicator: 'red'
                });
            }
        }
    });
}

window.reject_po = function(po_name) {
    // First get available workflow actions for this PO
    frappe.call({
        method: 'o2o_erpnext.dashboard.get_workflow_actions',
        args: {
            po_name: po_name
        },
        callback: function(r) {
            if (r.message && r.message.success) {
                let transitions = r.message.data.transitions;
                let reject_actions = transitions.filter(t => 
                    t.action.toLowerCase().includes('reject') || 
                    t.action === 'PO Reject' || 
                    t.action === 'Requisition Reject'
                );
                
                if (reject_actions.length === 0) {
                    frappe.show_alert({
                        message: 'No rejection actions available for this Purchase Order',
                        indicator: 'orange'
                    });
                    return;
                }
                
                // If multiple rejection actions, show dialog to choose
                if (reject_actions.length > 1) {
                    let d = new frappe.ui.Dialog({
                        title: 'Select Rejection Action',
                        fields: [{
                            label: 'Action',
                            fieldname: 'action',
                            fieldtype: 'Select',
                            options: reject_actions.map(a => a.action).join('\n'),
                            reqd: 1
                        }],
                        primary_action_label: 'Reject',
                        primary_action(values) {
                            apply_workflow_action_to_po(po_name, values.action, 'reject');
                            d.hide();
                        }
                    });
                    d.show();
                } else {
                    // Single rejection action available
                    frappe.confirm(
                        `Are you sure you want to reject Purchase Order ${po_name}?`,
                        () => {
                            apply_workflow_action_to_po(po_name, reject_actions[0].action, 'reject');
                        }
                    );
                }
            } else {
                frappe.show_alert({
                    message: r.message.message || 'Error getting workflow actions',
                    indicator: 'red'
                });
            }
        }
    });
}

// Helper function to apply workflow action
window.apply_workflow_action_to_po = function(po_name, action, action_type) {
    frappe.call({
        method: 'o2o_erpnext.dashboard.apply_workflow_action',
        args: {
            po_name: po_name,
            action: action
        },
        callback: function(r) {
            if (r.message && r.message.success) {
                frappe.show_alert({
                    message: r.message.message,
                    indicator: action_type === 'approve' ? 'green' : 'orange'
                });
                refresh_dashboard(get_current_workflow_state());
            } else {
                frappe.show_alert({
                    message: r.message.message || `Error ${action_type}ing PO`,
                    indicator: 'red'
                });
            }
        }
    });
}

window.create_pr_from_po = function(po_name) {
    frappe.call({
        method: 'o2o_erpnext.dashboard.create_purchase_receipt',
        args: {
            po_name: po_name
        },
        callback: function(r) {
            if (r.message && r.message.success) {
                frappe.show_alert({
                    message: r.message.message,
                    indicator: 'green'
                });
                // Open the created Purchase Receipt
                frappe.set_route('Form', 'Purchase Receipt', r.message.data.pr_name);
            } else {
                frappe.show_alert({
                    message: r.message.message || 'Error creating Purchase Receipt',
                    indicator: 'red'
                });
            }
        }
    });
}

window.create_pi_from_po = function(po_name) {
    frappe.call({
        method: 'o2o_erpnext.dashboard.create_purchase_invoice',
        args: {
            po_name: po_name
        },
        callback: function(r) {
            if (r.message && r.message.success) {
                frappe.show_alert({
                    message: r.message.message,
                    indicator: 'green'
                });
                // Open the created Purchase Invoice
                frappe.set_route('Form', 'Purchase Invoice', r.message.data.pi_name);
            } else {
                frappe.show_alert({
                    message: r.message.message || 'Error creating Purchase Invoice',
                    indicator: 'red'
                });
            }
        }
    });
}

// ===== BULK ACTION FUNCTIONS =====

window.bulk_approve_pos = function() {
    let selected_pos = get_selected_pos();
    if (selected_pos.length === 0) {
        frappe.msgprint('Please select Purchase Orders to approve');
        return;
    }
    
    // Get available actions for the first PO to determine bulk action
    frappe.call({
        method: 'o2o_erpnext.dashboard.get_workflow_actions',
        args: {
            po_name: selected_pos[0]
        },
        callback: function(r) {
            if (r.message && r.message.success) {
                let transitions = r.message.data.transitions;
                let approve_actions = transitions.filter(t => 
                    t.action.toLowerCase().includes('approve') || 
                    t.action === 'PO Approve' || 
                    t.action === 'Requisition Approve'
                );
                
                if (approve_actions.length === 0) {
                    frappe.show_alert({
                        message: 'No approval actions available for selected Purchase Orders',
                        indicator: 'orange'
                    });
                    return;
                }
                
                let action_to_use = approve_actions[0].action;
                
                frappe.confirm(
                    `Are you sure you want to apply "${action_to_use}" to ${selected_pos.length} Purchase Orders?`,
                    () => {
                        frappe.call({
                            method: 'o2o_erpnext.dashboard.bulk_workflow_action',
                            args: {
                                po_names: JSON.stringify(selected_pos),
                                action: action_to_use
                            },
                            callback: function(r) {
                                if (r.message && r.message.success) {
                                    frappe.show_alert({
                                        message: r.message.message,
                                        indicator: 'green'
                                    });
                                    clear_selection();
                                    refresh_dashboard(get_current_workflow_state());
                                } else {
                                    frappe.show_alert({
                                        message: r.message.message || 'Error in bulk approval',
                                        indicator: 'red'
                                    });
                                }
                            }
                        });
                    }
                );
            } else {
                frappe.show_alert({
                    message: 'Error getting workflow actions for bulk operation',
                    indicator: 'red'
                });
            }
        }
    });
}

window.bulk_reject_pos = function() {
    let selected_pos = get_selected_pos();
    if (selected_pos.length === 0) {
        frappe.msgprint('Please select Purchase Orders to reject');
        return;
    }
    
    // Get available actions for the first PO to determine bulk action
    frappe.call({
        method: 'o2o_erpnext.dashboard.get_workflow_actions',
        args: {
            po_name: selected_pos[0]
        },
        callback: function(r) {
            if (r.message && r.message.success) {
                let transitions = r.message.data.transitions;
                let reject_actions = transitions.filter(t => 
                    t.action.toLowerCase().includes('reject') || 
                    t.action === 'PO Reject' || 
                    t.action === 'Requisition Reject'
                );
                
                if (reject_actions.length === 0) {
                    frappe.show_alert({
                        message: 'No rejection actions available for selected Purchase Orders',
                        indicator: 'orange'
                    });
                    return;
                }
                
                let action_to_use = reject_actions[0].action;
                
                frappe.confirm(
                    `Are you sure you want to apply "${action_to_use}" to ${selected_pos.length} Purchase Orders?`,
                    () => {
                        frappe.call({
                            method: 'o2o_erpnext.dashboard.bulk_workflow_action',
                            args: {
                                po_names: JSON.stringify(selected_pos),
                                action: action_to_use
                            },
                            callback: function(r) {
                                if (r.message && r.message.success) {
                                    frappe.show_alert({
                                        message: r.message.message,
                                        indicator: 'orange'
                                    });
                                    clear_selection();
                                    refresh_dashboard(get_current_workflow_state());
                                } else {
                                    frappe.show_alert({
                                        message: r.message.message || 'Error in bulk rejection',
                                        indicator: 'red'
                                    });
                                }
                            }
                        });
                    }
                );
            } else {
                frappe.show_alert({
                    message: 'Error getting workflow actions for bulk operation',
                    indicator: 'red'
                });
            }
        }
    });
}

window.bulk_create_pr = function() {
    let selected_pos = get_selected_pos();
    if (selected_pos.length === 0) {
        frappe.msgprint('Please select Purchase Orders to create Purchase Receipts');
        return;
    }
    
    frappe.msgprint(`Creating Purchase Receipts for ${selected_pos.length} Purchase Orders...`);
    
    let promises = selected_pos.map(po_name => {
        return new Promise((resolve, reject) => {
            frappe.call({
                method: 'o2o_erpnext.dashboard.create_purchase_receipt',
                args: { po_name: po_name },
                callback: function(r) {
                    if (r.message && r.message.success) {
                        resolve(r.message.data.pr_name);
                    } else {
                        reject(r.message.message || 'Error creating PR');
                    }
                }
            });
        });
    });
    
    Promise.allSettled(promises).then(results => {
        let successful = results.filter(r => r.status === 'fulfilled').length;
        let failed = results.filter(r => r.status === 'rejected').length;
        
        frappe.show_alert({
            message: `Created ${successful} Purchase Receipts. ${failed} failed.`,
            indicator: successful > 0 ? 'green' : 'red'
        });
        
        clear_selection();
        refresh_dashboard(get_current_workflow_state());
    });
}

window.bulk_create_pi = function() {
    let selected_pos = get_selected_pos();
    if (selected_pos.length === 0) {
        frappe.msgprint('Please select Purchase Orders to create Purchase Invoices');
        return;
    }
    
    frappe.msgprint(`Creating Purchase Invoices for ${selected_pos.length} Purchase Orders...`);
    
    let promises = selected_pos.map(po_name => {
        return new Promise((resolve, reject) => {
            frappe.call({
                method: 'o2o_erpnext.dashboard.create_purchase_invoice',
                args: { po_name: po_name },
                callback: function(r) {
                    if (r.message && r.message.success) {
                        resolve(r.message.data.pi_name);
                    } else {
                        reject(r.message.message || 'Error creating PI');
                    }
                }
            });
        });
    });
    
    Promise.allSettled(promises).then(results => {
        let successful = results.filter(r => r.status === 'fulfilled').length;
        let failed = results.filter(r => r.status === 'rejected').length;
        
        frappe.show_alert({
            message: `Created ${successful} Purchase Invoices. ${failed} failed.`,
            indicator: successful > 0 ? 'green' : 'red'
        });
        
        clear_selection();
        refresh_dashboard(get_current_workflow_state());
    });
}

window.get_current_workflow_state = function() {
    // Get current workflow state from dashboard title
    let title_element = document.querySelector('.po-overview-dashboard h3 span');
    return title_element ? title_element.textContent : 'Awaiting Approval';
}

console.log("✅ Purchase Order List Script Completed");