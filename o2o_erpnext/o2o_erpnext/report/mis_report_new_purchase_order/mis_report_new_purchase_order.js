// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["MIS Report New Purchase Order"] = {
    "filters": [
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "default": frappe.defaults.get_user_default("Company"),
            "reqd": 1
        },
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
            "reqd": 1
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.get_today(),
            "reqd": 1
        },
        {
            "fieldname": "supplier",
            "label": __("Supplier"),
            "fieldtype": "Link",
            "options": "Supplier"
        },
        {
            "fieldname": "branch",
            "label": __("Branch"),
            "fieldtype": "Link",
            "options": "Branch"
        },
        {
            "fieldname": "status",
            "label": __("Status"),
            "fieldtype": "Select",
            "options": "\nAwaiting Approval\nApproved\nRejected\nCancelled"
        }
    ],
    
    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        
        // Status color coding
        if (column.fieldname == "status") {
            if (value === "Approved") {
                value = `<span style="color: green; font-weight: bold;">${value}</span>`;
            } else if (value === "Awaiting Approval") {
                value = `<span style="color: orange; font-weight: bold;">${value}</span>`;
            } else if (value === "Rejected" || value === "Cancelled") {
                value = `<span style="color: red; font-weight: bold;">${value}</span>`;
            }
        }
        
        // Currency formatting with color coding for high values
        if (column.fieldtype === "Currency" && column.fieldname === "total") {
            if (data.total > 100000) {
                value = `<span style="color: #d73527; font-weight: bold;">${value}</span>`;
            } else if (data.total > 50000) {
                value = `<span style="color: #ff8c00; font-weight: bold;">${value}</span>`;
            }
        }
        
        // Highlight overdue orders
        if (column.fieldname == "required_by" && data.required_by) {
            let required_date = new Date(data.required_by);
            let today = new Date();
            if (required_date < today && data.status !== "Approved") {
                value = `<span style="color: red; font-weight: bold;">${value}</span>`;
            }
        }
        
        return value;
    },
    
    "onload": function(report) {
        // Add custom buttons
        report.page.add_inner_button(__("Export to Excel"), function() {
            frappe.utils.csv_to_excel(frappe.query_report.get_data_for_csv(), __("Purchase Order MIS Report"));
        });
        
        report.page.add_inner_button(__("Create Purchase Receipt"), function() {
            let selected_items = frappe.query_report.datatable.rowmanager.getCheckedRows();
            if (selected_items.length === 0) {
                frappe.msgprint(__("Please select at least one Purchase Order"));
                return;
            }
            
            let purchase_orders = selected_items.map(item => 
                frappe.query_report.data[item].purchase_order
            );
            
            // Create new Purchase Receipt with selected POs
            frappe.new_doc("Purchase Receipt", {
                "purchase_orders": purchase_orders.join(", ")
            });
        });
        
        report.page.add_inner_button(__("Bulk Approve"), function() {
            let selected_items = frappe.query_report.datatable.rowmanager.getCheckedRows();
            if (selected_items.length === 0) {
                frappe.msgprint(__("Please select at least one Purchase Order"));
                return;
            }
            
            let pending_orders = selected_items.filter(item => 
                frappe.query_report.data[item].status === "Awaiting Approval"
            ).map(item => frappe.query_report.data[item].purchase_order);
            
            if (pending_orders.length === 0) {
                frappe.msgprint(__("No pending orders selected for approval"));
                return;
            }
            
            frappe.confirm(
                __("Are you sure you want to approve {0} Purchase Orders?", [pending_orders.length]),
                function() {
                    frappe.call({
                        method: "o2o_erpnext.api.purchase_order.bulk_approve_orders",
                        args: {
                            "purchase_orders": pending_orders
                        },
                        callback: function(r) {
                            if (r.message) {
                                frappe.msgprint(__("Successfully approved {0} Purchase Orders", [r.message.approved_count]));
                                frappe.query_report.refresh();
                            }
                        }
                    });
                }
            );
        });
    },
    
    "get_datatable_options": function(options) {
        return Object.assign(options, {
            checkboxColumn: true,
            events: {
                onCheckRow: function(data) {
                    // Custom logic when rows are selected
                }
            }
        });
    }
};
