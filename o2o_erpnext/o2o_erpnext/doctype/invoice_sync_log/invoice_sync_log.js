// Copyright (c) 2025, O2O ERPNext and contributors
// For license information, please see license.txt

frappe.ui.form.on('Invoice Sync Log', {
    refresh: function(frm) {
        // Add custom buttons and functionality
        if (frm.doc.status === 'Failed' && !frm.doc.__islocal) {
            frm.add_custom_button(__('Retry Sync'), function() {
                retry_sync(frm);
            }, __('Actions'));
        }
        
        if (frm.doc.status === 'In Progress' && !frm.doc.__islocal) {
            frm.add_custom_button(__('Mark as Failed'), function() {
                mark_as_failed(frm);
            }, __('Actions'));
        }
        
        // Add view details button for completed syncs
        if (frm.doc.status === 'Completed' && !frm.doc.__islocal) {
            frm.add_custom_button(__('View Details'), function() {
                view_sync_details(frm);
            }, __('View'));
        }
        
        // Color code the status field
        color_status_field(frm);
        
        // Make certain fields read-only after creation
        if (!frm.doc.__islocal) {
            frm.set_df_property('invoice_id', 'read_only', 1);
            frm.set_df_property('sync_direction', 'read_only', 1);
            frm.set_df_property('operation_type', 'read_only', 1);
        }
    },
    
    status: function(frm) {
        // Update timestamp when status changes
        if (frm.doc.status === 'Completed') {
            frm.set_value('completed_at', frappe.datetime.now_datetime());
        }
        
        // Color code the status field
        color_status_field(frm);
    },
    
    onload: function(frm) {
        // Set default values
        if (frm.doc.__islocal) {
            frm.set_value('started_at', frappe.datetime.now_datetime());
            frm.set_value('status', 'In Progress');
        }
    }
});

// Retry sync operation
function retry_sync(frm) {
    frappe.confirm(
        __('Are you sure you want to retry this sync operation?'),
        function() {
            frappe.call({
                method: 'o2o_erpnext.sync.sync_utils.retry_failed_sync',
                args: {
                    sync_log_id: frm.doc.name
                },
                callback: function(r) {
                    if (r.message && r.message.success) {
                        frappe.msgprint(__('Sync retry initiated successfully'));
                        frm.reload_doc();
                    } else {
                        frappe.msgprint(__('Failed to retry sync: ' + (r.message.error || 'Unknown error')));
                    }
                }
            });
        }
    );
}

// Mark sync as failed
function mark_as_failed(frm) {
    frappe.prompt([
        {
            'fieldname': 'error_message',
            'fieldtype': 'Text',
            'label': __('Error Message'),
            'reqd': 1,
            'description': __('Please provide a reason for marking this sync as failed')
        }
    ], function(values) {
        frm.set_value('status', 'Failed');
        frm.set_value('error_message', values.error_message);
        frm.set_value('completed_at', frappe.datetime.now_datetime());
        frm.save();
    }, __('Mark as Failed'), __('Mark Failed'));
}

// View sync details in a dialog
function view_sync_details(frm) {
    let d = new frappe.ui.Dialog({
        title: __('Sync Details'),
        fields: [
            {
                'fieldname': 'sync_info',
                'fieldtype': 'HTML',
                'options': get_sync_details_html(frm.doc)
            }
        ],
        size: 'large'
    });
    
    d.show();
}

// Generate HTML for sync details
function get_sync_details_html(doc) {
    let html = `
        <div class="sync-details">
            <h4>Sync Operation Details</h4>
            <table class="table table-bordered">
                <tr><td><strong>Invoice ID:</strong></td><td>${doc.invoice_id || 'N/A'}</td></tr>
                <tr><td><strong>Direction:</strong></td><td>${doc.sync_direction || 'N/A'}</td></tr>
                <tr><td><strong>Operation:</strong></td><td>${doc.operation_type || 'N/A'}</td></tr>
                <tr><td><strong>Started:</strong></td><td>${doc.started_at || 'N/A'}</td></tr>
                <tr><td><strong>Completed:</strong></td><td>${doc.completed_at || 'N/A'}</td></tr>
                <tr><td><strong>Duration:</strong></td><td>${get_duration(doc) || 'N/A'}</td></tr>
            </table>
    `;
    
    if (doc.external_data) {
        html += `
            <h5>External Data</h5>
            <pre style="background-color: #f8f9fa; padding: 10px; border-radius: 4px; max-height: 300px; overflow-y: auto;">${doc.external_data}</pre>
        `;
    }
    
    if (doc.error_message) {
        html += `
            <h5>Error Details</h5>
            <div class="alert alert-danger">${doc.error_message}</div>
        `;
    }
    
    html += '</div>';
    return html;
}

// Calculate duration between start and completion
function get_duration(doc) {
    if (doc.started_at && doc.completed_at) {
        let start = new Date(doc.started_at);
        let end = new Date(doc.completed_at);
        let diff = (end - start) / 1000; // seconds
        
        if (diff < 60) {
            return `${diff.toFixed(1)} seconds`;
        } else if (diff < 3600) {
            return `${(diff / 60).toFixed(1)} minutes`;
        } else {
            return `${(diff / 3600).toFixed(1)} hours`;
        }
    }
    return null;
}

// Color code status field based on status value
function color_status_field(frm) {
    if (!frm.doc.status) return;
    
    let color_map = {
        'In Progress': '#ffa500',  // Orange
        'Completed': '#28a745',    // Green
        'Failed': '#dc3545',       // Red
        'Cancelled': '#6c757d'     // Gray
    };
    
    let color = color_map[frm.doc.status];
    if (color) {
        frm.get_field('status').$input.css('color', color);
        frm.get_field('status').$input.css('font-weight', 'bold');
    }
}