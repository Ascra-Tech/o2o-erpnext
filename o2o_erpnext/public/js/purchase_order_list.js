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
    
    console.log("✅ Print and Export buttons added successfully");
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

// Debug function to check if script is loaded
console.log("✅ Purchase Order List Script Loaded Successfully");

// ===== MERGED CONTENT FROM purchase_order_view.js =====
// Note: List view enhancement removed to prevent filter issues

// ===== FORM FUNCTIONALITY REMOVED =====
// Purchase Receipt form functionality removed to prevent display issues
// Automatic linking now handled purely server-side via Purchase Receipt hooks

console.log("✅ Purchase Order List Script Completed");