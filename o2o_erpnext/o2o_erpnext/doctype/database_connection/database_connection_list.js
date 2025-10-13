// Copyright (c) 2025, Ascratech LLP and contributors
// For license information, please see license.txt

frappe.listview_settings['Database Connection'] = {
    onload: function(listview) {
        // Add SSH Tunnel Control Panel button
        listview.page.add_inner_button(__('SSH Tunnel Control Panel'), function() {
            show_ssh_tunnel_dashboard(listview);
        }).addClass('btn-primary');
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

function show_ssh_tunnel_dashboard(listview) {
    // Fetch all SSH-enabled connections
    frappe.call({
        method: 'o2o_erpnext.api.database_connection_api.get_all_ssh_connections',
        callback: function(r) {
            if (r.message && r.message.success) {
                create_ssh_tunnel_dialog(r.message.connections, listview);
            } else {
                frappe.msgprint(__('Failed to load SSH connections'));
            }
        }
    });
}

function create_ssh_tunnel_dialog(connections, listview) {
    let dialog_html = `
        <div class="ssh-tunnel-dashboard">
            <style>
                .ssh-tunnel-dashboard {
                    padding: 10px;
                }
                .tunnel-card {
                    border: 1px solid #d1d8dd;
                    border-radius: 6px;
                    padding: 15px;
                    margin-bottom: 15px;
                    background: #f8f9fa;
                }
                .tunnel-card.active {
                    border-color: #28a745;
                    background: #f0fff4;
                }
                .tunnel-card.inactive {
                    border-color: #dc3545;
                    background: #fff5f5;
                }
                .tunnel-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 10px;
                }
                .tunnel-name {
                    font-weight: 600;
                    font-size: 14px;
                }
                .tunnel-status {
                    display: inline-block;
                    padding: 4px 12px;
                    border-radius: 12px;
                    font-size: 12px;
                    font-weight: 500;
                }
                .tunnel-status.connected {
                    background: #28a745;
                    color: white;
                }
                .tunnel-status.disconnected {
                    background: #dc3545;
                    color: white;
                }
                .tunnel-details {
                    font-size: 12px;
                    color: #666;
                    margin-bottom: 10px;
                }
                .tunnel-actions {
                    display: flex;
                    gap: 8px;
                }
                .refresh-all {
                    margin-bottom: 15px;
                    text-align: right;
                }
            </style>
            <div class="refresh-all">
                <button class="btn btn-xs btn-default" onclick="refresh_ssh_dashboard()">
                    <i class="fa fa-refresh"></i> Refresh Status
                </button>
            </div>
            <div id="tunnel-connections-list">
                <!-- Connections will be inserted here -->
            </div>
        </div>
    `;
    
    let d = new frappe.ui.Dialog({
        title: __('SSH Tunnel Control Panel'),
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
    render_tunnel_connections(connections, d);
    
    // Auto-refresh every 5 seconds
    let refresh_interval = setInterval(function() {
        if (!d.is_visible) {
            clearInterval(refresh_interval);
            return;
        }
        refresh_tunnel_status(d);
    }, 5000);
    
    // Store dialog reference globally for refresh function
    window.ssh_tunnel_dialog = d;
}

function render_tunnel_connections(connections, dialog) {
    let container = dialog.$wrapper.find('#tunnel-connections-list');
    container.empty();
    
    if (!connections || connections.length === 0) {
        container.html('<p class="text-muted">No SSH-enabled database connections found.</p>');
        return;
    }
    
    connections.forEach(function(conn) {
        let is_connected = conn.tunnel_status && conn.tunnel_status.is_connected;
        let card_class = is_connected ? 'active' : 'inactive';
        let status_class = is_connected ? 'connected' : 'disconnected';
        let status_text = is_connected ? 'Connected' : 'Disconnected';
        
        let details_html = '';
        if (is_connected) {
            details_html = `
                <div class="tunnel-details">
                    <i class="fa fa-plug"></i> Local Port: <strong>${conn.tunnel_status.local_port}</strong> |
                    <i class="fa fa-clock"></i> Started: ${frappe.datetime.str_to_user(conn.tunnel_status.started_at)}
                </div>
            `;
        } else {
            details_html = `
                <div class="tunnel-details">
                    <i class="fa fa-database"></i> ${conn.database_type} | 
                    <i class="fa fa-server"></i> ${conn.host}:${conn.database_name}
                </div>
            `;
        }
        
        let card_html = `
            <div class="tunnel-card ${card_class}" data-connection="${conn.name}">
                <div class="tunnel-header">
                    <div class="tunnel-name">
                        <i class="fa fa-database"></i> ${conn.display_name}
                        <span class="text-muted" style="font-weight: normal; font-size: 12px;">(${conn.name})</span>
                    </div>
                    <span class="tunnel-status ${status_class}">${status_text}</span>
                </div>
                ${details_html}
                <div class="tunnel-actions">
                    ${is_connected ? 
                        `<button class="btn btn-xs btn-danger" onclick="stop_tunnel('${conn.name}')">
                            <i class="fa fa-stop"></i> Stop Tunnel
                        </button>` :
                        `<button class="btn btn-xs btn-success" onclick="start_tunnel('${conn.name}')">
                            <i class="fa fa-play"></i> Start Tunnel
                        </button>`
                    }
                    <button class="btn btn-xs btn-primary" onclick="test_connection('${conn.name}')">
                        <i class="fa fa-check"></i> Test Connection
                    </button>
                    <button class="btn btn-xs btn-default" onclick="restart_tunnel('${conn.name}')">
                        <i class="fa fa-refresh"></i> Restart
                    </button>
                </div>
            </div>
        `;
        
        container.append(card_html);
    });
}

function refresh_tunnel_status(dialog) {
    frappe.call({
        method: 'o2o_erpnext.api.database_connection_api.get_all_ssh_connections',
        callback: function(r) {
            if (r.message && r.message.success) {
                render_tunnel_connections(r.message.connections, dialog);
            }
        }
    });
}

window.refresh_ssh_dashboard = function() {
    if (window.ssh_tunnel_dialog) {
        refresh_tunnel_status(window.ssh_tunnel_dialog);
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
    frappe.call({
        method: 'o2o_erpnext.api.database_connection_api.test_database_connection',
        args: {connection_name: connection_name},
        freeze: true,
        freeze_message: __('Testing database connection...'),
        callback: function(r) {
            if (r.message && r.message.success) {
                let details = r.message.details;
                frappe.msgprint({
                    title: __('Connection Successful'),
                    message: `
                        <div style="line-height: 1.8;">
                            <p><strong>Database Version:</strong> ${details.version}</p>
                            <p><strong>Database Name:</strong> ${details.database}</p>
                            <p><strong>User:</strong> ${details.user}</p>
                            <p><strong>Table Count:</strong> ${details.table_count}</p>
                            <p><strong>Local Port:</strong> ${details.local_port}</p>
                        </div>
                    `,
                    indicator: 'green'
                });
            } else {
                frappe.msgprint({
                    title: __('Connection Failed'),
                    message: r.message.message || __('Failed to connect to database'),
                    indicator: 'red'
                });
            }
        }
    });
};

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
