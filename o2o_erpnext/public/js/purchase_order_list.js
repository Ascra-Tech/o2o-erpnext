// ========================================
// Purchase Order List - PO Scanner & Statistics
// ========================================
// This file adds PO Scanner functionality to Purchase Order list view
// Using doctype_list_js pattern - Following purchase_invoice_list.js approach
// ========================================

// Store listview reference globally for use in other functions
window.purchase_order_listview = null;

frappe.listview_settings['Purchase Order'] = {
    hide_name_column: true,
    onload: function(listview) {
        console.log("Purchase Order List View onload called");
        
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
        // Hide like icons (from client script)
        $("use.like-icon").hide();
    }
};

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

    // Add Print PR button
    listview.page.add_button(__('Print PR'), function() {
        let selected = listview.get_checked_items();
        if (!selected.length || selected.length > 1) {
            frappe.msgprint('Please select one Purchase Order');
            return;
        }

        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                doctype: 'Purchase Receipt',
                filters: [['Purchase Receipt Item', 'purchase_order', '=', selected[0].name]],
                fields: ['name', 'posting_date', 'supplier', 'grand_total', 'status']
            },
            callback: function(r) {
                if (!r.message?.length) {
                    frappe.msgprint('No Purchase Receipts found');
                    return;
                }

                let d = new frappe.ui.Dialog({
                    title: 'Select Purchase Receipt to Print',
                    fields: [{
                        label: 'Select Purchase Receipt',
                        fieldname: 'selected_pr',
                        fieldtype: 'Select',
                        options: r.message.map(pr => ({
                            label: `${pr.name} | ${frappe.datetime.str_to_user(pr.posting_date)} | ${format_currency(pr.grand_total)}`,
                            value: pr.name
                        })),
                        reqd: 1
                    }],
                    primary_action_label: 'Print',
                    primary_action(values) {
                        frappe.set_route('print', 'Purchase Receipt', values.selected_pr);
                        d.hide();
                    }
                });

                let receipt_list = `<div class="receipt-list" style="margin-top: 10px;">
                    <table class="table table-bordered">
                        <thead>
                            <tr>
                                <th>Receipt No</th>
                                <th>Date</th>
                                <th>Status</th>
                                <th>Amount</th>
                            </tr>
                        </thead>
                        <tbody>
                        ${r.message.map(pr => `
                            <tr>
                                <td>${pr.name}</td>
                                <td>${frappe.datetime.str_to_user(pr.posting_date)}</td>
                                <td>${pr.status}</td>
                                <td>${format_currency(pr.grand_total)}</td>
                            </tr>
                        `).join('')}
                        </tbody>
                    </table>
                </div>`;
                
                d.fields_dict.selected_pr.$wrapper.append(receipt_list);
                d.show();
            }
        });
    }, true).addClass('btn-primary');
    
    console.log("✅ Print buttons added successfully");
}

function hide_ui_elements(listview) {
    console.log("🔧 Hiding UI elements");
    
    if (!listview || !listview.page) {
        console.error("❌ Invalid listview for hiding UI elements");
        return;
    }
    
    // Hide specific action buttons (from client script)
    listview.page.actions.find('[data-label="Edit"],[data-label="Print"],[data-label="Export"],[data-label="Assign%20To"],[data-label="Apply%20Assignment%20Rule"],[data-label="Add%20Tags"]').parent().parent().remove();
    
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

// Debug function to check if script is loaded
console.log("✅ Purchase Order List Script Loaded Successfully");