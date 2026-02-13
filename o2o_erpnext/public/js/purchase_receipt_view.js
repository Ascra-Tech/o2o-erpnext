// ===== PURCHASE RECEIPT VIEW ENHANCEMENTS =====
// This file provides both list view and form functionality for Purchase Receipt
// - List view: Shows custom_purchase_invoice and custom_purchase_order as clickable columns
// - Form view: Auto-updates custom fields from first item

// ===== LIST VIEW SETTINGS =====
// Wait for the DOM to be ready and then extend listview settings
$(document).ready(function() {
    // Ensure the listview settings exist
    if (!frappe.listview_settings['Purchase Receipt1']) {
        frappe.listview_settings['Purchase Receipt1'] = {};
    }
    
    // Add custom fields to existing add_fields array or create new one
    const existing_add_fields = frappe.listview_settings['Purchase Receipt1'].add_fields || [];
    frappe.listview_settings['Purchase Receipt1'].add_fields = [
        ...existing_add_fields,
        "custom_purchase_invoice", 
        "custom_purchase_order"
    ];
    
    // Add formatters to existing formatters object or create new one
    const existing_formatters = frappe.listview_settings['Purchase Receipt2'].formatters || {};
    frappe.listview_settings['Purchase Receipt2'].formatters = {
        ...existing_formatters,
        custom_purchase_invoice: function(value, field, doc) {
            if (value) {
                return `<a href="/app/purchase-invoice/${encodeURIComponent(value)}" 
                          class="text-primary small" 
                          title="View Purchase Invoice: ${value}"
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
frappe.ui.form.on('Purchase Receipt3', {
    refresh: function(frm) {
        console.log("Purchase Receipt - Refresh triggered");
        update_po_pi_from_first_item(frm);
    },
    
    onload: function(frm) {
        console.log("Purchase Receipt - Onload triggered");
        update_po_pi_from_first_item(frm);
    },
    
    before_save: function(frm) {
        console.log("Purchase Receipt - Before Save triggered");
        update_po_pi_from_first_item(frm);
    },
    
    items_on_form_rendered: function(frm) {
        console.log("Purchase Receipt - Items form rendered");
        update_po_pi_from_first_item(frm);
    }
});

frappe.ui.form.on('Purchase Receipt Item', {
    items_add: function(frm, cdt, cdn) {
        console.log("Item added to Purchase Receipt");
        setTimeout(function() {
            update_po_pi_from_first_item(frm);
        }, 500);
    },
    
    items_remove: function(frm, cdt, cdn) {
        console.log("Item removed from Purchase Receipt");
        setTimeout(function() {
            update_po_pi_from_first_item(frm);
        }, 500);
    },
    
    purchase_order: function(frm, cdt, cdn) {
        console.log("Purchase Order changed in Purchase Receipt item");
        update_po_pi_from_first_item(frm);
    },
    
    purchase_invoice: function(frm, cdt, cdn) {
        console.log("Purchase Invoice changed in Purchase Receipt item");
        update_po_pi_from_first_item(frm);
    }
});

// ===== HELPER FUNCTION =====
function update_po_pi_from_first_item(frm) {
    console.log("🔄 === update_po_pi_from_first_item called ===");
    
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
            purchase_invoice: first_item.purchase_invoice
        });
        
        // Update custom_purchase_order
        let po_value = first_item.purchase_order || '';
        console.log("🔗 Setting custom_purchase_order to:", po_value);
        
        // Update custom_purchase_invoice  
        let pi_value = first_item.purchase_invoice || '';
        console.log("📄 Setting custom_purchase_invoice to:", pi_value);
        
        // Set values with error handling
        try {
            frm.set_value('custom_purchase_order', po_value);
            frm.set_value('custom_purchase_invoice', pi_value);
            console.log("✅ Values set successfully");
            
            // Show user notification if values were populated
            if (po_value || pi_value) {
                frappe.show_alert({
                    message: `Updated: PO: ${po_value || 'None'}, PI: ${pi_value || 'None'}`,
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
            frm.set_value('custom_purchase_invoice', '');
            console.log("✅ Fields cleared");
        } catch (error) {
            console.error("❌ Error clearing fields:", error);
        }
    }
    
    console.log("🏁 === End of update function ===");
}

console.log("✅ Purchase Receipt View Enhancements Loaded");
