// Copyright (c) 2025, Ascratech LLP and contributors
// For license information, please see license.txt

frappe.query_reports["Profit and Loss Dashborad"] = {
	"filters": [

	]
};

// formatter: function (value, row, column, data, default_formatter) {
// 	value = default_formatter(value, row, column, data);

// 	if (column.fieldname === "name" && data && data.name) {
// 		// Link to open Purchase Order in the same tab:
// 		return `<a href="/app/purchase-order/${data.name}">${value}</a>`;

// 		// OR, if you want it in a new tab:
// 		// return `<a href="/app/purchase-order/${data.name}" target="_blank">${value}</a>`;
// 	}
// 	if (column.fieldname === "supplier" && data && data.supplier) {
// 		return `<a href="/app/supplier/${data.supplier}">${value}</a>`;
// 	}

// 	return value;
// }