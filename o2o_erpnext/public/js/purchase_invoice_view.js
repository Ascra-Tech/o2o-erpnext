// ===== PURCHASE INVOICE VIEW ENHANCEMENTS =====
// This file provides both list view and form functionality for Purchase Invoice
// - List view: Shows custom_purchase_receipt and custom_purchase_order as clickable columns
// - Form view: Auto-updates custom fields from first item

// ===== LIST VIEW SETTINGS =====
// Wait for the DOM to be ready and then extend listview settings
$(document).ready(function() {
    // Ensure the listview settings exist
    if (!frappe.listview_settings['Purchase Invoice']) {
        frappe.listview_settings['Purchase Invoice'] = {};
    }
    
    // Add custom fields to existing add_fields array or create new one
    const existing_add_fields = frappe.listview_settings['Purchase Invoice'].add_fields || [];
    frappe.listview_settings['Purchase Invoice'].add_fields = [
        ...existing_add_fields,
        "custom_purchase_receipt", 
        "custom_purchase_order"
    ];
    
    // Add formatters to existing formatters object or create new one
    const existing_formatters = frappe.listview_settings['Purchase Invoice'].formatters || {};
    frappe.listview_settings['Purchase Invoice'].formatters = {
        ...existing_formatters,
        custom_purchase_receipt: function(value, field, doc) {
            if (value) {
                return `<a href="/app/purchase-receipt/${encodeURIComponent(value)}" 
                          class="text-primary small" 
                          title="View Purchase Receipt: ${value}"
                          target="_blank">${value}</a>`;
            }
            return '<div class="text-muted small">-</div>';
        },
        
        custom_purchase_order: function(value, field, doc) {
            if (value) {
                return `<a href="/app/purchase-order/${encodeURIComponent(value)}" 
                          class="text-primary small" 
                          title="View Purchase Order: ${value}"
                          target="_blank">${value}</a>`;
            }
            return '<div class="text-muted small">-</div>';
        }
    };
});

// ===== FORM FUNCTIONALITY =====
frappe.ui.form.on('Purchase Invoice', {
    refresh: function(frm) {
        console.log("Purchase Invoice - Refresh triggered");
        update_po_pr_from_first_item(frm);
    },
    
    onload: function(frm) {
        console.log("Purchase Invoice - Onload triggered");
        update_po_pr_from_first_item(frm);
    },
    
    before_save: function(frm) {
        console.log("Purchase Invoice - Before Save triggered");
        update_po_pr_from_first_item(frm);
    },
    
    items_on_form_rendered: function(frm) {
        console.log("Purchase Invoice - Items form rendered");
        update_po_pr_from_first_item(frm);
    }
});

frappe.ui.form.on('Purchase Invoice Item', {
    items_add: function(frm, cdt, cdn) {
        console.log("Item added");
        setTimeout(function() {
            update_po_pr_from_first_item(frm);
        }, 500);
    },
    
    items_remove: function(frm, cdt, cdn) {
        console.log("Item removed");
        setTimeout(function() {
            update_po_pr_from_first_item(frm);
        }, 500);
    },
    
    purchase_order: function(frm, cdt, cdn) {
        console.log("Purchase Order changed in item");
        update_po_pr_from_first_item(frm);
    },
    
    purchase_receipt: function(frm, cdt, cdn) {
        console.log("Purchase Receipt changed in item");
        update_po_pr_from_first_item(frm);
    }
});

// ===== HELPER FUNCTION =====
function update_po_pr_from_first_item(frm) {
    console.log("🔄 === update_po_pr_from_first_item called ===");
    
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
    
    console.log("📋 Document name:", frm.doc.name);
    console.log("📊 Document status:", frm.doc.docstatus, "(0=Draft, 1=Submitted, 2=Cancelled)");
    console.log("📦 Items array:", frm.doc.items);
    console.log("🔢 Number of items:", frm.doc.items ? frm.doc.items.length : 0);
    
    // Check if items exist
    if (frm.doc.items && frm.doc.items.length > 0) {
        // Get the first item
        let first_item = frm.doc.items[0];
        console.log("🎯 First item details:", {
            idx: first_item.idx,
            item_code: first_item.item_code,
            purchase_order: first_item.purchase_order,
            purchase_receipt: first_item.purchase_receipt
        });
        
        // Update custom_purchase_order
        let po_value = first_item.purchase_order || '';
        console.log("🔗 Setting custom_purchase_order to:", po_value);
        
        // Update custom_purchase_receipt  
        let pr_value = first_item.purchase_receipt || '';
        console.log("📄 Setting custom_purchase_receipt to:", pr_value);
        
        // Set values with error handling
        try {
            frm.set_value('custom_purchase_order', po_value);
            frm.set_value('custom_purchase_receipt', pr_value);
            console.log("✅ Values set successfully");
            
            // Show user notification if values were populated
            if (po_value || pr_value) {
                frappe.show_alert({
                    message: `Updated: PO: ${po_value || 'None'}, PR: ${pr_value || 'None'}`,
                    indicator: 'green'
                }, 3);
            }
        } catch (error) {
            console.error("❌ Error setting values:", error);
            frappe.show_alert({
                message: 'Error updating custom fields: ' + error.message,
                indicator: 'red'
            }, 5);
        }
        
    } else {
        // Clear fields if no items exist
        console.log("🧹 No items found, clearing fields");
        try {
            frm.set_value('custom_purchase_order', '');
            frm.set_value('custom_purchase_receipt', '');
            console.log("✅ Fields cleared");
        } catch (error) {
            console.error("❌ Error clearing fields:", error);
        }
    }
    
    console.log("🏁 === End of update function ===");
}

console.log("✅ Purchase Invoice View Enhancements Loaded");
