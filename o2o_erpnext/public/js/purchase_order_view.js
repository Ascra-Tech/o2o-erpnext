// ===== PURCHASE ORDER VIEW ENHANCEMENTS =====
// This file provides both list view and form functionality for Purchase Order
// - List view: Shows custom_purchase_receipt as clickable column
// - Form view: Auto-updates custom_purchase_receipt field from linked Purchase Receipts

// ===== LIST VIEW SETTINGS =====
// Wait for the DOM to be ready and then extend listview settings
$(document).ready(function() {
    // Ensure the listview settings exist
    if (!frappe.listview_settings['Purchase Order']) {
        frappe.listview_settings['Purchase Order'] = {};
    }
    
    // Add custom fields to existing add_fields array or create new one
    const existing_add_fields = frappe.listview_settings['Purchase Order'].add_fields || [];
    frappe.listview_settings['Purchase Order'].add_fields = [
        ...existing_add_fields,
        "custom_purchase_receipt"
    ];
    
    // Add formatters to existing formatters object or create new one
    const existing_formatters = frappe.listview_settings['Purchase Order'].formatters || {};
    frappe.listview_settings['Purchase Order'].formatters = {
        ...existing_formatters,
        custom_purchase_receipt: function(value, field, doc) {
            if (value) {
                return `<a href="/app/purchase-receipt/${encodeURIComponent(value)}" 
                          class="text-primary small" 
                          title="View Purchase Receipt: ${value}"
                          target="_blank">${value}</a>`;
            }
            return '<div class="text-muted small">-</div>';
        }
    };
});

// ===== FORM FUNCTIONALITY =====
frappe.ui.form.on('Purchase Order', {
    refresh: function(frm) {
        console.log("Purchase Order - Refresh triggered");
        update_purchase_receipt_from_linked_docs(frm);
    },
    
    onload: function(frm) {
        console.log("Purchase Order - Onload triggered");
        update_purchase_receipt_from_linked_docs(frm);
    },
    
    before_save: function(frm) {
        console.log("Purchase Order - Before Save triggered");
        update_purchase_receipt_from_linked_docs(frm);
    }
});

// ===== HELPER FUNCTION =====
function update_purchase_receipt_from_linked_docs(frm) {
    console.log("🔄 === update_purchase_receipt_from_linked_docs called ===");
    
    // Check if form exists
    if (!frm || !frm.doc) {
        console.log("❌ Form or doc not available");
        return;
    }
    
    // Only run on new/draft documents (docstatus = 0), not submitted (docstatus = 1) or cancelled (docstatus = 2)
    if (frm.doc.docstatus !== 0) {
        console.log("⏹️ Skipping - Document is submitted/cancelled (docstatus:", frm.doc.docstatus, ")");
        return;
    }
    
    // Check if document has a name (saved at least once)
    if (!frm.doc.name || frm.doc.name.startsWith('new-purchase-order')) {
        console.log("⏹️ Skipping - Document not saved yet (name:", frm.doc.name, ")");
        return;
    }
    
    console.log("📋 Purchase Order name:", frm.doc.name);
    console.log("📊 Document status:", frm.doc.docstatus, "(0=Draft, 1=Submitted, 2=Cancelled)");
    
    // Query Purchase Receipt Items to find linked Purchase Receipts
    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Purchase Receipt Item',
            filters: {
                'purchase_order': frm.doc.name
            },
            fields: ['parent', 'purchase_order'],
            limit_page_length: 1,  // We only need the first one
            order_by: 'creation desc'
        },
        callback: function(response) {
            console.log("📦 Purchase Receipt query response:", response);
            
            if (response.message && response.message.length > 0) {
                // Get the first linked Purchase Receipt
                let first_receipt = response.message[0];
                let receipt_name = first_receipt.parent;
                
                console.log("🎯 Found linked Purchase Receipt:", receipt_name);
                
                // Set the custom field value
                try {
                    frm.set_value('custom_purchase_receipt', receipt_name);
                    console.log("✅ custom_purchase_receipt set to:", receipt_name);
                    
                    // Show user notification
                    frappe.show_alert({
                        message: `Linked Purchase Receipt: ${receipt_name}`,
                        indicator: 'green'
                    }, 3);
                    
                } catch (error) {
                    console.error("❌ Error setting custom_purchase_receipt:", error);
                    frappe.show_alert({
                        message: 'Error updating custom field: ' + error.message,
                        indicator: 'red'
                    }, 5);
                }
                
            } else {
                // No linked Purchase Receipts found, clear the field
                console.log("🧹 No linked Purchase Receipts found, clearing field");
                try {
                    frm.set_value('custom_purchase_receipt', '');
                    console.log("✅ custom_purchase_receipt cleared");
                } catch (error) {
                    console.error("❌ Error clearing custom_purchase_receipt:", error);
                }
            }
        },
        error: function(error) {
            console.error("❌ Error querying Purchase Receipt Items:", error);
            frappe.show_alert({
                message: 'Error querying linked Purchase Receipts: ' + error.message,
                indicator: 'red'
            }, 5);
        }
    });
    
    console.log("🏁 === End of update function ===");
}

console.log("✅ Purchase Order View Enhancements Loaded");
