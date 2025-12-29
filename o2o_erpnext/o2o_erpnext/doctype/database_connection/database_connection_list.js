// Copyright (c) 2025, Ascratech LLP and contributors
// For license information, please see license.txt

frappe.listview_settings['Database Connection'] = {
    onload: function(listview) {
        // Add Database Connection Control Panel button (modified to include all connections)
        listview.page.add_inner_button(__('Database Connection Control Panel'), function() {
            show_database_connection_dashboard(listview);
        }).addClass('btn-primary');
    },
    
    // Add custom action buttons to each row
    get_indicator: function(doc) {
        const status_colors = {
            'Connected': 'green',
            'Disconnected': 'red', 
            'Error': 'red',
            'Testing': 'orange',
            'Unknown': 'grey'
        };
        return [__(doc.connection_status), status_colors[doc.connection_status] || 'grey'];
    },
    
    // Add status indicator for each row
    formatters: {
        connection_status: function(value) {
            const status_colors = {
                'Connected': 'green',
                'Disconnected': 'red',
                'Error': 'red',
                'Testing': 'orange',
                'Unknown': 'grey'
            };
            const color = status_colors[value] || 'grey';
            return `<span class="indicator-pill ${color}">${value}</span>`;
        }
    }
};

function show_database_connection_dashboard(listview) {
    // Check if user has selected a connection from the list view
    let selected = listview.get_checked_items();
    
    if (selected.length === 0) {
        frappe.msgprint({
            title: __('No Connection Selected'),
            message: __('Please select a database connection from the list by checking the checkbox, then click the Database Connection Control Panel button.'),
            indicator: 'blue'
        });
        return;
    }
    
    if (selected.length > 1) {
        frappe.msgprint({
            title: __('Multiple Connections Selected'),
            message: __('Please select only one database connection to test.'),
            indicator: 'orange'
        });
        return;
    }
    
    // Get the selected connection
    let connection = selected[0];
    
    // Show enhanced test dialog directly for the selected connection
    show_connection_test_dialog(connection.name);
}

function show_connection_selection_dialog(listview) {
    // Get available connections from the current list view
    let connections = [];
    
    // Extract connections from the list view data
    if (listview && listview.data && listview.data.length > 0) {
        connections = listview.data.map(function(item) {
            return {
                name: item.name,
                display_name: item.display_name || item.name,
                database_type: item.database_type,
                host: item.host,
                database_name: item.database_name,
                ssh_tunnel: item.ssh_tunnel,
                connection_status: item.connection_status
            };
        });
    }
    
    if (connections.length === 0) {
        frappe.msgprint(__('No database connections found. Please create a connection first.'));
        return;
    }
    
    // Create selection dialog
    let d = new frappe.ui.Dialog({
        title: __('Select Database Connection'),
        size: 'medium',
        fields: [
            {
                fieldtype: 'Section Break',
                label: __('Choose Connection')
            },
            {
                fieldtype: 'Select',
                fieldname: 'selected_connection',
                label: __('Database Connection'),
                options: connections.map(conn => `${conn.name}\n${conn.display_name}`).join('\n'),
                reqd: 1,
                description: __('Select the database connection you want to test or manage')
            },
            {
                fieldtype: 'Column Break'
            },
            {
                fieldtype: 'HTML',
                fieldname: 'connection_info',
                label: __('Connection Details')
            }
        ],
        primary_action_label: __('Test Connection'),
        primary_action: function() {
            let values = d.get_values();
            if (values && values.selected_connection) {
                d.hide();
                // Show enhanced test dialog for selected connection
                show_connection_test_dialog(values.selected_connection);
            }
        },
        secondary_action_label: __('Cancel')
    });
    
    // Update connection info when selection changes
    d.fields_dict.selected_connection.$input.on('change', function() {
        let selected_name = d.get_value('selected_connection');
        let selected_conn = connections.find(conn => conn.name === selected_name);
        
        if (selected_conn) {
            let info_html = `
                <div style="padding: 10px; background: #f8f9fa; border-radius: 4px; margin-top: 10px;">
                    <h6><i class="fa fa-database"></i> ${selected_conn.display_name}</h6>
                    <div style="font-size: 12px; color: #666;">
                        <p><strong>Type:</strong> ${selected_conn.database_type}</p>
                        <p><strong>Host:</strong> ${selected_conn.host}</p>
                        <p><strong>Database:</strong> ${selected_conn.database_name}</p>
                        <p><strong>Connection Type:</strong> ${selected_conn.ssh_tunnel ? 'SSH Tunnel' : 'Direct Connection'}</p>
                        <p><strong>Status:</strong> <span class="indicator-pill ${selected_conn.connection_status === 'Connected' ? 'green' : 'grey'}">${selected_conn.connection_status || 'Unknown'}</span></p>
                    </div>
                </div>
            `;
            d.fields_dict.connection_info.$wrapper.html(info_html);
        }
    });
    
    d.show();
    
    // Trigger initial info display
    if (connections.length > 0) {
        d.set_value('selected_connection', connections[0].name);
        d.fields_dict.selected_connection.$input.trigger('change');
    }
}

function create_database_connection_dialog(connections, listview) {
    let dialog_html = `
        <div class="database-connection-dashboard">
            <style>
                .database-connection-dashboard {
                    padding: 10px;
                }
                .connection-card {
                    border: 1px solid #d1d8dd;
                    border-radius: 6px;
                    padding: 15px;
                    margin-bottom: 15px;
                    background: #f8f9fa;
                }
                .connection-card.ssh {
                    border-left: 4px solid #007bff;
                }
                .connection-card.direct {
                    border-left: 4px solid #28a745;
                }
                .connection-card.active {
                    border-color: #28a745;
                    background: #f0fff4;
                }
                .connection-card.inactive {
                    border-color: #dc3545;
                    background: #fff5f5;
                }
                .connection-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 10px;
                }
                .connection-name {
                    font-weight: 600;
                    font-size: 14px;
                }
                .connection-type {
                    display: inline-block;
                    padding: 2px 8px;
                    border-radius: 8px;
                    font-size: 10px;
                    font-weight: 500;
                    margin-left: 8px;
                }
                .connection-type.ssh {
                    background: #007bff;
                    color: white;
                }
                .connection-type.direct {
                    background: #28a745;
                    color: white;
                }
                .connection-status {
                    display: inline-block;
                    padding: 4px 12px;
                    border-radius: 12px;
                    font-size: 12px;
                    font-weight: 500;
                }
                .connection-status.connected {
                    background: #28a745;
                    color: white;
                }
                .connection-status.disconnected {
                    background: #dc3545;
                    color: white;
                }
                .connection-status.unknown {
                    background: #6c757d;
                    color: white;
                }
                .connection-details {
                    font-size: 12px;
                    color: #666;
                    margin-bottom: 10px;
                }
                .connection-actions {
                    display: flex;
                    gap: 8px;
                }
                .refresh-all {
                    margin-bottom: 15px;
                    text-align: right;
                }
            </style>
            <div class="refresh-all">
                <button class="btn btn-xs btn-default" onclick="refresh_connection_dashboard()">
                    <i class="fa fa-refresh"></i> Refresh Status
                </button>
            </div>
            <div id="database-connections-list">
                <!-- Connections will be inserted here -->
            </div>
        </div>
    `;
    
    let d = new frappe.ui.Dialog({
        title: __('Database Connection Control Panel'),
        size: 'large',
        fields: [
            {
                fieldtype: 'HTML',
                fieldname: 'dashboard_html'
            }
        ]
    });
    
    d.fields_dict.dashboard_html.$wrapper.html(dialog_html);
    d.show();
    
    // Render connections
    render_database_connections(connections, d);
    
    // Auto-refresh every 5 seconds
    let refresh_interval = setInterval(function() {
        if (!d.is_visible) {
            clearInterval(refresh_interval);
            return;
        }
        refresh_connection_status(d);
    }, 5000);
    
    // Store dialog reference globally for refresh function
    window.database_connection_dialog = d;
}

function render_database_connections(connections, dialog) {
    let container = dialog.$wrapper.find('#database-connections-list');
    container.empty();
    
    if (!connections || connections.length === 0) {
        container.html('<p class="text-muted">No database connections found.</p>');
        return;
    }
    
    connections.forEach(function(conn) {
        let is_ssh = conn.ssh_tunnel;
        let connection_type = is_ssh ? 'ssh' : 'direct';
        let type_label = is_ssh ? 'SSH' : 'DIRECT';
        
        // Determine connection status
        let status_info = get_connection_status(conn);
        let card_class = status_info.card_class;
        let status_class = status_info.status_class;
        let status_text = status_info.status_text;
        
        let details_html = '';
        if (is_ssh && conn.tunnel_status && conn.tunnel_status.is_connected) {
            details_html = `
                <div class="connection-details">
                    <i class="fa fa-plug"></i> Local Port: <strong>${conn.tunnel_status.local_port}</strong> |
                    <i class="fa fa-clock"></i> Started: ${frappe.datetime.str_to_user(conn.tunnel_status.started_at)}
                </div>
            `;
        } else {
            details_html = `
                <div class="connection-details">
                    <i class="fa fa-database"></i> ${conn.database_type} | 
                    <i class="fa fa-server"></i> ${conn.host}:${conn.port || (conn.database_type === 'MySQL' ? 3306 : 5432)} |
                    <i class="fa fa-hdd-o"></i> ${conn.database_name}
                </div>
            `;
        }
        
        // Generate action buttons based on connection type
        let action_buttons = get_action_buttons(conn, is_ssh);
        
        let card_html = `
            <div class="connection-card ${connection_type} ${card_class}" data-connection="${conn.name}">
                <div class="connection-header">
                    <div class="connection-name">
                        <i class="fa fa-database"></i> ${conn.display_name}
                        <span class="connection-type ${connection_type}">${type_label}</span>
                        <span class="text-muted" style="font-weight: normal; font-size: 12px;">(${conn.name})</span>
                    </div>
                    <span class="connection-status ${status_class}">${status_text}</span>
                </div>
                ${details_html}
                <div class="connection-actions">
                    ${action_buttons}
                </div>
            </div>
        `;
        
        container.append(card_html);
    });
}

function get_connection_status(conn) {
    if (conn.ssh_tunnel) {
        // SSH connection
        let is_connected = conn.tunnel_status && conn.tunnel_status.is_connected;
        return {
            card_class: is_connected ? 'active' : 'inactive',
            status_class: is_connected ? 'connected' : 'disconnected',
            status_text: is_connected ? 'Connected' : 'Disconnected'
        };
    } else {
        // Direct connection
        let status = conn.connection_status || 'Unknown';
        return {
            card_class: status === 'Connected' ? 'active' : 'inactive',
            status_class: status.toLowerCase(),
            status_text: status
        };
    }
}

function get_action_buttons(conn, is_ssh) {
    let buttons = [];
    
    if (is_ssh) {
        // SSH connection buttons
        let is_connected = conn.tunnel_status && conn.tunnel_status.is_connected;
        
        if (is_connected) {
            buttons.push(`<button class="btn btn-xs btn-danger" onclick="stop_tunnel('${conn.name}')">
                <i class="fa fa-stop"></i> Stop Tunnel
            </button>`);
        } else {
            buttons.push(`<button class="btn btn-xs btn-success" onclick="start_tunnel('${conn.name}')">
                <i class="fa fa-play"></i> Start Tunnel
            </button>`);
        }
        
        buttons.push(`<button class="btn btn-xs btn-default" onclick="restart_tunnel('${conn.name}')">
            <i class="fa fa-refresh"></i> Restart
        </button>`);
    }
    
    // Test Connection button for all connections
    buttons.push(`<button class="btn btn-xs btn-primary" onclick="test_connection('${conn.name}')">
        <i class="fa fa-check"></i> Test Connection
    </button>`);
    
    return buttons.join('');
}

function refresh_connection_status(dialog) {
    frappe.call({
        method: 'o2o_erpnext.api.database_connection_api.get_all_database_connections',
        callback: function(r) {
            if (r.message && r.message.success) {
                render_database_connections(r.message.connections, dialog);
            }
        }
    });
}

window.refresh_connection_dashboard = function() {
    if (window.database_connection_dialog) {
        refresh_connection_status(window.database_connection_dialog);
        frappe.show_alert({message: __('Status refreshed'), indicator: 'blue'}, 2);
    }
};

window.start_tunnel = function(connection_name) {
    frappe.call({
        method: 'o2o_erpnext.api.database_connection_api.start_ssh_tunnel',
        args: {connection_name: connection_name},
        freeze: true,
        freeze_message: __('Starting SSH tunnel...'),
        callback: function(r) {
            if (r.message && r.message.success) {
                frappe.show_alert({message: __('Tunnel started successfully'), indicator: 'green'}, 3);
                if (window.ssh_tunnel_dialog) {
                    refresh_tunnel_status(window.ssh_tunnel_dialog);
                }
            } else {
                frappe.msgprint({
                    title: __('Error'),
                    message: r.message.message || __('Failed to start tunnel'),
                    indicator: 'red'
                });
            }
        }
    });
};

window.stop_tunnel = function(connection_name) {
    frappe.call({
        method: 'o2o_erpnext.api.database_connection_api.stop_ssh_tunnel',
        args: {connection_name: connection_name},
        freeze: true,
        freeze_message: __('Stopping SSH tunnel...'),
        callback: function(r) {
            if (r.message && r.message.success) {
                frappe.show_alert({message: __('Tunnel stopped'), indicator: 'orange'}, 3);
                if (window.ssh_tunnel_dialog) {
                    refresh_tunnel_status(window.ssh_tunnel_dialog);
                }
            } else {
                frappe.msgprint({
                    title: __('Error'),
                    message: r.message.message || __('Failed to stop tunnel'),
                    indicator: 'red'
                });
            }
        }
    });
};

window.test_connection = function(connection_name) {
    // Show enhanced connection test dialog
    show_connection_test_dialog(connection_name);
};

function show_connection_test_dialog(connection_name) {
    // First get connection details
    frappe.call({
        method: 'o2o_erpnext.api.database_connection_api.get_connection_details',
        args: {connection_name: connection_name},
        callback: function(r) {
            if (r.message && r.message.success) {
                create_connection_test_dialog(r.message.connection);
            } else {
                frappe.msgprint(__('Failed to load connection details'));
            }
        }
    });
}

function create_connection_test_dialog(connection) {
    let dialog_fields = [
        {
            fieldtype: 'Section Break',
            label: __('Connection Test Configuration')
        },
        {
            fieldtype: 'Data',
            fieldname: 'connection_name',
            label: __('Connection Name'),
            default: connection.name,
            read_only: 1
        },
        {
            fieldtype: 'Data',
            fieldname: 'display_name',
            label: __('Display Name'),
            default: connection.display_name,
            read_only: 1
        },
        {
            fieldtype: 'Column Break'
        },
        {
            fieldtype: 'Select',
            fieldname: 'database_type',
            label: __('Database Type'),
            options: 'MySQL\nPostgreSQL\nSQLite',
            default: connection.database_type,
            read_only: 1
        },
        {
            fieldtype: 'Data',
            fieldname: 'host',
            label: __('Host'),
            default: connection.host,
            read_only: 1
        }
    ];

    // Add SSH tunnel options if connection uses SSH
    if (connection.ssh_tunnel) {
        dialog_fields.push(
            {
                fieldtype: 'Section Break',
                label: __('SSH Tunnel Configuration')
            },
            {
                fieldtype: 'Check',
                fieldname: 'use_ssh_tunnel',
                label: __('Use SSH Tunnel'),
                default: 1,
                description: __('Enable SSH tunnel for this connection test')
            },
            {
                fieldtype: 'Data',
                fieldname: 'ssh_host',
                label: __('SSH Host'),
                default: connection.ssh_host,
                depends_on: 'use_ssh_tunnel'
            },
            {
                fieldtype: 'Column Break'
            },
            {
                fieldtype: 'Int',
                fieldname: 'ssh_port',
                label: __('SSH Port'),
                default: connection.ssh_port || 22,
                depends_on: 'use_ssh_tunnel'
            },
            {
                fieldtype: 'Data',
                fieldname: 'ssh_username',
                label: __('SSH Username'),
                default: connection.ssh_username,
                depends_on: 'use_ssh_tunnel'
            }
        );
    }

    // Add database selection options
    dialog_fields.push(
        {
            fieldtype: 'Section Break',
            label: __('Database Selection')
        },
        {
            fieldtype: 'Data',
            fieldname: 'database_name',
            label: __('Database Name'),
            default: connection.database_name,
            description: __('Specify which database to connect to')
        },
        {
            fieldtype: 'Column Break'
        },
        {
            fieldtype: 'Int',
            fieldname: 'port',
            label: __('Port'),
            default: connection.port || (connection.database_type === 'MySQL' ? 3306 : 5432)
        },
        {
            fieldtype: 'Section Break',
            label: __('Test Options')
        },
        {
            fieldtype: 'Check',
            fieldname: 'test_tables',
            label: __('Test Table Access'),
            default: 1,
            description: __('Test if we can access database tables')
        },
        {
            fieldtype: 'Check',
            fieldname: 'test_write_access',
            label: __('Test Write Access'),
            default: 0,
            description: __('Test if we can write to the database (creates and drops a test table)')
        }
    );

    let d = new frappe.ui.Dialog({
        title: __('Test Database Connection: {0}', [connection.display_name]),
        size: 'large',
        fields: dialog_fields,
        primary_action_label: __('Test Connection'),
        primary_action: function() {
            let values = d.get_values();
            if (values) {
                execute_connection_test(values, d);
            }
        },
        secondary_action_label: __('Cancel')
    });

    d.show();
}

function execute_connection_test(test_config, dialog) {
    // Show progress indicator
    let progress_html = `
        <div class="test-progress" style="padding: 20px; text-align: center;">
            <div class="progress" style="margin-bottom: 15px;">
                <div class="progress-bar progress-bar-striped progress-bar-animated" 
                     role="progressbar" style="width: 0%"></div>
            </div>
            <div class="test-status">Initializing connection test...</div>
        </div>
    `;
    
    dialog.$wrapper.find('.modal-body').html(progress_html);
    
    // Update progress function
    function update_progress(percent, message) {
        dialog.$wrapper.find('.progress-bar').css('width', percent + '%');
        dialog.$wrapper.find('.test-status').text(message);
    }

    // Step 1: Start SSH tunnel if needed
    if (test_config.use_ssh_tunnel) {
        update_progress(20, 'Starting SSH tunnel...');
        
        frappe.call({
            method: 'o2o_erpnext.api.database_connection_api.start_ssh_tunnel',
            args: {connection_name: test_config.connection_name},
            callback: function(r) {
                if (r.message && r.message.success) {
                    update_progress(50, 'SSH tunnel established. Testing database connection...');
                    test_database_connection(test_config, dialog, update_progress);
                } else {
                    show_test_error('SSH tunnel failed: ' + (r.message.message || 'Unknown error'), dialog);
                }
            }
        });
    } else {
        update_progress(50, 'Testing database connection...');
        test_database_connection(test_config, dialog, update_progress);
    }
}

function test_database_connection(test_config, dialog, update_progress) {
    frappe.call({
        method: 'o2o_erpnext.api.database_connection_api.enhanced_test_connection',
        args: {
            connection_name: test_config.connection_name,
            database_name: test_config.database_name,
            port: test_config.port,
            test_tables: test_config.test_tables,
            test_write_access: test_config.test_write_access
        },
        callback: function(r) {
            if (r.message && r.message.success) {
                update_progress(100, 'Connection test completed successfully!');
                show_test_results(r.message.details, dialog);
            } else {
                show_test_error(r.message.message || 'Connection test failed', dialog);
            }
        }
    });
}

function show_test_results(details, dialog) {
    let results_html = `
        <div class="test-results" style="padding: 20px;">
            <div class="alert alert-success">
                <h4><i class="fa fa-check-circle"></i> Connection Test Successful!</h4>
            </div>
            
            <div class="row">
                <div class="col-md-6">
                    <h5>Database Information</h5>
                    <table class="table table-bordered">
                        <tr><td><strong>Database Version:</strong></td><td>${details.version}</td></tr>
                        <tr><td><strong>Database Name:</strong></td><td>${details.database}</td></tr>
                        <tr><td><strong>User:</strong></td><td>${details.user}</td></tr>
                        <tr><td><strong>Host:</strong></td><td>${details.host}</td></tr>
                        <tr><td><strong>Port:</strong></td><td>${details.port}</td></tr>
                    </table>
                </div>
                <div class="col-md-6">
                    <h5>Test Results</h5>
                    <table class="table table-bordered">
                        <tr><td><strong>Table Count:</strong></td><td>${details.table_count}</td></tr>
                        <tr><td><strong>Connection Time:</strong></td><td>${details.connection_time}ms</td></tr>
                        ${details.local_port ? `<tr><td><strong>Local Port:</strong></td><td>${details.local_port}</td></tr>` : ''}
                        ${details.write_test ? `<tr><td><strong>Write Access:</strong></td><td><span class="text-success">✓ Verified</span></td></tr>` : ''}
                    </table>
                </div>
            </div>
            
            ${details.sample_tables && details.sample_tables.length > 0 ? `
                <div class="mt-3">
                    <h5>Sample Tables</h5>
                    <div class="row">
                        ${details.sample_tables.map(table => `<div class="col-md-3"><span class="label label-info">${table}</span></div>`).join('')}
                    </div>
                </div>
            ` : ''}
        </div>
    `;
    
    dialog.$wrapper.find('.modal-body').html(results_html);
    dialog.set_primary_action(__('Close'), function() { dialog.hide(); });
}

function show_test_error(error_message, dialog) {
    let error_html = `
        <div class="test-error" style="padding: 20px;">
            <div class="alert alert-danger">
                <h4><i class="fa fa-exclamation-triangle"></i> Connection Test Failed</h4>
                <p>${error_message}</p>
            </div>
            
            <div class="troubleshooting">
                <h5>Troubleshooting Tips:</h5>
                <ul>
                    <li>Verify database credentials are correct</li>
                    <li>Check if the database server is running</li>
                    <li>Ensure network connectivity to the database host</li>
                    <li>For SSH connections, verify SSH key permissions (chmod 600)</li>
                    <li>Check firewall settings and security groups</li>
                </ul>
            </div>
        </div>
    `;
    
    dialog.$wrapper.find('.modal-body').html(error_html);
    dialog.set_primary_action(__('Retry'), function() { 
        dialog.hide();
        show_connection_test_dialog(dialog.connection_name);
    });
}

window.restart_tunnel = function(connection_name) {
    frappe.call({
        method: 'o2o_erpnext.api.database_connection_api.restart_ssh_tunnel',
        args: {connection_name: connection_name},
        freeze: true,
        freeze_message: __('Restarting SSH tunnel...'),
        callback: function(r) {
            if (r.message && r.message.success) {
                frappe.show_alert({message: __('Tunnel restarted'), indicator: 'green'}, 3);
                if (window.ssh_tunnel_dialog) {
                    refresh_tunnel_status(window.ssh_tunnel_dialog);
                }
            } else {
                frappe.msgprint({
                    title: __('Error'),
                    message: r.message.message || __('Failed to restart tunnel'),
                    indicator: 'red'
                });
            }
        }
    });
};
