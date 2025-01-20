frappe.ui.form.on('Branch', {
    setup: function(frm) {
        // Add query filter for supplier field
        frm.set_query('custom_supplier', function() {
            return {
                filters: {
                    'custom_user': frappe.session.user
                }
            };
        });
    },
    
    custom_supplier: function(frm) {
        if (!frm.doc.custom_supplier) return;
        
        if (frm.supplier_check_timeout) {
            clearTimeout(frm.supplier_check_timeout);
        }
        
        frm.supplier_check_timeout = setTimeout(() => {
            frappe.call({
                method: 'o2o_erpnext.o2o_erpnext.doctype.branch.branch.get_supplier_branch_info',
                args: {
                    supplier: frm.doc.custom_supplier
                },
                callback: function(response) {
                    const branch = response.message;
                    
                    if (branch && branch.name && branch.name !== frm.doc.name) {
                        frm.set_value('custom_supplier', '');
                        frappe.show_alert({
                            message: __('This supplier already has a branch (created on {0}). Please select a different supplier.',
                                [frappe.datetime.str_to_user(branch.creation)]),
                            indicator: 'red'
                        });
                    }
                }
            });
        }, 300);
    },
    
    refresh: function(frm) {
        if (frm.supplier_check_timeout) {
            clearTimeout(frm.supplier_check_timeout);
        }
    }
});