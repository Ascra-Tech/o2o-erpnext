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
        // Custom onload functionality can be added here if needed
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
