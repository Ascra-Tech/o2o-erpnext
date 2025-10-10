// ========================================
// Purchase Invoice List - Portal Sync Tools
// ========================================
// This file adds sync functionality to Purchase Invoice list view
// Using doctype_list_js pattern
// ========================================

frappe.listview_settings['Purchase Invoice'] = {
    onload: function(listview) {
        console.log("Purchase Invoice List View onload called");
        
        // Add Portal Sync Tools dropdown
        setTimeout(function() {
            add_portal_sync_dropdown(listview);
        }, 500);
        
        console.log("Portal Sync Tools dropdown setup complete");
    }
};

function add_portal_sync_dropdown(listview) {
    console.log("🔧 Adding Portal Sync Tools dropdown");
    
    if (!listview || !listview.page) {
        console.error("❌ Invalid listview");
        return;
    }
    
    // Remove existing dropdown if any
    $(listview.page.page_actions).find('.portal-sync-tools-dropdown').remove();
    
    // Create dropdown HTML using the exact pattern from living_dna_manager
    let dropdown_html = `
        <div class="portal-sync-tools-dropdown btn-group" style="display: inline-block;">
            <button type="button" class="btn btn-primary" onclick="show_advanced_portal_dashboard()">
                Portal Sync Tools
            </button>
            <button type="button" class="btn btn-primary dropdown-toggle" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                <span class="caret"></span>
            </button>
            <ul class="dropdown-menu" role="menu">
                <li><a href="#" onclick="show_advanced_portal_dashboard(); return false;">
                    <i class="fa fa-chart-line"></i> Portal Dashboard
                </a></li>
                <li class="divider"></li>
                <li><a href="#" onclick="batch_import_invoices(); return false;">
                    <i class="fa fa-upload"></i> Invoice Batch Import
                </a></li>
                <li><a href="#" onclick="fetch_single_invoice(); return false;">
                    <i class="fa fa-search"></i> Fetch Single Invoice
                </a></li>
                <li class="divider"></li>
                <li><a href="#" onclick="sync_to_procureuat(); return false;">
                    <i class="fa fa-cloud"></i> Send to AGO2O-PHP
                </a></li>
                <li><a href="#" onclick="test_procureuat_connection(); return false;">
                    <i class="fa fa-plug"></i> Test Connection
                </a></li>
                <!--
                <li><a href="#" onclick="test_purchase_requisitions(); return false;">
                    <i class="fa fa-flask"></i> Test Purchase Requisitions
                </a></li>
                --> 
            </ul>
        </div>
    `;
    
    // Add to page actions using the exact same method as living_dna_manager
    $(listview.page.page_actions).prepend(dropdown_html);
    console.log("✅ Portal Sync Tools dropdown added successfully");
}

// ========================================
// GLOBAL FUNCTIONS - Same functionality, no changes to logic/design
// ========================================

window.show_advanced_portal_dashboard = function() {
    // Add custom CSS
    if (!$('#sync-tools-styles').length) {
        $('head').append(`
            <style id="sync-tools-styles">
                .sync-tools-dropdown {
                    display: inline-block !important;
                    margin-left: 10px !important;
                    vertical-align: middle !important;
                    position: relative !important;
                }
                .sync-tools-dropdown .btn {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    border: none;
                    color: white;
                    font-weight: 500;
                }
                .sync-tools-dropdown .btn:hover {
                    transform: translateY(-1px);
                    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
                }
                .sync-tools-dropdown .dropdown-menu {
                    min-width: 280px;
                    border-radius: 8px;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.15);
                }
                .sync-tools-dropdown .dropdown-item:hover {
                    background: linear-gradient(135deg, #f8f9ff 0%, #e8f0fe 100%);
                }
            </style>
        `);
    }
    
    const dropdown_html = `
        <div class="sync-tools-dropdown">
            <div class="btn-group">
                <button type="button" class="btn btn-primary btn-sm dropdown-toggle" 
                        data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                    <i class="fa fa-sync-alt"></i> Portal Sync Tools
                    <i class="fa fa-caret-down"></i>
                </button>
                <div class="dropdown-menu dropdown-menu-right">
                    <h6 class="dropdown-header">
                        <i class="fa fa-tachometer-alt"></i> Portal Dashboard
                    </h6>
                    <a class="dropdown-item" href="#" onclick="window.show_advanced_portal_dashboard(); return false;">
                        <i class="fa fa-chart-pie text-success"></i> Advanced Portal Dashboard
                    </a>
                    <div class="dropdown-divider"></div>
                    <h6 class="dropdown-header">
                        <i class="fa fa-download"></i> Import Functions
                    </h6>
                    <a class="dropdown-item" href="#" onclick="window.batch_import_invoices(); return false;">
                        <i class="fa fa-download text-success"></i> Batch Import
                    </a>
                    <a class="dropdown-item" href="#" onclick="window.fetch_single_invoice(); return false;">
                        <i class="fa fa-search text-info"></i> Fetch Single Invoice
                    </a>
                    <div class="dropdown-divider"></div>
                    <h6 class="dropdown-header">
                        <i class="fa fa-tools"></i> System Tools
                    </h6>
                    <a class="dropdown-item" href="#" onclick="window.sync_to_procureuat(); return false;">
                        <i class="fa fa-cloud-upload-alt text-warning"></i> Sync to ProcureUAT
                    </a>
                    <a class="dropdown-item" href="#" onclick="window.test_procureuat_connection(); return false;">
                        <i class="fa fa-plug text-secondary"></i> Test Connection
                    </a>
                    <a class="dropdown-item" href="#" onclick="window.test_purchase_requisitions(); return false;">
                        <i class="fa fa-database text-info"></i> Test Purchase Requisitions
                    </a>
                </div>
            </div>
        </div>
    `;
    
    // Try to add to standard actions
    let $container = listview.page.wrapper.find('.standard-actions');
    if ($container.length) {
        $container.append(dropdown_html);
        console.log("✅ Custom dropdown added");
        
        // Initialize dropdown
        setTimeout(() => {
            listview.page.wrapper.find('.sync-tools-dropdown .dropdown-toggle').dropdown();
        }, 100);
    }
}

// Show sync menu as modal (alternative approach)
function show_sync_menu() {
    const menu_items = [
        {
            label: '📋 Show Portal Invoices',
            action: 'show_php_portal_invoices',
            description: 'Browse and import recent invoices from portal'
        },
        {
            label: '📥 Batch Import',
            action: 'batch_import_invoices',
            description: 'Import multiple invoices with options'
        },
        {
            label: '🔍 Fetch Single Invoice',
            action: 'fetch_single_invoice',
            description: 'Get specific invoice by number'
        },
        {
            label: '☁️ Sync to ProcureUAT',
            action: 'sync_to_procureuat',
            description: 'Sync selected invoices to external system'
        },
        {
            label: '🔌 Test Connection',
            action: 'test_procureuat_connection',
            description: 'Verify database connectivity'
        }
    ];
    
    let html = '<div class="sync-menu-items">';
    menu_items.forEach(item => {
        html += `
            <div class="sync-menu-item" style="padding: 15px; border-bottom: 1px solid #eee; cursor: pointer;"
                 onclick="window.${item.action}(); cur_dialog.hide();">
                <div style="font-weight: 600; margin-bottom: 5px;">${item.label}</div>
                <div style="font-size: 12px; color: #888;">${item.description}</div>
            </div>
        `;
    });
    html += '</div>';
    
    frappe.msgprint({
        title: __('Sync Tools'),
        message: html,
        primary_action: {
            label: __('Close'),
            action: function() {
                cur_dialog.hide();
            }
        }
    });
}

// ========================================
// GLOBAL FUNCTIONS - Make them available globally
// ========================================

// ========================================
// PURCHASE REQUISITIONS FUNCTIONS 
// Focus on Advanced Portal Dashboard only
// ========================================

window.batch_import_invoices = function() {
    console.log("📥 Batch import...");
    
    let dialog = new frappe.ui.Dialog({
        title: __('Batch Import Invoices'),
        fields: [
            {
                fieldtype: 'Int',
                fieldname: 'batch_size',
                label: __('Batch Size'),
                default: 50,
                reqd: 1
            },
            {
                fieldtype: 'Int',
                fieldname: 'total_limit',
                label: __('Total Limit'),
                default: 500,
                reqd: 1
            },
            {
                fieldtype: 'Check',
                fieldname: 'skip_duplicates',
                label: __('Skip Duplicates'),
                default: 1
            }
        ],
        primary_action_label: __('Start Import'),
        primary_action: function(values) {
            dialog.hide();
            
            // Show progress dialog for batch import
            let import_progress_dialog = new frappe.ui.Dialog({
                title: __('Batch Import Progress'),
                size: 'small',
                fields: [
                    {
                        fieldtype: 'HTML',
                        fieldname: 'import_progress_html',
                        options: `
                            <div class="import-progress-container" style="text-align: center; padding: 20px;">
                                <div class="loading-spinner" style="margin-bottom: 15px;">
                                    <div class="spinner-border text-success" role="status" style="width: 3rem; height: 3rem;">
                                        <span class="sr-only">Importing...</span>
                                    </div>
                                </div>
                                <div class="progress" style="height: 20px; margin-bottom: 15px;">
                                    <div class="progress-bar progress-bar-striped progress-bar-animated bg-success" 
                                         role="progressbar" style="width: 0%" id="import-progress-bar">
                                    </div>
                                </div>
                                <div class="progress-text">
                                    <strong id="import-progress-status">Starting batch import...</strong>
                                </div>
                                <div class="progress-details" style="margin-top: 10px; font-size: 12px; color: #666;">
                                    <span id="import-progress-details">Preparing to import ${values.total_limit} invoices in batches of ${values.batch_size}...</span>
                                </div>
                            </div>
                            <style>
                                .import-progress-container {
                                    background: linear-gradient(135deg, #f0f9f0 0%, #e8f5e8 100%);
                                    border-radius: 8px;
                                    box-shadow: inset 0 1px 3px rgba(0,0,0,0.1);
                                }
                            </style>
                        `
                    }
                ]
            });
            
            import_progress_dialog.show();
            
            // Simulate import progress
            let import_progress = 0;
            const import_progress_bar = import_progress_dialog.$wrapper.find('#import-progress-bar');
            const import_progress_status = import_progress_dialog.$wrapper.find('#import-progress-status');
            const import_progress_details = import_progress_dialog.$wrapper.find('#import-progress-details');
            
            // Step 1: Preparing
            setTimeout(() => {
                import_progress = 20;
                import_progress_bar.css('width', import_progress + '%');
                import_progress_status.text('Fetching portal data...');
                import_progress_details.text('Retrieving invoices from PHP portal...');
            }, 300);
            
            // Step 2: Processing
            setTimeout(() => {
                import_progress = 60;
                import_progress_bar.css('width', import_progress + '%');
                import_progress_status.text('Processing invoices...');
                import_progress_details.text('Creating Purchase Invoice records...');
            }, 1000);
            
            // Call the actual batch import API
            frappe.call({
                method: 'o2o_erpnext.api.php_portal_invoices.batch_import_invoices',
                args: values,
                callback: function(r) {
                    // Complete progress
                    import_progress = 100;
                    import_progress_bar.css('width', import_progress + '%');
                    import_progress_status.text('Import Complete!');
                    import_progress_details.text('Successfully processed all invoices');
                    
                    setTimeout(() => {
                        import_progress_dialog.hide();
                        
                        if (r.message && r.message.success) {
                            frappe.show_alert({
                                message: __('Successfully imported {0} invoices', [r.message.imported_count]),
                                indicator: 'green'
                            }, 5);
                            if (cur_list) cur_list.refresh();
                        } else {
                            frappe.msgprint({
                                title: __('Import Failed'),
                                message: r.message ? r.message.message : __('Unknown error occurred'),
                                indicator: 'red'
                            });
                        }
                    }, 1000);
                },
                error: function(err) {
                    import_progress_dialog.hide();
                    frappe.msgprint({
                        title: __('Import Error'),
                        message: __('Failed to import invoices from portal'),
                        indicator: 'red'
                    });
                }
            });
        }
    });
    
    dialog.show();
};

function batch_import_invoices() {
    window.batch_import_invoices();
}

window.fetch_single_invoice = function() {
    console.log("🔍 Fetch single invoice...");
    
    frappe.prompt([
        {
            fieldtype: 'Data',
            fieldname: 'invoice_number',
            label: __('Invoice Number'),
            reqd: 1
        },
        {
            fieldtype: 'Check',
            fieldname: 'create_if_not_exists',
            label: __('Create if not exists'),
            default: 1
        }
    ], function(values) {
        // Show fetch progress dialog
        let fetch_progress_dialog = new frappe.ui.Dialog({
            title: __('Fetching Invoice'),
            size: 'small',
            fields: [
                {
                    fieldtype: 'HTML',
                    fieldname: 'fetch_progress_html',
                    options: `
                        <div class="fetch-progress-container" style="text-align: center; padding: 20px;">
                            <div class="loading-spinner" style="margin-bottom: 15px;">
                                <div class="spinner-border text-info" role="status" style="width: 3rem; height: 3rem;">
                                    <span class="sr-only">Fetching...</span>
                                </div>
                            </div>
                            <div class="progress" style="height: 20px; margin-bottom: 15px;">
                                <div class="progress-bar progress-bar-striped progress-bar-animated bg-info" 
                                     role="progressbar" style="width: 0%" id="fetch-progress-bar">
                                </div>
                            </div>
                            <div class="progress-text">
                                <strong id="fetch-progress-status">Searching for invoice...</strong>
                            </div>
                            <div class="progress-details" style="margin-top: 10px; font-size: 12px; color: #666;">
                                <span id="fetch-progress-details">Looking for invoice: ${values.invoice_number}</span>
                            </div>
                        </div>
                        <style>
                            .fetch-progress-container {
                                background: linear-gradient(135deg, #e1f5fe 0%, #b3e5fc 100%);
                                border-radius: 8px;
                                box-shadow: inset 0 1px 3px rgba(0,0,0,0.1);
                            }
                        </style>
                    `
                }
            ]
        });
        
        fetch_progress_dialog.show();
        
        // Simulate fetch progress
        let fetch_progress = 0;
        const fetch_progress_bar = fetch_progress_dialog.$wrapper.find('#fetch-progress-bar');
        const fetch_progress_status = fetch_progress_dialog.$wrapper.find('#fetch-progress-status');
        const fetch_progress_details = fetch_progress_dialog.$wrapper.find('#fetch-progress-details');
        
        // Step 1: Searching
        setTimeout(() => {
            fetch_progress = 40;
            fetch_progress_bar.css('width', fetch_progress + '%');
            fetch_progress_status.text('Connecting to portal...');
            fetch_progress_details.text('Accessing PHP portal database...');
        }, 300);
        
        // Step 2: Processing
        setTimeout(() => {
            fetch_progress = 80;
            fetch_progress_bar.css('width', fetch_progress + '%');
            fetch_progress_status.text('Processing invoice...');
            fetch_progress_details.text('Creating ERPNext record...');
        }, 800);
        
        frappe.call({
            method: 'o2o_erpnext.api.php_portal_invoices.fetch_single_invoice',
            args: values,
            callback: function(r) {
                // Complete progress
                fetch_progress = 100;
                fetch_progress_bar.css('width', fetch_progress + '%');
                fetch_progress_status.text('Complete!');
                fetch_progress_details.text('Invoice fetched successfully');
                
                setTimeout(() => {
                    fetch_progress_dialog.hide();
                    
                    if (r.message && r.message.success) {
                        frappe.show_alert({
                            message: __('Successfully processed invoice {0}', [values.invoice_number]),
                            indicator: 'green'
                        }, 5);
                        
                        // Open the created/updated invoice
                        if (r.message.invoice_name) {
                            frappe.set_route('Form', 'Purchase Invoice', r.message.invoice_name);
                        }
                        
                        if (cur_list) cur_list.refresh();
                    } else {
                        // Enhanced error display with suggestions if available
                        let errorMessage = r.message ? r.message.message : __('Invoice not found in portal');
                        
                        if (r.message && r.message.suggestions && r.message.suggestions.length > 0) {
                            // Show suggestions in a more user-friendly dialog
                            const suggestionsHtml = r.message.suggestions.map(suggestion => 
                                `<button class="btn btn-sm btn-default suggestion-btn" style="margin: 2px;" data-invoice="${suggestion}">${suggestion}</button>`
                            ).join('');
                            
                            const suggestionDialog = new frappe.ui.Dialog({
                                title: __('Invoice Not Found'),
                                fields: [
                                    {
                                        fieldtype: 'HTML',
                                        fieldname: 'suggestion_html',
                                        options: `
                                            <div style="padding: 10px;">
                                                <p><strong>Invoice "${values.invoice_number}" not found in portal.</strong></p>
                                                <p>Did you mean one of these?</p>
                                                <div style="margin: 10px 0;">
                                                    ${suggestionsHtml}
                                                </div>
                                                <p style="font-size: 12px; color: #666; margin-top: 15px;">
                                                    Click on a suggestion to search for that invoice instead.
                                                </p>
                                            </div>
                                        `
                                    }
                                ],
                                primary_action_label: __('Search Again'),
                                primary_action: function() {
                                    suggestionDialog.hide();
                                    window.fetch_single_invoice();
                                }
                            });
                            
                            suggestionDialog.show();
                            
                            // Add click handlers for suggestion buttons
                            suggestionDialog.$wrapper.find('.suggestion-btn').on('click', function() {
                                const suggestedInvoice = $(this).data('invoice');
                                suggestionDialog.hide();
                                
                                // Auto-fill the prompt with the suggested invoice
                                frappe.prompt([
                                    {
                                        fieldtype: 'Data',
                                        fieldname: 'invoice_number',
                                        label: __('Invoice Number'),
                                        reqd: 1,
                                        default: suggestedInvoice
                                    },
                                    {
                                        fieldtype: 'Check',
                                        fieldname: 'create_if_not_exists',
                                        label: __('Create if not exists'),
                                        default: 1
                                    }
                                ], function(newValues) {
                                    // Re-call the fetch function with suggested invoice
                                    frappe.call({
                                        method: 'o2o_erpnext.api.php_portal_invoices.fetch_single_invoice',
                                        args: newValues,
                                        callback: function(newR) {
                                            if (newR.message && newR.message.success) {
                                                frappe.show_alert({
                                                    message: __('Successfully processed invoice {0}', [newValues.invoice_number]),
                                                    indicator: 'green'
                                                }, 5);
                                                
                                                if (newR.message.invoice_name) {
                                                    frappe.set_route('Form', 'Purchase Invoice', newR.message.invoice_name);
                                                }
                                                
                                                if (cur_list) cur_list.refresh();
                                            } else {
                                                frappe.msgprint({
                                                    title: __('Fetch Failed'),
                                                    message: newR.message ? newR.message.message : __('Invoice not found in portal'),
                                                    indicator: 'orange'
                                                });
                                            }
                                        }
                                    });
                                }, __('Fetch Suggested Invoice'));
                            });
                        } else {
                            // Standard error message
                            frappe.msgprint({
                                title: __('Fetch Failed'),
                                message: errorMessage,
                                indicator: 'orange'
                            });
                        }
                    }
                }, 800);
            },
            error: function(err) {
                fetch_progress_dialog.hide();
                frappe.msgprint({
                    title: __('Fetch Error'),
                    message: __('Failed to fetch invoice from portal'),
                    indicator: 'red'
                });
            }
        });
    }, __('Fetch Invoice'));
};

function fetch_single_invoice() {
    window.fetch_single_invoice();
}

window.sync_to_procureuat = function() {
    console.log("🚀 Push Purchase Invoice to Portal...");
    
    if (!cur_list) {
        frappe.msgprint(__('List view not available'));
        return;
    }
    
    const selected = cur_list.get_checked_items();
    if (selected.length === 0) {
        frappe.show_alert({message: __('Please select an invoice to push'), indicator: 'yellow'}, 3);
        return;
    }
    
    if (selected.length > 1) {
        frappe.show_alert({message: __('Please select only one invoice at a time'), indicator: 'yellow'}, 3);
        return;
    }
    
    const invoice_name = selected[0].name;
    
    frappe.confirm(
        __('Push Purchase Invoice "{0}" to ProcureUAT Portal?', [invoice_name]),
        function() {
            // Show push progress dialog
            let push_progress_dialog = new frappe.ui.Dialog({
                title: __('Pushing Invoice to Portal'),
                size: 'small',
                fields: [
                    {
                        fieldtype: 'HTML',
                        fieldname: 'push_progress_html',
                        options: `
                            <div class="push-progress-container" style="text-align: center; padding: 20px;">
                                <div class="loading-spinner" style="margin-bottom: 15px;">
                                    <div class="spinner-border text-primary" role="status" style="width: 3rem; height: 3rem;">
                                        <span class="sr-only">Pushing...</span>
                                    </div>
                                </div>
                                <div class="progress" style="height: 20px; margin-bottom: 15px;">
                                    <div class="progress-bar progress-bar-striped progress-bar-animated bg-primary" 
                                         role="progressbar" style="width: 0%" id="push-progress-bar">
                                    </div>
                                </div>
                                <div class="progress-text">
                                    <strong id="push-progress-status">Validating invoice...</strong>
                                </div>
                                <div class="progress-details" style="margin-top: 10px; font-size: 12px; color: #666;">
                                    <span id="push-progress-details">Preparing to push invoice "${invoice_name}" to portal...</span>
                                </div>
                            </div>
                            <style>
                                .push-progress-container {
                                    background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
                                    border-radius: 8px;
                                    box-shadow: inset 0 1px 3px rgba(0,0,0,0.1);
                                }
                            </style>
                        `
                    }
                ]
            });
            
            push_progress_dialog.show();
            
            // Progress tracking
            let push_progress = 0;
            const push_progress_bar = push_progress_dialog.$wrapper.find('#push-progress-bar');
            const push_progress_status = push_progress_dialog.$wrapper.find('#push-progress-status');
            const push_progress_details = push_progress_dialog.$wrapper.find('#push-progress-details');
            
            // Step 1: Validation
            setTimeout(() => {
                push_progress = 20;
                push_progress_bar.css('width', push_progress + '%');
                push_progress_status.text('Validating invoice data...');
                push_progress_details.text('Checking invoice requirements for portal sync...');
            }, 300);
            
            // Step 2: Transformation
            setTimeout(() => {
                push_progress = 50;
                push_progress_bar.css('width', push_progress + '%');
                push_progress_status.text('Transforming data...');
                push_progress_details.text('Converting invoice to portal format...');
            }, 600);
            
            // Step 3: Database connection
            setTimeout(() => {
                push_progress = 80;
                push_progress_bar.css('width', push_progress + '%');
                push_progress_status.text('Connecting to portal...');
                push_progress_details.text('Establishing secure database connection...');
            }, 900);
            
            frappe.call({
                method: 'o2o_erpnext.sync.erpnext_to_external_updated.push_invoice_to_procureuat',
                args: {
                    invoice_name: invoice_name
                },
                callback: function(r) {
                    // Complete progress
                    push_progress = 100;
                    push_progress_bar.css('width', push_progress + '%');
                    push_progress_status.text('Push Complete!');
                    push_progress_details.text('Successfully pushed invoice to portal');
                    
                    setTimeout(() => {
                        push_progress_dialog.hide();
                        
                        if (r.message && r.message.success) {
                            // Show success with details
                            let success_message = `
                                <div class="push-success-details">
                                    <h5>✅ Invoice Successfully Pushed!</h5>
                                    <p><strong>Invoice:</strong> ${invoice_name}</p>
                                    <p><strong>Portal Record ID:</strong> ${r.message.portal_record_id || 'Generated'}</p>
                                    <p><strong>Status:</strong> ${r.message.portal_status || 'Active'}</p>
                                    <p><strong>Synced At:</strong> ${new Date().toLocaleString()}</p>
                                    ${r.message.notes ? `<p><strong>Notes:</strong> ${r.message.notes}</p>` : ''}
                                </div>
                            `;
                            
                            frappe.msgprint({
                                title: __('Push Successful'),
                                message: success_message,
                                indicator: 'green'
                            });
                            
                            frappe.show_alert({
                                message: __('Invoice "{0}" pushed to portal successfully!', [invoice_name]),
                                indicator: 'green'
                            }, 5);
                            
                            // Refresh the list to show updated sync status
                            if (cur_list && cur_list.refresh) {
                                cur_list.refresh();
                            }
                        } else {
                            frappe.msgprint({
                                title: __('Push Failed'),
                                message: r.message ? r.message.message : __('Unknown error occurred while pushing invoice'),
                                indicator: 'red'
                            });
                        }
                    }, 1000);
                },
                error: function(err) {
                    push_progress_dialog.hide();
                    frappe.msgprint({
                        title: __('Push Error'),
                        message: __('Network error occurred while pushing invoice to portal'),
                        indicator: 'red'
                    });
                    console.error('Push error:', err);
                }
            });
        }
    );
};

function sync_to_procureuat() {
    window.sync_to_procureuat();
}

window.test_procureuat_connection = function() {
    console.log("🔌 Testing connection...");
    
    frappe.show_alert({message: __('Testing connection...'), indicator: 'blue'});
    
    frappe.call({
        method: 'o2o_erpnext.api.php_portal_invoices.test_portal_connection',
        callback: function(r) {
            if (r.message && r.message.success) {
                frappe.msgprint({
                    title: __('Connection Successful'),
                    message: __('Successfully connected to ProcureUAT database.<br><br>Statistics:<br>• Purchase Requisitions: {0}<br>• Purchase Order Items: {1}<br>• Active Vendors: {2}', 
                              [r.message.statistics.purchase_requisitions, 
                               r.message.statistics.purchase_order_items, 
                               r.message.statistics.active_vendors]),
                    indicator: 'green'
                });
            } else {
                frappe.msgprint({
                    title: __('Connection Failed'),
                    message: r.message ? r.message.message : __('Could not connect'),
                    indicator: 'red'
                });
            }
        },
        error: function(err) {
            frappe.msgprint({
                title: __('Connection Error'),
                message: __('Network error while testing connection'),
                indicator: 'red'
            });
        }
    });
};

function test_procureuat_connection() {
    window.test_procureuat_connection();
}

window.test_purchase_requisitions = function() {
    console.log("🧪 Testing purchase requisitions connection...");
    
    frappe.show_alert({message: __('Testing purchase requisitions...'), indicator: 'blue'});
    
    frappe.call({
        method: 'o2o_erpnext.api.php_portal_invoices.test_purchase_requisitions_connection',
        callback: function(r) {
            if (r.message && r.message.success) {
                // Show detailed results
                let html = `
                    <div class="test-results">
                        <h5>✅ Connection Successful!</h5>
                        <p><strong>Message:</strong> ${r.message.message}</p>
                        
                        <h6>Sample Data (Latest 5 records):</h6>
                        <div class="table-responsive" style="max-height: 300px;">
                            <table class="table table-striped table-sm">
                                <thead>
                                    <tr>
                                        <th>ID</th>
                                        <th>Invoice Number</th>
                                        <th>Order Code</th>
                                        <th>Entity</th>
                                        <th>Status</th>
                                        <th>Invoice Generated</th>
                                    </tr>
                                </thead>
                                <tbody>
                `;
                
                if (r.message.sample_data && r.message.sample_data.length > 0) {
                    r.message.sample_data.forEach(record => {
                        html += `
                            <tr>
                                <td>${record.id}</td>
                                <td>${record.invoice_number}</td>
                                <td>${record.order_code}</td>
                                <td>${record.entity}</td>
                                <td><span class="badge badge-${record.status === 'active' ? 'success' : 'secondary'}">${record.status}</span></td>
                                <td>${record.invoice_generated == 1 ? '✅' : '❌'}</td>
                            </tr>
                        `;
                    });
                } else {
                    html += '<tr><td colspan="6">No sample data found</td></tr>';
                }
                
                html += `
                                </tbody>
                            </table>
                        </div>
                        
                        <h6>Field Information:</h6>
                        <ul>
                            <li><strong>invoice_number:</strong> ${r.message.field_info.invoice_number_usage}</li>
                            <li><strong>order_code:</strong> ${r.message.field_info.order_code_usage}</li>
                            <li><strong>entity:</strong> ${r.message.field_info.entity}</li>
                            <li><strong>subentity_id:</strong> ${r.message.field_info.subentity_id}</li>
                        </ul>
                    </div>
                `;
                
                frappe.msgprint({
                    title: __('Purchase Requisitions Test Results'),
                    message: html,
                    indicator: 'green'
                });
                
                frappe.show_alert({
                    message: __('Purchase Requisitions test completed successfully!'),
                    indicator: 'green'
                }, 3);
            } else {
                frappe.msgprint({
                    title: __('Test Failed'),
                    message: r.message ? r.message.message : __('Unknown error occurred'),
                    indicator: 'red'
                });
            }
        },
        error: function(err) {
            frappe.msgprint({
                title: __('Network Error'),
                message: __('Failed to test purchase requisitions connection'),
                indicator: 'red'
            });
        }
    });
};

function test_purchase_requisitions() {
    window.test_purchase_requisitions();
}

// ========================================
// PORTAL INVOICES DIALOG
// ========================================

function show_portal_invoices_dialog(invoices, statistics) {
    console.log("📋 Showing advanced portal invoices dialog with", invoices.length, "invoices");
    
    // Sort invoices: AGO2O 25-26 first, then AGO2O 24-25, then others by date desc
    const sorted_invoices = invoices.sort((a, b) => {
        // Check if invoice has AGO2O pattern
        const a_ago2o_current = a.portal_invoice_number && a.portal_invoice_number.includes('AGO2O/25-26');
        const b_ago2o_current = b.portal_invoice_number && b.portal_invoice_number.includes('AGO2O/25-26');
        const a_ago2o_prev = a.portal_invoice_number && a.portal_invoice_number.includes('AGO2O/24-25');
        const b_ago2o_prev = b.portal_invoice_number && b.portal_invoice_number.includes('AGO2O/24-25');
        const a_ago2o_any = a.portal_invoice_number && a.portal_invoice_number.includes('AGO2O');
        const b_ago2o_any = b.portal_invoice_number && b.portal_invoice_number.includes('AGO2O');
        
        // Priority 1: AGO2O 25-26 (current FY) at top
        if (a_ago2o_current && !b_ago2o_current) return -1;
        if (!a_ago2o_current && b_ago2o_current) return 1;
        
        // Priority 2: AGO2O 24-25 (previous FY) 
        if (a_ago2o_prev && !b_ago2o_prev) return -1;
        if (!a_ago2o_prev && b_ago2o_prev) return 1;
        
        // Priority 3: Other AGO2O invoices
        if (a_ago2o_any && !b_ago2o_any) return -1;
        if (!a_ago2o_any && b_ago2o_any) return 1;
        
        // Within same category, sort by date (newest first)
        const a_date = new Date(a.created_date || a.updated_at || '1970-01-01');
        const b_date = new Date(b.created_date || b.updated_at || '1970-01-01');
        return b_date - a_date;
    });
    
    console.log("📊 Sorted invoices by priority and date");
    
    // Create enhanced dialog with all advanced features
    let dialog = new frappe.ui.Dialog({
        title: __('🚀 Advanced Portal Invoices Manager ({0} found)', [sorted_invoices.length]),
        size: 'extra-large',
        fields: [
            {
                fieldtype: 'HTML',
                fieldname: 'invoices_html',
                options: generate_advanced_invoices_html(sorted_invoices, statistics)
            }
        ]
    });
    
    dialog.show();
    
    // Initialize advanced functionality after dialog renders
    setTimeout(() => {
        initialize_advanced_dialog_features(dialog);
    }, 200);
}

function generate_advanced_invoices_html(invoices, statistics) {
    // Calculate enhanced statistics
    const total_amount = invoices.reduce((sum, inv) => sum + (parseFloat(inv.total_amount) || 0), 0);
    const current_fy_count = invoices.filter(inv => inv.invoice_number && inv.invoice_number.includes('25-26')).length;
    const unique_customers = new Set(invoices.map(inv => inv.customer_name)).size;
    
    let html = `
        <div class="advanced-portal-container">
            <!-- Enhanced Statistics Dashboard -->
            <div class="stats-dashboard" style="margin-bottom: 25px;">
                <div class="row">
                    <div class="col-md-3 col-sm-6">
                        <div class="stat-card total-invoices">
                            <div class="stat-icon">📊</div>
                            <div class="stat-content">
                                <h3>${invoices.length}</h3>
                                <p>Total Invoices</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3 col-sm-6">
                        <div class="stat-card total-value">
                            <div class="stat-icon">💰</div>
                            <div class="stat-content">
                                <h3>₹${total_amount.toLocaleString('en-IN')}</h3>
                                <p>Total Value</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3 col-sm-6">
                        <div class="stat-card current-fy">
                            <div class="stat-icon">📅</div>
                            <div class="stat-content">
                                <h3>${current_fy_count}</h3>
                                <p>Current FY (25-26)</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3 col-sm-6">
                        <div class="stat-card unique-customers">
                            <div class="stat-icon">�</div>
                            <div class="stat-content">
                                <h3>${unique_customers}</h3>
                                <p>Unique Customers</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Advanced Filtering Controls -->
            <div class="filter-controls" style="margin-bottom: 20px;">
                <div class="row">
                    <div class="col-md-3">
                        <div class="filter-group">
                            <label>🔍 Quick Filter:</label>
                            <select class="form-control" id="quick-filter">
                                <option value="all">All Invoices</option>
                                <option value="current-fy">Current FY (25-26)</option>
                                <option value="last-fy">Last FY (24-25)</option>
                            </select>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="filter-group">
                            <label>📊 Status Filter:</label>
                            <select class="form-control" id="status-filter">
                                <option value="all">All Status</option>
                                <option value="active">Active</option>
                                <option value="pending">Pending</option>
                                <option value="cancelled">Cancelled</option>
                            </select>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="filter-group">
                            <label>💰 Amount Range:</label>
                            <select class="form-control" id="amount-filter">
                                <option value="all">All Amounts</option>
                                <option value="low">< ₹10,000</option>
                                <option value="medium">₹10,000 - ₹50,000</option>
                                <option value="high">> ₹50,000</option>
                            </select>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="filter-group">
                            <label>🔎 Search:</label>
                            <input type="text" class="form-control" id="search-input" placeholder="Invoice, customer, order...">
                        </div>
                    </div>
                </div>
                <div class="row" style="margin-top: 15px;">
                    <div class="col-md-12">
                        <div class="bulk-actions">
                            <label>🚀 Bulk Actions:</label>
                            <div class="btn-group" style="width: 100%;">
                                <button class="btn btn-primary btn-sm" id="select-all-btn">☑️ Select All</button>
                                <button class="btn btn-secondary btn-sm" id="clear-selection-btn">❌ Clear Selection</button>
                                <button class="btn btn-success btn-sm" id="import-selected-btn" disabled>⬇️ Import Selected (<span id="selection-count">0</span>)</button>
                                <button class="btn btn-info btn-sm" id="filter-selected-btn">🔍 Show Selected Only</button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Enhanced Invoice Table -->
            <div class="table-container">
                <div class="table-responsive" style="max-height: 500px; overflow-y: auto;">
                    <table class="table table-striped table-hover" id="invoices-table">
                        <thead class="table-dark" style="position: sticky; top: 0; z-index: 10;">
                            <tr>
                                <th width="40"><input type="checkbox" id="select-all-checkbox"></th>
                                <th width="150">Invoice Number</th>
                                <th width="200">Customer & Entity Details</th>
                                <th width="150">Logistics Info</th>
                                <th width="100">Amount</th>
                                <th width="100">Date</th>
                                <th width="60">Status</th>
                                <th width="120">Actions</th>
                            </tr>
                        </thead>
                        <tbody id="invoices-tbody">
                            ${generate_invoice_rows(invoices)}
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Selection Summary -->
            <div class="selection-summary" style="margin-top: 15px; padding: 10px; background: #f8f9fa; border-radius: 5px; display: none;">
                <strong>Selection Summary:</strong> 
                <span id="selected-count">0</span> invoices selected | 
                <span id="selected-amount">₹0</span> total value
            </div>
        </div>

        <style>
        .advanced-portal-container {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }
        
        .stats-dashboard .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            transition: transform 0.2s ease;
        }
        
        .stats-dashboard .stat-card:hover {
            transform: translateY(-2px);
        }
        
        .stats-dashboard .total-invoices { background: linear-gradient(135deg, #3498db, #2980b9); }
        .stats-dashboard .total-value { background: linear-gradient(135deg, #27ae60, #229954); }
        .stats-dashboard .current-fy { background: linear-gradient(135deg, #f39c12, #e67e22); }
        .stats-dashboard .unique-customers { background: linear-gradient(135deg, #9b59b6, #8e44ad); }
        
        .stat-icon {
            font-size: 2.5em;
            margin-right: 15px;
            opacity: 0.9;
        }
        
        .stat-content h3 {
            margin: 0;
            font-size: 1.8em;
            font-weight: bold;
        }
        
        .stat-content p {
            margin: 0;
            font-size: 0.9em;
            opacity: 0.9;
        }
        
        .filter-controls {
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .filter-group label {
            font-weight: 600;
            margin-bottom: 5px;
            display: block;
        }
        
        .table-container {
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        .table th {
            background: #2c3e50 !important;
            color: white !important;
            border: none !important;
            font-weight: 600;
            font-size: 0.9em;
        }
        
        .table td {
            vertical-align: middle;
            border-color: #ecf0f1;
            font-size: 0.9em;
        }
        
        .table tbody tr:hover {
            background-color: #f8f9fa;
        }
        
        .status-badge {
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 0.8em;
            font-weight: 500;
        }
        
        .status-active { background: #d4edda; color: #155724; }
        .status-pending { background: #fff3cd; color: #856404; }
        .status-cancelled { background: #f8d7da; color: #721c24; }
        
        .action-buttons .btn {
            margin: 1px;
            font-size: 0.8em;
        }
        
        .selection-summary {
            border: 1px solid #dee2e6;
            animation: slideDown 0.3s ease;
        }
        
        @keyframes slideDown {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .highlight-row {
            background-color: #e3f2fd !important;
            animation: highlight 1s ease-in-out;
        }
        
        @keyframes highlight {
            0% { background-color: #fff3e0; }
            50% { background-color: #ffcc80; }
            100% { background-color: #e3f2fd; }
        }
        </style>
    `;
    
    return html;
}

function generate_invoice_rows(invoices) {
    return invoices.map(invoice => {
        const amount = parseFloat(invoice.total_amount) || 0;
        const amount_color = amount > 50000 ? '#e74c3c' : amount > 10000 ? '#f39c12' : '#27ae60';
        const formatted_date = invoice.created_date ? new Date(invoice.created_date).toLocaleDateString('en-IN') : 'N/A';
        
        let status_class = 'status-active';
        let status_text = invoice.status || 'active';
        if (status_text.toLowerCase().includes('pending')) status_class = 'status-pending';
        if (status_text.toLowerCase().includes('cancel')) status_class = 'status-cancelled';
        
        // Proper customer-vendor display based on invoice structure
        const customer_display = invoice.customer_name || invoice.entity_code || 'N/A';
        const delivery_to = invoice.delivery_to || invoice.subentity_code || '';
        const vendor_display = invoice.vendor_name || 'AGO2O STORES LLP';
        
        // Prioritize portal_invoice_number over invoice_number for display
        const display_invoice_number = invoice.portal_invoice_number || invoice.invoice_number;
        const has_portal_number = !!invoice.portal_invoice_number;
        
        // Detect AGO2O and FY patterns from both fields
        const is_ago2o = (invoice.invoice_number && invoice.invoice_number.includes('AGO2O')) ||
                         (invoice.portal_invoice_number && invoice.portal_invoice_number.includes('AGO2O'));
        const is_current_fy = (invoice.invoice_number && invoice.invoice_number.includes('25-26')) ||
                             (invoice.portal_invoice_number && invoice.portal_invoice_number.includes('25-26'));
        const is_last_fy = (invoice.invoice_number && invoice.invoice_number.includes('24-25')) ||
                          (invoice.portal_invoice_number && invoice.portal_invoice_number.includes('24-25'));
        
        return `
            <tr data-invoice-id="${invoice.invoice_id}" 
                data-invoice-number="${display_invoice_number}" 
                data-customer="${customer_display}"
                data-status="${status_text.toLowerCase()}"
                data-amount="${amount}"
                data-fy="${is_current_fy ? 'current' : is_last_fy ? 'last' : 'other'}">
                <td><input type="checkbox" class="invoice-checkbox" data-amount="${amount}"></td>
                <td><strong class="text-primary">${invoice.invoice_id}</strong></td>
                <td>
                    <span class="invoice-number" style="font-weight: bold; color: ${has_portal_number ? '#2c3e50' : '#666'};">${display_invoice_number}</span>
                    ${!has_portal_number && invoice.invoice_number ? `<br><small style="color: #999;">Internal: ${invoice.invoice_number}</small>` : ''}
                    <div style="margin-top: 4px;">
                        ${is_ago2o ? '<span class="badge badge-primary">AGO2O</span>' : ''}
                        ${is_current_fy ? '<span class="badge badge-success">25-26</span>' : ''}
                        ${is_last_fy ? '<span class="badge badge-warning">24-25</span>' : ''}
                    </div>
                </td>
                <td class="customer-info">
                    <div class="customer-name"><strong>${customer_display}</strong></div>
                    ${delivery_to ? `<small class="text-muted">Ship to: ${delivery_to}</small>` : ''}
                    <div class="vendor-info" style="font-size: 11px; color: #666;">
                        Vendor: ${vendor_display}
                    </div>
                </td>
                <td><span class="badge badge-info">${invoice.total_items || 0}</span></td>
                <td><strong style="color: ${amount_color};">₹${amount.toLocaleString('en-IN')}</strong></td>
                <td>${formatted_date}</td>
                <td><span class="status-badge ${status_class}">${status_text}</span></td>
                <td class="action-buttons">
                    <button class="btn btn-success btn-sm import-single-btn" data-invoice-id="${invoice.invoice_id}" title="Import This Invoice">
                        <i class="fa fa-download"></i>
                    </button>
                    <button class="btn btn-info btn-sm preview-btn" data-invoice-id="${invoice.invoice_id}" title="Preview Invoice">
                        <i class="fa fa-eye"></i>
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

function initialize_advanced_dialog_features(dialog) {
    const $wrapper = dialog.$wrapper;
    
    // Initialize all filter elements with debug logging
    const $quickFilter = $wrapper.find('#quick-filter');
    const $statusFilter = $wrapper.find('#status-filter');
    const $amountFilter = $wrapper.find('#amount-filter');
    const $searchInput = $wrapper.find('#search-input');
    const $selectAllCheckbox = $wrapper.find('#select-all-checkbox');
    const $selectAllBtn = $wrapper.find('#select-all-btn');
    const $clearSelectionBtn = $wrapper.find('#clear-selection-btn');
    const $importSelectedBtn = $wrapper.find('#import-selected-btn');
    const $filterSelectedBtn = $wrapper.find('#filter-selected-btn');
    const $selectionSummary = $wrapper.find('.selection-summary');
    
    // Debug log filter elements
    console.log('🔧 Filter elements found:', {
        quickFilter: $quickFilter.length,
        statusFilter: $statusFilter.length, 
        amountFilter: $amountFilter.length,
        searchInput: $searchInput.length
    });
    
    let showSelectedOnly = false;
    
    // Optimized apply all filters function with performance improvements
    function applyAllFilters() {
        console.log('🔄 applyAllFilters called');
        
        // Show subtle loading indicator for large datasets
        let $loadingIndicator = $wrapper.find('.filter-loading');
        if ($loadingIndicator.length === 0) {
            $loadingIndicator = $('<span class="filter-loading" style="font-size: 11px; color: #999; margin-left: 10px;">🔄 Filtering...</span>');
            $wrapper.find('.filter-controls').append($loadingIndicator);
        }
        $loadingIndicator.show();
        
        // Use setTimeout to allow UI to update before heavy filtering operation
        setTimeout(() => {
            // Cache filter values to avoid repeated DOM queries
            const quickFilterValue = $quickFilter.val();
            const statusFilterValue = $statusFilter.val();
            const amountFilterValue = $amountFilter.val();
            const searchValue = $searchInput.val().toLowerCase();
            
            console.log('Filter values:', {
                quick: quickFilterValue,
                status: statusFilterValue, 
                amount: amountFilterValue,
                search: searchValue,
                selectedOnly: showSelectedOnly
            });
            
            // Performance optimization: batch DOM operations
            const $rows = $wrapper.find('#invoices-tbody tr');
            let visibleCount = 0;
            
            console.log('Total rows found:', $rows.length);
        
        $rows.each(function() {
            const $row = $(this);
            const invoiceNumber = $row.data('invoice-number') || '';
            const customer = $row.data('customer') || '';
            const status = $row.data('status') || '';
            const amount = parseFloat($row.data('amount')) || 0;
            const fy = $row.data('fy') || '';
            const isSelected = $row.find('.invoice-checkbox').is(':checked');
            
            let showRow = true;
            
            // Quick filter logic
            if (quickFilterValue !== 'all') {
                switch(quickFilterValue) {
                    case 'current-fy':
                        showRow = showRow && fy === 'current';
                        break;
                    case 'last-fy':
                        showRow = showRow && fy === 'last';
                        break;
                }
            }
            
            // Status filter logic
            if (statusFilterValue !== 'all') {
                showRow = showRow && status.includes(statusFilterValue);
            }
            
            // Amount filter logic
            if (amountFilterValue !== 'all') {
                switch(amountFilterValue) {
                    case 'low':
                        showRow = showRow && amount < 10000;
                        break;
                    case 'medium':
                        showRow = showRow && amount >= 10000 && amount <= 50000;
                        break;
                    case 'high':
                        showRow = showRow && amount > 50000;
                        break;
                }
            }
            
            // Search filter logic - optimized with cached lowercase value
            if (searchValue) {
                const searchableText = (invoiceNumber + ' ' + customer).toLowerCase();
                showRow = showRow && searchableText.includes(searchValue);
            }
            
            // Show selected only filter
            if (showSelectedOnly) {
                showRow = showRow && isSelected;
            }
            
            // Batch DOM manipulation for better performance
            if (showRow) {
                $row.show();
                visibleCount++;
            } else {
                $row.hide();
            }
        });
        
        // Update filter result count for user feedback
        updateFilterResultsCount(visibleCount, $rows.length);
        
        console.log('✅ Filtering complete:', { visible: visibleCount, total: $rows.length });
        
        updateSelectionSummary();
        
        // Hide loading indicator
        $loadingIndicator.hide();
        }, 1); // 1ms timeout to allow UI update
    }
    
    // Function to update filter results count with user feedback
    function updateFilterResultsCount(visibleCount, totalCount) {
        let $resultCounter = $wrapper.find('.filter-results-counter');
        if ($resultCounter.length === 0) {
            // Create counter if it doesn't exist
            $resultCounter = $('<div class="filter-results-counter" style="font-size: 12px; color: #666; margin-top: 5px;"></div>');
            $wrapper.find('.filter-controls').append($resultCounter);
        }
        
        if (visibleCount === totalCount) {
            $resultCounter.text(`Showing all ${totalCount} invoices`);
        } else {
            $resultCounter.text(`Showing ${visibleCount} of ${totalCount} invoices`);
        }
    }
    
    // Enhanced responsive filter event handlers with IMMEDIATE response
    // Immediate response for dropdowns - trigger on change, input, click events
    $quickFilter.on('change input click', function() {
        console.log('Quick filter changed:', $(this).val());
        applyAllFilters();
    });
    
    $statusFilter.on('change input click', function() {
        console.log('Status filter changed:', $(this).val());
        applyAllFilters();
    });
    
    $amountFilter.on('change input click', function() {
        console.log('Amount filter changed:', $(this).val());
        applyAllFilters();
    });
    
    // Real-time search with minimal debouncing
    let searchTimeout;
    $searchInput.on('input keyup paste', function() {
        console.log('Search input changed:', $(this).val());
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            applyAllFilters();
        }, 100); // Reduced to 100ms for faster response
    });
    
    // Select all functionality
    $selectAllCheckbox.on('change', function() {
        const isChecked = $(this).is(':checked');
        $wrapper.find('.invoice-checkbox:visible').prop('checked', isChecked);
        updateSelectionSummary();
    });
    
    $selectAllBtn.on('click', function() {
        $selectAllCheckbox.prop('checked', true).trigger('change');
    });
    
    // Clear selection functionality
    $clearSelectionBtn.on('click', function() {
        $wrapper.find('.invoice-checkbox').prop('checked', false);
        $selectAllCheckbox.prop('checked', false);
        updateSelectionSummary();
    });
    
    // Show selected only toggle
    $filterSelectedBtn.on('click', function() {
        showSelectedOnly = !showSelectedOnly;
        if (showSelectedOnly) {
            $(this).text('📄 Show All').removeClass('btn-info').addClass('btn-warning');
        } else {
            $(this).text('🔍 Show Selected Only').removeClass('btn-warning').addClass('btn-info');
        }
        applyAllFilters();
    });
    
    // Individual checkbox handling
    $wrapper.on('change', '.invoice-checkbox', function() {
        updateSelectionSummary();
        
        // Update select all checkbox state
        const totalVisible = $wrapper.find('.invoice-checkbox:visible').length;
        const checkedVisible = $wrapper.find('.invoice-checkbox:visible:checked').length;
        $selectAllCheckbox.prop('checked', totalVisible > 0 && checkedVisible === totalVisible);
    });
    
    // Import selected functionality
    $importSelectedBtn.on('click', function() {
        const selectedIds = [];
        $wrapper.find('.invoice-checkbox:checked').each(function() {
            const $row = $(this).closest('tr');
            selectedIds.push($row.data('invoice-id'));
        });
        
        if (selectedIds.length > 0) {
            import_selected_invoices(selectedIds);
        }
    });
    
    // Single import buttons
    $wrapper.on('click', '.import-single-btn', function() {
        const invoiceId = $(this).data('invoice-id');
        import_single_portal_invoice(invoiceId);
    });
    
    // Preview buttons
    $wrapper.on('click', '.preview-btn', function() {
        const invoiceId = $(this).data('invoice-id');
        preview_invoice_details(invoiceId);
    });
    
    function updateSelectionSummary() {
        const $checkedBoxes = $wrapper.find('.invoice-checkbox:checked');
        const count = $checkedBoxes.length;
        const totalAmount = Array.from($checkedBoxes).reduce((sum, checkbox) => {
            return sum + (parseFloat($(checkbox).data('amount')) || 0);
        }, 0);
        
        $wrapper.find('#selection-count').text(count);
        $wrapper.find('#selected-count').text(count);
        $wrapper.find('#selected-amount').text('₹' + totalAmount.toLocaleString('en-IN'));
        
        $importSelectedBtn.prop('disabled', count === 0);
        
        if (count > 0) {
            $selectionSummary.show();
        } else {
            $selectionSummary.hide();
        }
    }
    
    // Initial filter test and application
    setTimeout(() => {
        console.log('🚀 Running initial filter test...');
        applyAllFilters();
    }, 500);
}

// Helper functions for dialog actions
function import_selected_invoices(selectedIds) {
    if (selectedIds.length === 0) {
        frappe.show_alert({message: __('No invoices selected'), indicator: 'orange'});
        return;
    }
    
    frappe.confirm(
        __('Import {0} selected invoice(s)?', [selectedIds.length]),
        function() {
            frappe.show_alert({message: __('Importing {0} invoices...', [selectedIds.length]), indicator: 'blue'});
            
            frappe.call({
                method: 'o2o_erpnext.api.php_portal_invoices.import_multiple_invoices',
                args: {
                    invoice_ids: selectedIds
                },
                callback: function(r) {
                    if (r.message && r.message.success) {
                        frappe.show_alert({
                            message: __('Successfully imported {0} invoice(s)', [selectedIds.length]),
                            indicator: 'green'
                        }, 5);
                        
                        if (cur_list) cur_list.refresh();
                        if (cur_dialog) cur_dialog.hide();
                    } else {
                        frappe.msgprint({
                            title: __('Import Failed'),
                            message: r.message ? r.message.message : __('Failed to import selected invoices'),
                            indicator: 'red'
                        });
                    }
                },
                error: function(err) {
                    frappe.msgprint({
                        title: __('Import Error'),
                        message: __('Failed to import invoices from portal'),
                        indicator: 'red'
                    });
                }
            });
        }
    );
}

function preview_invoice_details(invoiceId) {
    frappe.call({
        method: 'o2o_erpnext.api.php_portal_invoices.get_invoice_details',
        args: {
            invoice_id: invoiceId
        },
        callback: function(r) {
            if (r.message && r.message.success) {
                const invoice = r.message.invoice;
                
                let html = `
                    <div class="invoice-preview">
                        <table class="table table-bordered">
                            <tr><th>Invoice ID:</th><td>${invoice.invoice_id}</td></tr>
                            <tr><th>Invoice Number:</th><td>${invoice.invoice_number || 'Not Generated'}</td></tr>
                            <tr><th>Customer:</th><td>${invoice.customer_name || 'N/A'}</td></tr>
                            <tr><th>Total Amount:</th><td>₹${Number(invoice.total_amount || 0).toLocaleString('en-IN')}</td></tr>
                            <tr><th>Status:</th><td>${invoice.status || 'Active'}</td></tr>
                            <tr><th>Created Date:</th><td>${invoice.created_date || 'N/A'}</td></tr>
                            <tr><th>Total Items:</th><td>${invoice.total_items || 0}</td></tr>
                        </table>
                    </div>
                `;
                
                frappe.msgprint({
                    title: __('Invoice Preview - {0}', [invoice.invoice_id]),
                    message: html,
                    indicator: 'blue'
                });
            } else {
                frappe.msgprint({
                    title: __('Preview Failed'),
                    message: __('Could not load invoice details'),
                    indicator: 'red'
                });
            }
        }
    });
}

function generate_invoices_table_html(invoices, statistics) {
    const total_amount = invoices.reduce((sum, inv) => sum + (inv.total_amount || 0), 0);
    
    let html = `
        <div class="portal-invoices-container">
            <!-- Summary Cards -->
            <div class="row" style="margin-bottom: 20px;">
                <div class="col-sm-3">
                    <div class="card text-center" style="background: linear-gradient(135deg, #3498db, #2980b9); color: white;">
                        <div class="card-body">
                            <h4>${invoices.length}</h4>
                            <small>Total Invoices</small>
                        </div>
                    </div>
                </div>
                <div class="col-sm-3">
                    <div class="card text-center" style="background: linear-gradient(135deg, #27ae60, #229954); color: white;">
                        <div class="card-body">
                            <h4>₹${total_amount.toLocaleString('en-IN')}</h4>
                            <small>Total Value</small>
                        </div>
                    </div>
                </div>
                <div class="col-sm-3">
                    <div class="card text-center" style="background: linear-gradient(135deg, #e74c3c, #c0392b); color: white;">
                        <div class="card-body">
                            <h4>${new Set(invoices.map(inv => inv.customer_name)).size}</h4>
                            <small>Customers</small>
                        </div>
                    </div>
                </div>
                <div class="col-sm-3">
                    <div class="card text-center" style="background: linear-gradient(135deg, #f39c12, #e67e22); color: white;">
                        <div class="card-body">
                            <h4>${Math.round(total_amount / invoices.length).toLocaleString('en-IN')}</h4>
                            <small>Avg Amount</small>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Invoices Table -->
            <div class="table-responsive" style="max-height: 500px; overflow-y: auto;">
                <table class="table table-striped table-hover">
                    <thead class="bg-dark text-white" style="position: sticky; top: 0; z-index: 10;">
                        <tr>
                            <th>ID</th>
                            <th>Invoice Number</th>
                            <th>Customer</th>
                            <th>Items</th>
                            <th>Amount</th>
                            <th>Date</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody>
    `;
    
    invoices.forEach(invoice => {
        const amount_color = invoice.total_amount > 50000 ? '#e74c3c' : '#27ae60';
        html += `
            <tr>
                <td><strong>${invoice.invoice_id}</strong></td>
                <td><span class="text-primary">${invoice.invoice_number}</span></td>
                <td>${invoice.customer_name}</td>
                <td><span class="badge badge-info">${invoice.total_items || 0}</span></td>
                <td style="color: ${amount_color}; font-weight: bold;">₹${Number(invoice.total_amount || 0).toLocaleString('en-IN')}</td>
                <td>${invoice.created_date ? invoice.created_date.split(' ')[0] : 'N/A'}</td>
                <td>
                    <button class="btn btn-sm btn-success import-invoice-btn" data-invoice-id="${invoice.invoice_id}" title="Import This Invoice">
                        <i class="fa fa-download"></i> Import
                    </button>
                </td>
            </tr>
        `;
    });
    
    html += `
                    </tbody>
                </table>
            </div>
        </div>
        
        <style>
        .portal-invoices-container .card {
            border-radius: 8px;
            margin: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .portal-invoices-container .table th {
            border: none;
            font-weight: 600;
        }
        .portal-invoices-container .table td {
            border-color: #eee;
            vertical-align: middle;
        }
        .portal-invoices-container .table tr:hover {
            background-color: #f8f9fa;
        }
        </style>
    `;
    
    return html;
}

function import_single_portal_invoice(invoice_id) {
    frappe.confirm(
        __('Import this invoice into Purchase Invoice?'),
        function() {
            frappe.show_alert({message: __('Importing invoice...'), indicator: 'blue'});
            
            frappe.call({
                method: 'o2o_erpnext.api.php_portal_invoices.import_multiple_invoices',
                args: {
                    invoice_ids: [invoice_id]
                },
                callback: function(r) {
                    if (r.message && r.message.success) {
                        frappe.show_alert({
                            message: __('Invoice imported successfully'),
                            indicator: 'green'
                        }, 3);
                        
                        if (cur_list) cur_list.refresh();
                    } else {
                        frappe.msgprint({
                            title: __('Import Failed'),
                            message: r.message ? r.message.message : __('Failed to import invoice'),
                            indicator: 'red'
                        });
                    }
                },
                error: function(err) {
                    frappe.msgprint({
                        title: __('Import Error'),
                        message: __('Failed to import invoice from portal'),
                        indicator: 'red'
                    });
                }
            });
        }
    );
}

// Advanced Portal Dashboard Function
window.show_advanced_portal_dashboard = function() {
    console.log("🚀 Loading Advanced Portal Dashboard...");
    
    // Create and show progress dialog
    let progress_dialog = new frappe.ui.Dialog({
        title: __('Loading Advanced Portal Dashboard'),
        size: 'small',
        fields: [
            {
                fieldtype: 'HTML',
                fieldname: 'progress_html',
                options: `
                    <div class="progress-container" style="text-align: center; padding: 20px;">
                        <div class="loading-spinner" style="margin-bottom: 15px;">
                            <div class="spinner-border text-primary" role="status" style="width: 3rem; height: 3rem;">
                                <span class="sr-only">Loading...</span>
                            </div>
                        </div>
                        <div class="progress" style="height: 20px; margin-bottom: 15px;">
                            <div class="progress-bar progress-bar-striped progress-bar-animated bg-primary" 
                                 role="progressbar" style="width: 0%" id="portal-progress-bar">
                            </div>
                        </div>
                        <div class="progress-text">
                            <strong id="progress-status">Connecting to Portal Database...</strong>
                        </div>
                        <div class="progress-details" style="margin-top: 10px; font-size: 12px; color: #666;">
                            <span id="progress-details">Loading purchase requisitions with advanced dashboard...</span>
                        </div>
                    </div>
                `
            }
        ]
    });
    
    progress_dialog.show();
    
    // Simulate progress steps
    let progress = 0;
    const progress_bar = progress_dialog.$wrapper.find('#portal-progress-bar');
    const progress_status = progress_dialog.$wrapper.find('#progress-status');
    const progress_details = progress_dialog.$wrapper.find('#progress-details');
    
    // Step 1: Initial connection
    setTimeout(() => {
        progress = 25;
        progress_bar.css('width', progress + '%');
        progress_status.text('Authenticating...');
        progress_details.text('Establishing secure connection with enhanced features...');
    }, 300);
    
    // Step 2: Fetching data
    setTimeout(() => {
        progress = 50;
        progress_bar.css('width', progress + '%');
        progress_status.text('Fetching Invoice Data...');
        progress_details.text('Loading all invoices with customer and vendor details...');
    }, 800);
    
    // Step 3: Processing
    setTimeout(() => {
        progress = 75;
        progress_bar.css('width', progress + '%');
        progress_status.text('Building Dashboard...');
        progress_details.text('Preparing advanced filters and bulk actions...');
    }, 1200);
    
    frappe.call({
        method: 'o2o_erpnext.api.php_portal_invoices.get_recent_purchase_requisitions',
        args: { limit: 500, offset: 0 },
        callback: function(r) {
            // Complete progress
            progress = 100;
            progress_bar.css('width', progress + '%');
            progress_status.text('Complete!');
            progress_details.text('Successfully loaded advanced portal dashboard');
            
            setTimeout(() => {
                progress_dialog.hide();
                
                if (r.message && r.message.status === 'success') {
                    const requisitions = r.message.data || [];
                    const pagination = r.message.pagination || {};
                    
                    // Show success alert briefly
                    frappe.show_alert({
                        message: __('Successfully loaded {0} purchase requisitions', [requisitions.length]),
                        indicator: 'green'
                    }, 2);
                    
                    // Show the enhanced portal dashboard with requisitions data
                    setTimeout(() => {
                        show_enhanced_portal_dashboard(requisitions, pagination);
                    }, 500);
                } else {
                    frappe.msgprint({
                        title: __('Error'),
                        message: r.message ? r.message.message : __('Failed to load purchase requisitions'),
                        indicator: 'red'
                    });
                }
            }, 800);
        },
        error: function(err) {
            progress_dialog.hide();
            frappe.msgprint({
                title: __('Network Error'),
                message: __('Failed to connect to Portal database'),
                indicator: 'red'
            });
        }
    });
};

// Enhanced Portal Dashboard with all advanced features
function show_enhanced_portal_dashboard(invoices, statistics) {
    console.log("🎯 Showing Enhanced Portal Dashboard with", invoices.length, "invoices");
    
    // Sort purchase requisitions by created_at date (latest first)
    const sorted_invoices = invoices.sort((a, b) => {
        // Check if we're dealing with purchase requisitions (have created_at) or portal invoices
        if (a.created_at && b.created_at) {
            // Purchase requisitions sorting - by created_at DESC (latest first)
            const a_date = new Date(a.created_at);
            const b_date = new Date(b.created_at);
            
            if (a_date !== b_date) {
                return b_date - a_date; // Latest first
            }
            
            // If dates are same, sort by ID DESC as tiebreaker
            return (b.id || 0) - (a.id || 0);
        } else {
            // Portal invoices sorting - keep the original AGO2O logic
            const a_ago2o_current = a.portal_invoice_number && a.portal_invoice_number.includes('AGO2O/25-26');
            const b_ago2o_current = b.portal_invoice_number && b.portal_invoice_number.includes('AGO2O/25-26');
            const a_ago2o_prev = a.portal_invoice_number && a.portal_invoice_number.includes('AGO2O/24-25');
            const b_ago2o_prev = b.portal_invoice_number && b.portal_invoice_number.includes('AGO2O/24-25');
            const a_ago2o_any = a.portal_invoice_number && a.portal_invoice_number.includes('AGO2O');
            const b_ago2o_any = b.portal_invoice_number && b.portal_invoice_number.includes('AGO2O');
            
            // Priority 1: AGO2O 25-26 (current FY) at top
            if (a_ago2o_current && !b_ago2o_current) return -1;
            if (!a_ago2o_current && b_ago2o_current) return 1;
            
            // Priority 2: AGO2O 24-25 (previous FY) 
            if (a_ago2o_prev && !b_ago2o_prev) return -1;
            if (!a_ago2o_prev && b_ago2o_prev) return 1;
            
            // Priority 3: Other AGO2O invoices
            if (a_ago2o_any && !b_ago2o_any) return -1;
            if (!a_ago2o_any && b_ago2o_any) return 1;
            
            // Within same category, sort by date (newest first)
            const a_date = new Date(a.created_date || a.updated_at || '1970-01-01');
            const b_date = new Date(b.created_date || b.updated_at || '1970-01-01');
            return b_date - a_date;
        }
    });
    
    console.log("📊 Dashboard sorted by created_at date - latest first, oldest last");
    
    // Create the enhanced dashboard dialog
    let dialog = new frappe.ui.Dialog({
        title: __('🚀 Purchase Requisitions Dashboard ({0} records)', [sorted_invoices.length]),
        size: 'extra-large',
        fields: [
            {
                fieldtype: 'HTML',
                fieldname: 'dashboard_html',
                options: generate_enhanced_dashboard_html(sorted_invoices, statistics)
            }
        ],
        primary_action_label: __('Close Dashboard'),
        primary_action: function() {
            dialog.hide();
        },
        secondary_action_label: __('🔄 Refresh Data'),
        secondary_action: function() {
            dialog.hide();
            show_advanced_portal_dashboard();
        }
    });
    
    dialog.show();
    
    // Initialize all advanced features after dialog is shown
    setTimeout(() => {
        initialize_enhanced_dashboard_features(dialog, sorted_invoices);
    }, 100);
}

function generate_enhanced_dashboard_html(requisitions, statistics) {
    // Update statistics for purchase requisitions using actual available fields
    const with_invoice_count = requisitions.filter(req => req.invoice_number && req.invoice_number.trim()).length;
    const generated_invoices = requisitions.filter(req => req.invoice_generated == 1).length;
    const unique_entities = new Set(requisitions.map(req => req.entity).filter(e => e)).size;
    const active_requisitions = requisitions.filter(req => req.status === 'active').length;
    const approved_count = requisitions.filter(req => req.approved_at).length;
    
    return `
        <div class="enhanced-portal-dashboard">
            <!-- Statistics Dashboard -->
            <div class="statistics-dashboard" style="margin-bottom: 25px;">
                <div class="row">
                    <div class="col-md-3 col-sm-6">
                        <div class="stat-card total">
                            <div class="stat-icon">📊</div>
                            <div class="stat-content">
                                <h3>${requisitions.length}</h3>
                                <p>Total Requisitions</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3 col-sm-6">
                        <div class="stat-card amount">
                            <div class="stat-icon">✅</div>
                            <div class="stat-content">
                                <h3>${approved_count}</h3>
                                <p>Approved Requisitions</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3 col-sm-6">
                        <div class="stat-card generated">
                            <div class="stat-icon">✅</div>
                            <div class="stat-content">
                                <h3>${generated_invoices}</h3>
                                <p>Invoices Generated</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3 col-sm-6">
                        <div class="stat-card entities">
                            <div class="stat-icon">🏢</div>
                            <div class="stat-content">
                                <h3>${unique_entities}</h3>
                                <p>Unique Entities</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Advanced Filtering Controls -->
            <div class="filter-controls" style="margin-bottom: 20px;">
                <div class="row">
                    <div class="col-md-3">
                        <div class="filter-group">
                            <label>🔍 Status Filter:</label>
                            <select class="form-control" id="pattern-filter">
                                <option value="all">All Requisitions (${requisitions.length})</option>
                                <option value="generated">Invoice Generated (${generated_invoices})</option>
                                <option value="with-invoice">With Invoice # (${with_invoice_count})</option>
                                <option value="active">Active Status (${active_requisitions})</option>
                            </select>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="filter-group">
                            <label>🔎 Search:</label>
                            <input type="text" class="form-control" id="search-input" placeholder="Entity, order name, invoice number, challan...">
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="filter-group">
                            <label>💰 Amount Range:</label>
                            <select class="form-control" id="amount-filter">
                                <option value="all">All Amounts</option>
                                <option value="high">Above ₹50,000</option>
                                <option value="medium">₹10,000 - ₹50,000</option>
                                <option value="low">Below ₹10,000</option>
                            </select>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="bulk-actions">
                            <label>🚀 Bulk Actions:</label>
                            <div class="btn-group" style="width: 100%;">
                                <button class="btn btn-primary btn-sm" id="select-all-btn">☑️ All</button>
                                <button class="btn btn-success btn-sm" id="import-selected-btn" disabled>⬇️ Import (<span id="selection-count">0</span>)</button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Quick Action Buttons -->
            <div class="quick-actions" style="margin-bottom: 20px;">
                <div class="btn-group" role="group">
                    <button class="btn btn-outline-primary" id="import-generated-btn">
                        ✅ Import Generated Invoices - ${generated_invoices} requisitions
                    </button>
                    <button class="btn btn-outline-success" id="import-with-invoice-btn">
                        � Import With Invoice Numbers - ${with_invoice_count} requisitions
                    </button>
                    <button class="btn btn-outline-info" id="show-statistics-btn">
                        📊 Detailed Statistics
                    </button>
                    <button class="btn btn-outline-info" id="load-more-btn">
                        📥 Load More Records (+300) | Current: ${requisitions.length}
                    </button>
                    <button class="btn btn-outline-warning" id="refresh-dashboard-btn">
                        🔄 Refresh Dashboard
                    </button>
                </div>
            </div>

            <!-- Selection Summary -->
            <div class="selection-summary" style="margin-bottom: 15px; display: none;">
                <div class="alert alert-info">
                    <strong>📋 Selection Summary:</strong>
                    <span id="selected-count">0</span> invoices selected with total value of 
                    <strong>₹<span id="selected-amount">0</span></strong>
                </div>
            </div>

            <!-- Enhanced Invoice Table -->
            <div class="table-container">
                <div class="table-responsive" style="max-height: 600px; overflow-y: auto;">
                    <table class="table table-striped table-hover" id="invoices-table">
                        <thead class="table-dark" style="position: sticky; top: 0; z-index: 10;">
                            <tr>
                                <th width="40"><input type="checkbox" id="select-all-checkbox"></th>
                                <th width="150">Invoice Number</th>
                                <th width="200">Entity</th>
                                <th width="250">Subentity Names</th>
                                <th width="180">Order Name</th>
                                <th width="140">Challan Number</th>
                                <th width="80">Status</th>
                                <th width="100">Created At</th>
                                <th width="100">Approved At</th>
                                <th width="140">Actions</th>
                            </tr>
                        </thead>
                        <tbody id="requisitions-tbody">
                            ${generate_enhanced_invoice_rows(requisitions)}
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Enhanced Styles -->
            <style>
                .enhanced-portal-dashboard .stat-card {
                    background: white;
                    border-radius: 10px;
                    padding: 20px;
                    margin: 10px 0;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                    display: flex;
                    align-items: center;
                    transition: transform 0.2s;
                }
                .enhanced-portal-dashboard .stat-card:hover {
                    transform: translateY(-2px);
                }
                .enhanced-portal-dashboard .stat-card.total { border-left: 4px solid #3498db; }
                .enhanced-portal-dashboard .stat-card.amount { border-left: 4px solid #27ae60; }
                .enhanced-portal-dashboard .stat-card.ago2o { border-left: 4px solid #e74c3c; }
                .enhanced-portal-dashboard .stat-card.current-fy { border-left: 4px solid #f39c12; }
                
                .enhanced-portal-dashboard .stat-icon {
                    font-size: 2.5em;
                    margin-right: 15px;
                }
                .enhanced-portal-dashboard .stat-content h3 {
                    margin: 0;
                    font-size: 1.8em;
                    font-weight: bold;
                }
                .enhanced-portal-dashboard .stat-content p {
                    margin: 0;
                    color: #666;
                    font-size: 0.9em;
                }
                
                .enhanced-portal-dashboard .filter-group label {
                    font-size: 12px;
                    font-weight: bold;
                    color: #666;
                    margin-bottom: 5px;
                }
                
                .enhanced-portal-dashboard .customer-info {
                    line-height: 1.3;
                }
                .enhanced-portal-dashboard .customer-name {
                    font-weight: bold;
                    color: #2c3e50;
                }
                .enhanced-portal-dashboard .delivery-to {
                    font-size: 11px;
                    color: #7f8c8d;
                }
                .enhanced-portal-dashboard .vendor-info {
                    font-size: 10px;
                    color: #95a5a6;
                    font-style: italic;
                }
                
                .enhanced-portal-dashboard .status-badge {
                    padding: 3px 8px;
                    border-radius: 12px;
                    font-size: 11px;
                    font-weight: bold;
                    text-transform: uppercase;
                }
                .enhanced-portal-dashboard .status-active { background: #d4edda; color: #155724; }
                .enhanced-portal-dashboard .status-pending { background: #fff3cd; color: #856404; }
                .enhanced-portal-dashboard .status-cancelled { background: #f8d7da; color: #721c24; }
                
                .enhanced-portal-dashboard .invoice-number {
                    font-weight: bold;
                    color: #2c3e50;
                }
                
                .enhanced-portal-dashboard .badge {
                    font-size: 9px;
                    margin-left: 5px;
                }
                
                .enhanced-portal-dashboard .action-buttons .btn {
                    margin: 1px;
                    padding: 4px 8px;
                    font-size: 11px;
                }
                
                .enhanced-portal-dashboard .quick-actions {
                    text-align: center;
                }
                .enhanced-portal-dashboard .quick-actions .btn {
                    margin: 0 5px;
                    padding: 8px 15px;
                    font-weight: 500;
                }
            </style>
        </div>
    `;
}

function generate_enhanced_invoice_rows(requisitions) {
    return requisitions.map(req => {
        // Format dates properly
        const created_date = req.created_at ? new Date(req.created_at).toLocaleDateString('en-IN') : 'N/A';
        const approved_date = req.approved_at ? new Date(req.approved_at).toLocaleDateString('en-IN') : 'Not Approved';
        
        // Get the exact fields as requested
        const invoice_number = req.invoice_number || 'Not Generated';
        const entity_name = req.entity_name || `Entity ${req.entity}` || 'N/A';
        const subentity_names = req.subentity_names || `Subentity ${req.subentity_id}` || 'N/A';
        const order_name = req.order_name || 'N/A';
        const challan_number = req.challan_number || 'Not Generated';
        const status = req.status || 'N/A';
        
        let status_class = 'status-active';
        if (status.toLowerCase().includes('pending')) status_class = 'status-pending';
        if (status.toLowerCase().includes('cancel')) status_class = 'status-cancelled';
        
        return `
            <tr data-req-id="${req.id}">
                <td><input type="checkbox" class="requisition-checkbox" data-req-id="${req.id}"></td>
                <td>
                    <div class="invoice-number" style="font-weight: bold; color: #2c3e50;">
                        ${invoice_number}
                    </div>
                    ${req.invoice_generated == 1 ? '<span class="badge badge-success">Generated</span>' : '<span class="badge badge-warning">Pending</span>'}
                </td>
                <td>
                    <div class="entity-name" style="font-weight: bold; color: #2980b9;">
                        ${entity_name}
                    </div>
                    <small class="text-muted">ID: ${req.entity}</small>
                </td>
                <td>
                    <div class="subentity-names" style="color: #27ae60;">
                        ${subentity_names}
                    </div>
                    <small class="text-muted">IDs: ${req.subentity_id}</small>
                </td>
                <td>
                    <div class="order-name" style="font-weight: bold; color: #34495e;">
                        ${order_name}
                    </div>
                </td>
                <td>
                    <div class="challan-number">
                        ${challan_number}
                    </div>
                </td>
                <td>
                    <span class="status-badge ${status_class}">${status}</span>
                </td>
                <td>
                    <div class="created-date">
                        ${created_date}
                    </div>
                </td>
                <td>
                    <div class="approved-date">
                        ${approved_date}
                    </div>
                </td>
                <td class="action-buttons">
                    <button class="btn btn-success btn-sm import-single-btn" data-req-id="${req.id}" title="Import This Requisition">
                        <i class="fa fa-download"></i> Import
                    </button>
                    <button class="btn btn-info btn-sm preview-btn" data-req-id="${req.id}" title="Preview Requisition Details">
                        <i class="fa fa-eye"></i> Preview
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}


function initialize_enhanced_dashboard_features(dialog, invoices) {
    console.log("🔧 Initializing Enhanced Dashboard Features");
    
    let filtered_invoices = [...invoices];
    let selected_invoices = new Set();
    
    // Initialize filters
    $('#pattern-filter').on('change', function() {
        apply_all_filters();
    });
    
    $('#search-input').on('input', function() {
        apply_all_filters();
    });
    
    $('#amount-filter').on('change', function() {
        apply_all_filters();
    });
    
    // Select All functionality
    $('#select-all-checkbox').on('change', function() {
        const isChecked = $(this).is(':checked');
        $('.invoice-checkbox:visible').prop('checked', isChecked).trigger('change');
    });
    
    $('#select-all-btn').on('click', function() {
        $('.invoice-checkbox:visible').prop('checked', true).trigger('change');
    });
    
    // Individual checkbox handling
    $(document).on('change', '.invoice-checkbox', function() {
        const invoice_id = $(this).closest('tr').data('invoice-id');
        const amount = parseFloat($(this).data('amount')) || 0;
        
        if ($(this).is(':checked')) {
            selected_invoices.add({ id: invoice_id, amount: amount });
        } else {
            selected_invoices.delete([...selected_invoices].find(inv => inv.id === invoice_id));
        }
        
        update_selection_summary();
    });
    
    // Import actions
    $('#import-selected-btn').on('click', function() {
        if (selected_invoices.size === 0) {
            frappe.msgprint('Please select at least one invoice to import.');
            return;
        }
        
        const invoice_ids = [...selected_invoices].map(inv => inv.id);
        import_multiple_invoices(invoice_ids);
    });
    
    $('#import-current-fy-btn').on('click', function() {
        const current_fy_invoices = invoices.filter(inv => 
            inv.invoice_number && inv.invoice_number.includes('25-26')
        ).map(inv => inv.invoice_id);
        
        if (current_fy_invoices.length === 0) {
            frappe.msgprint('No current financial year (25-26) invoices found.');
            return;
        }
        
        frappe.confirm(
            `Import all ${current_fy_invoices.length} current FY invoices?`,
            () => import_multiple_invoices(current_fy_invoices)
        );
    });
    
    $('#import-all-ago2o-btn').on('click', function() {
        const ago2o_invoices = invoices.filter(inv => 
            inv.invoice_number && inv.invoice_number.startsWith('AGO2O')
        ).map(inv => inv.invoice_id);
        
        if (ago2o_invoices.length === 0) {
            frappe.msgprint('No AGO2O invoices found.');
            return;
        }
        
        frappe.confirm(
            `Import all ${ago2o_invoices.length} AGO2O invoices?`,
            () => import_multiple_invoices(ago2o_invoices)
        );
    });
    
    // Individual import buttons
    $(document).on('click', '.import-single-btn', function() {
        const invoice_id = $(this).data('invoice-id');
        import_multiple_invoices([invoice_id]);
    });
    
    // Preview functionality
    $(document).on('click', '.preview-btn', function() {
        const invoice_id = $(this).data('invoice-id');
        const invoice = invoices.find(inv => inv.invoice_id === invoice_id);
        show_invoice_preview(invoice);
    });
    
    // Statistics button
    $('#show-statistics-btn').on('click', function() {
        show_detailed_statistics(invoices, filtered_invoices);
    });
    
    // Load More button
    $('#load-more-btn').on('click', function() {
        load_more_requisitions(dialog, invoices);
    });
    
    // Refresh Dashboard button  
    $('#refresh-dashboard-btn').on('click', function() {
        dialog.hide();
        show_advanced_portal_dashboard();
    });
    
    function apply_all_filters() {
        const pattern_filter = $('#pattern-filter').val();
        const search_term = $('#search-input').val().toLowerCase();
        const amount_filter = $('#amount-filter').val();
        
        $('#invoices-tbody tr').each(function() {
            const $row = $(this);
            const pattern = $row.data('pattern');
            const fy = $row.data('fy');
            const invoice_number = $row.data('invoice-number');
            const customer = $row.data('customer');
            const amount = parseFloat($row.data('amount')) || 0;
            
            let show = true;
            
            // Pattern filter
            if (pattern_filter === 'ago2o' && pattern !== 'ago2o') show = false;
            if (pattern_filter === 'current-fy' && fy !== 'current') show = false;
            if (pattern_filter === 'last-fy' && fy !== 'last') show = false;
            
            // Search filter
            if (search_term && show) {
                const searchable = `${invoice_number} ${customer}`.toLowerCase();
                if (!searchable.includes(search_term)) show = false;
            }
            
            // Amount filter
            if (amount_filter !== 'all' && show) {
                if (amount_filter === 'high' && amount <= 50000) show = false;
                if (amount_filter === 'medium' && (amount < 10000 || amount > 50000)) show = false;
                if (amount_filter === 'low' && amount >= 10000) show = false;
            }
            
            $row.toggle(show);
        });
        
        update_visible_count();
    }
    
    function update_visible_count() {
        const visible_count = $('#invoices-tbody tr:visible').length;
        $('#pattern-filter option:first').text(`All Invoices (${visible_count})`);
    }
    
    function update_selection_summary() {
        const count = selected_invoices.size;
        const total_amount = [...selected_invoices].reduce((sum, inv) => sum + inv.amount, 0);
        
        $('#selection-count').text(count);
        $('#selected-count').text(count);
        $('#selected-amount').text(total_amount.toLocaleString('en-IN'));
        
        $('#import-selected-btn').prop('disabled', count === 0);
        $('.selection-summary').toggle(count > 0);
    }
}

function import_multiple_invoices(invoice_ids) {
    console.log("📥 Importing invoices:", invoice_ids);
    
    if (!invoice_ids || invoice_ids.length === 0) {
        frappe.msgprint('No invoices selected for import.');
        return;
    }
    
    const progress_dialog = frappe.show_progress('Importing Invoices', 0, invoice_ids.length, 'Starting import...');
    
    frappe.call({
        method: 'php_portal_invoices.import_multiple_portal_invoices',
        args: {
            invoice_ids: invoice_ids
        },
        callback: function(response) {
            progress_dialog.hide();
            
            if (response.message && response.message.success) {
                const results = response.message;
                
                frappe.msgprint({
                    title: 'Import Complete',
                    message: `
                        <div style="margin: 15px 0;">
                            <h4>✅ Import Results</h4>
                            <ul>
                                <li><strong>Successfully Imported:</strong> ${results.imported_count} invoices</li>
                                <li><strong>Already Existed:</strong> ${results.skipped_count} invoices</li>
                                <li><strong>Failed:</strong> ${results.failed_count} invoices</li>
                            </ul>
                            ${results.failed_count > 0 ? `<div class="alert alert-warning"><strong>Failures:</strong><br>${results.failures.join('<br>')}</div>` : ''}
                        </div>
                    `,
                    indicator: 'green'
                });
                
                // Refresh the portal list after successful import
                setTimeout(() => {
                    show_advanced_portal_dashboard();
                }, 2000);
            } else {
                frappe.msgprint('Import failed: ' + (response.exc || 'Unknown error'));
            }
        },
        error: function(err) {
            progress_dialog.hide();
            frappe.msgprint('Import error: ' + err.message);
        }
    });
}

function show_invoice_preview(invoice) {
    console.log("👁️ Showing invoice preview for:", invoice.invoice_id);
    
    // Prioritize portal_invoice_number for display
    const display_invoice_number = invoice.portal_invoice_number || invoice.invoice_number;
    const has_portal_number = !!invoice.portal_invoice_number;
    
    const preview_dialog = new frappe.ui.Dialog({
        title: `📋 Invoice Preview: ${display_invoice_number}`,
        size: 'large',
        fields: [
            {
                fieldtype: 'HTML',
                fieldname: 'preview_html',
                options: `
                    <div class="invoice-preview">
                        <div class="row">
                            <div class="col-md-6">
                                <h4>📄 Invoice Details</h4>
                                <table class="table table-sm">
                                    <tr><th>ID:</th><td>${invoice.invoice_id}</td></tr>
                                    <tr><th>${has_portal_number ? 'Portal Invoice Number:' : 'Invoice Number:'}</th><td><strong style="color: ${has_portal_number ? '#2c3e50' : '#666'};">${display_invoice_number}</strong></td></tr>
                                    ${has_portal_number && invoice.invoice_number ? `<tr><th>Internal Number:</th><td style="color: #999;">${invoice.invoice_number}</td></tr>` : ''}
                                    ${invoice.portal_invoice_number ? `<tr><th>Series:</th><td><span class="badge badge-primary">AGO2O</span> ${invoice.portal_invoice_number.includes('25-26') ? '<span class="badge badge-success">Current FY</span>' : invoice.portal_invoice_number.includes('24-25') ? '<span class="badge badge-warning">Previous FY</span>' : ''}</td></tr>` : ''}
                                    <tr><th>Date:</th><td>${invoice.created_date ? new Date(invoice.created_date).toLocaleDateString('en-IN') : 'N/A'}</td></tr>
                                    <tr><th>Total Items:</th><td>${invoice.total_items || 0}</td></tr>
                                    <tr><th>Amount:</th><td><strong style="color: #27ae60;">₹${(parseFloat(invoice.total_amount) || 0).toLocaleString('en-IN')}</strong></td></tr>
                                </table>
                            </div>
                            <div class="col-md-6">
                                <h4>🏢 Customer & Vendor Info</h4>
                                <table class="table table-sm">
                                    <tr><th>Customer:</th><td><strong>${invoice.customer_name || invoice.entity_code || 'N/A'}</strong></td></tr>
                                    <tr><th>Delivery To:</th><td>${invoice.delivery_to || invoice.subentity_code || 'N/A'}</td></tr>
                                    <tr><th>Vendor:</th><td>${invoice.vendor_name || 'AGO2O STORES LLP'}</td></tr>
                                    <tr><th>Entity Code:</th><td>${invoice.entity_code || 'N/A'}</td></tr>
                                    <tr><th>Subentity Code:</th><td>${invoice.subentity_code || 'N/A'}</td></tr>
                                </table>
                            </div>
                        </div>
                        
                        <div style="margin-top: 20px; text-align: center;">
                            <button class="btn btn-success" onclick="import_multiple_invoices(['${invoice.invoice_id}'])">
                                📥 Import This Invoice
                            </button>
                        </div>
                    </div>
                `
            }
        ]
    });
    
    preview_dialog.show();
}

function show_detailed_statistics(all_invoices, filtered_invoices) {
    console.log("📊 Showing detailed statistics");
    
    const stats = calculate_detailed_statistics(all_invoices, filtered_invoices);
    
    const stats_dialog = new frappe.ui.Dialog({
        title: '📊 Detailed Portal Statistics',
        size: 'large',
        fields: [
            {
                fieldtype: 'HTML',
                fieldname: 'stats_html',
                options: generate_statistics_html(stats)
            }
        ]
    });
    
    stats_dialog.show();
}

function calculate_detailed_statistics(all_invoices, filtered_invoices) {
    const stats = {
        total: { count: all_invoices.length, amount: 0 },
        filtered: { count: filtered_invoices.length, amount: 0 },
        ago2o: { count: 0, amount: 0 },
        current_fy: { count: 0, amount: 0 },
        last_fy: { count: 0, amount: 0 },
        by_customer: {},
        by_amount_range: { low: 0, medium: 0, high: 0 }
    };
    
    all_invoices.forEach(inv => {
        const amount = parseFloat(inv.total_amount) || 0;
        stats.total.amount += amount;
        
        if (inv.invoice_number && inv.invoice_number.startsWith('AGO2O')) {
            stats.ago2o.count++;
            stats.ago2o.amount += amount;
        }
        
        if (inv.invoice_number && inv.invoice_number.includes('25-26')) {
            stats.current_fy.count++;
            stats.current_fy.amount += amount;
        }
        
        if (inv.invoice_number && inv.invoice_number.includes('24-25')) {
            stats.last_fy.count++;
            stats.last_fy.amount += amount;
        }
        
        const customer = inv.customer_name || inv.entity_code || 'Unknown';
        if (!stats.by_customer[customer]) {
            stats.by_customer[customer] = { count: 0, amount: 0 };
        }
        stats.by_customer[customer].count++;
        stats.by_customer[customer].amount += amount;
        
        if (amount < 10000) stats.by_amount_range.low++;
        else if (amount <= 50000) stats.by_amount_range.medium++;
        else stats.by_amount_range.high++;
    });
    
    return stats;
}

function generate_statistics_html(stats) {
    const top_customers = Object.entries(stats.by_customer)
        .sort((a, b) => b[1].amount - a[1].amount)
        .slice(0, 10);
    
    return `
        <div class="statistics-details">
            <div class="row">
                <div class="col-md-6">
                    <h4>📊 Overall Statistics</h4>
                    <table class="table table-striped">
                        <tr><th>Total Invoices:</th><td>${stats.total.count}</td></tr>
                        <tr><th>Total Value:</th><td>₹${stats.total.amount.toLocaleString('en-IN')}</td></tr>
                        <tr><th>AGO2O Invoices:</th><td>${stats.ago2o.count} (₹${stats.ago2o.amount.toLocaleString('en-IN')})</td></tr>
                        <tr><th>Current FY 25-26:</th><td>${stats.current_fy.count} (₹${stats.current_fy.amount.toLocaleString('en-IN')})</td></tr>
                        <tr><th>Last FY 24-25:</th><td>${stats.last_fy.count} (₹${stats.last_fy.amount.toLocaleString('en-IN')})</td></tr>
                    </table>
                </div>
                <div class="col-md-6">
                    <h4>💰 Amount Distribution</h4>
                    <table class="table table-striped">
                        <tr><th>High Value (>₹50k):</th><td>${stats.by_amount_range.high} invoices</td></tr>
                        <tr><th>Medium (₹10k-₹50k):</th><td>${stats.by_amount_range.medium} invoices</td></tr>
                        <tr><th>Low Value (<₹10k):</th><td>${stats.by_amount_range.low} invoices</td></tr>
                    </table>
                </div>
            </div>
            
            <div class="row" style="margin-top: 20px;">
                <div class="col-md-12">
                    <h4>🏆 Top 10 Customers by Value</h4>
                    <table class="table table-striped">
                        <thead>
                            <tr><th>Customer</th><th>Invoice Count</th><th>Total Value</th></tr>
                        </thead>
                        <tbody>
                            ${top_customers.map(([customer, data]) => 
                                `<tr><td>${customer}</td><td>${data.count}</td><td>₹${data.amount.toLocaleString('en-IN')}</td></tr>`
                            ).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    `;
}

// Load More Requisitions Function
function load_more_requisitions(dialog, current_invoices) {
    console.log("📥 Loading more requisitions...");
    
    // Disable the load more button and show loading state
    const $loadMoreBtn = $('#load-more-btn');
    const originalText = $loadMoreBtn.html();
    $loadMoreBtn.prop('disabled', true).html('⏳ Loading...');
    
    // Calculate current offset
    const current_count = current_invoices.length;
    const load_count = 300;
    
    frappe.call({
        method: 'o2o_erpnext.api.php_portal_invoices.get_recent_purchase_requisitions',
        args: { 
            limit: load_count,
            offset: current_count 
        },
        callback: function(r) {
            if (r.message && r.message.status === 'success') {
                const new_requisitions = r.message.data || [];
                const pagination = r.message.pagination || {};
                
                if (new_requisitions.length === 0) {
                    frappe.show_alert({
                        message: __('No more records to load'),
                        indicator: 'orange'
                    });
                    $loadMoreBtn.prop('disabled', true).html('📭 No More Records');
                    return;
                }
                
                // Sort new requisitions by created_at DESC
                const sorted_new_requisitions = new_requisitions.sort((a, b) => {
                    const a_date = new Date(a.created_at);
                    const b_date = new Date(b.created_at);
                    
                    if (a_date !== b_date) {
                        return b_date - a_date; // Latest first
                    }
                    return (b.id || 0) - (a.id || 0);
                });
                
                // Generate HTML for new rows
                const new_rows_html = generate_enhanced_invoice_rows(sorted_new_requisitions);
                
                // Append to existing table
                $('#requisitions-tbody').append(new_rows_html);
                
                // Update button text with new count
                const total_loaded = current_count + new_requisitions.length;
                $loadMoreBtn.prop('disabled', false).html(`📥 Load More Records (+300) | Loaded: ${total_loaded}`);
                
                // Show success message
                frappe.show_alert({
                    message: __('Loaded {0} more requisitions. Total: {1}', [new_requisitions.length, total_loaded]),
                    indicator: 'green'
                });
                
                // Add new requisitions to the current list for future reference
                current_invoices.push(...sorted_new_requisitions);
                
                // Reinitialize event handlers for new rows only (avoid duplicate handlers)
                // The existing initialize_enhanced_dashboard_features handles all event binding
                
                console.log(`📊 Loaded ${new_requisitions.length} more requisitions. Total now: ${total_loaded}`);
                
            } else {
                frappe.show_alert({
                    message: r.message ? r.message.message : __('Failed to load more requisitions'),
                    indicator: 'red'
                });
                $loadMoreBtn.prop('disabled', false).html(originalText);
            }
        },
        error: function(err) {
            frappe.show_alert({
                message: __('Network error while loading more records'),
                indicator: 'red'  
            });
            $loadMoreBtn.prop('disabled', false).html(originalText);
        }
    });
}

console.log("✅ Purchase Invoice List Script Loaded");