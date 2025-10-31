import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def install_remote_sync_fields():
    """Install custom fields for remote invoice sync tracking"""
    
    custom_fields = {
        "Purchase Invoice": [
            {
                "fieldname": "custom_skip_external_sync",
                "label": "Skip External Sync",
                "fieldtype": "Check",
                "insert_after": "custom_sync_status",
                "description": "Check this to skip creating invoice in external portal",
                "allow_on_submit": 1
            },
            {
                "fieldname": "custom_portal_sync_id", 
                "label": "Portal Invoice Code",
                "fieldtype": "Data",
                "read_only": 1,
                "insert_after": "custom_skip_external_sync",
                "description": "Generated invoice code in portal database (e.g., AGO2O/25-26/0046)",
                "allow_on_submit": 1
            },
            {
                "fieldname": "custom_sync_status",
                "label": "Portal Sync Status",
                "fieldtype": "Select",
                "options": "Not Synced\nSynced\nFailed\nSkipped",
                "default": "Not Synced",
                "read_only": 1,
                "insert_after": "custom_portal_sync_id",
                "allow_on_submit": 1
            },
            {
                "fieldname": "custom_sync_timestamp",
                "label": "Last Sync Time", 
                "fieldtype": "Datetime",
                "read_only": 1,
                "insert_after": "custom_sync_status",
                "allow_on_submit": 1
            }
        ]
    }
    
    try:
        create_custom_fields(custom_fields)
        frappe.db.commit()
        print("✅ Remote sync custom fields installed successfully")
        
    except Exception as e:
        frappe.db.rollback()
        print(f"❌ Error installing custom fields: {str(e)}")
        raise

def add_sync_buttons_to_purchase_invoice():
    """Add custom buttons for sync operations to Purchase Invoice form"""
    
    # This will be handled via client script
    client_script = """
// Add sync buttons to Purchase Invoice
frappe.ui.form.on('Purchase Invoice', {
    refresh: function(frm) {
        // Only show buttons for submitted invoices
        if (frm.doc.docstatus === 1) {
            
            // Manual Sync Button
            if (frm.doc.custom_sync_status !== 'Synced') {
                frm.add_custom_button(__('Sync to Portal'), function() {
                    frappe.call({
                        method: 'o2o_erpnext.api.remote_invoice_creator.sync_purchase_invoice_to_remote',
                        args: {
                            purchase_invoice_name: frm.doc.name
                        },
                        callback: function(r) {
                            if (r.message && r.message.success) {
                                frappe.msgprint({
                                    message: `Invoice synced successfully!<br>Portal Code: ${r.message.remote_invoice_code}`,
                                    title: 'Sync Successful',
                                    indicator: 'green'
                                });
                                frm.reload_doc();
                            } else {
                                frappe.msgprint({
                                    message: r.message ? r.message.message : 'Sync failed',
                                    title: 'Sync Failed',
                                    indicator: 'red'
                                });
                            }
                        }
                    });
                }, __('Portal Actions'));
            }
            
            // Sync Status Button
            frm.add_custom_button(__('Check Sync Status'), function() {
                frappe.call({
                    method: 'o2o_erpnext.api.remote_invoice_creator.get_invoice_sync_status',
                    args: {
                        purchase_invoice_name: frm.doc.name
                    },
                    callback: function(r) {
                        if (r.message && r.message.success) {
                            let status = r.message;
                            let message = `
                                <table class="table table-bordered">
                                    <tr><td><b>Sync Status:</b></td><td>${status.sync_status}</td></tr>
                                    <tr><td><b>Portal Code:</b></td><td>${status.portal_sync_id || 'Not Generated'}</td></tr>
                                    <tr><td><b>Skip Sync:</b></td><td>${status.skip_external_sync ? 'Yes' : 'No'}</td></tr>
                                </table>
                            `;
                            
                            frappe.msgprint({
                                message: message,
                                title: 'Sync Status',
                                indicator: status.sync_status === 'Synced' ? 'green' : 'orange'
                            });
                        }
                    }
                });
            }, __('Portal Actions'));
        }
        
        // Add indicator for sync status
        if (frm.doc.custom_sync_status) {
            let indicator_color = 'red';
            if (frm.doc.custom_sync_status === 'Synced') indicator_color = 'green';
            else if (frm.doc.custom_sync_status === 'Skipped') indicator_color = 'yellow';
            
            frm.dashboard.add_indicator(__('Portal: {0}', [frm.doc.custom_sync_status]), indicator_color);
        }
    }
});
"""
    
    # Create client script document
    if not frappe.db.exists("Client Script", "Purchase Invoice Portal Sync"):
        doc = frappe.get_doc({
            "doctype": "Client Script",
            "name": "Purchase Invoice Portal Sync", 
            "dt": "Purchase Invoice",
            "view": "Form",
            "script": client_script,
            "enabled": 1
        })
        doc.insert()
        frappe.db.commit()
        print("✅ Purchase Invoice sync buttons added")

if __name__ == "__main__":
    install_remote_sync_fields()
    add_sync_buttons_to_purchase_invoice()