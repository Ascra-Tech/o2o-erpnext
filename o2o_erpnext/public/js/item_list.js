frappe.listview_settings['Item'] = {
	add_fields: ['item_name', 'item_group', 'stock_uom', 'disabled'],
	hide_name_column: true,
	
	// Track state to prevent duplicate operations
	filter_initialized: false,
	supplier_value: null,
	
	get_indicator: function(doc) {
		if(doc.disabled) {
			return [__("Disabled"), "gray"];
		}
	},
	onload: function(listview) {
		// Store reference to listview
		this.listview = listview;
		
		// Add export button using Frappe's standard method
		add_export_button(listview);
		
		// Remove unwanted action buttons from toolbar
		listview.page.actions.find('[data-label="Print"],[data-label="Export"],[data-label="Assign%20To"],[data-label="Apply%20Assignment%20Rule"],[data-label="Add%20Tags"]').parent().parent().remove();
		
		// Hide ID column
		this.hideIDColumn();
		
		// Initialize supplier filter if needed
		const hasRelevantRole = this.hasSupplierRole() || this.hasApproverRole();
		
		if (!this.isAdministrator() && hasRelevantRole && !this.filter_initialized) {
			console.log("Initializing supplier filter for restricted user");
			this.initializeSupplierFilter();
		}
	},
	refresh: function(listview) {
		// Update listview reference
		this.listview = listview;
		
		// Hide unwanted menu items
		listview.page.menu.find('[data-label="User%20Permissions"]').parent().hide();
		listview.page.menu.find('[data-label="Role%20Permissions%20Manager"]').parent().hide();
		listview.page.menu.find('[data-label="Import"]').parent().hide();
		listview.page.menu.find('[data-label="Toggle%20Sidebar"]').parent().hide();
		listview.page.menu.find('[data-label="List%Settings"]').parent().hide();
		
		// Re-hide ID column on refresh
		this.hideIDColumn();
		
		// Re-initialize filter if not already done
		const hasRelevantRole = this.hasSupplierRole() || this.hasApproverRole();
		
		if (!this.isAdministrator() && hasRelevantRole && !this.filter_initialized) {
			this.initializeSupplierFilter();
		} else if (!this.isAdministrator() && hasRelevantRole && this.filter_initialized) {
			// Re-apply UI restrictions
			this.applyUIRestrictions();
		}
	},
	
	// ===== Supplier Filtering Functions =====
	
	isAdministrator: function() {
		// Check if current user is Administrator
		return frappe.user_roles.includes('Administrator');
	},
	
	hasSupplierRole: function() {
		// Check if user has Supplier role
		return frappe.user_roles.includes('Supplier');
	},
	
	hasApproverRole: function() {
		// Check if user has either Requisition Approver or PO Approver role
		return frappe.user_roles.includes('Requisition Approver') || 
		       frappe.user_roles.includes('PO Approver');
	},
	
	initializeSupplierFilter: function() {
		// Mark as initialized to prevent duplicate calls
		this.filter_initialized = true;
		
		var me = this;
		
		// Different supplier lookup logic based on role
		if (this.hasSupplierRole()) {
			// For Supplier role - Get supplier directly linked to user
			this.getSupplierFromUser();
		} else if (this.hasApproverRole()) {
			// For Approver roles - Get supplier through employee
			this.getSupplierFromEmployee();
		}
	},
	
	getSupplierFromUser: function() {
		var me = this;
		
		// Get the supplier linked to the current user
		frappe.call({
			method: 'frappe.client.get_value',
			args: {
				doctype: 'Supplier',
				filters: { 'custom_user': frappe.session.user },
				fieldname: ['name']
			},
			callback: function(r) {
				if (r.message && r.message.name) {
					me.supplier_value = r.message.name;
					console.log("Found supplier for current user:", me.supplier_value);
					
					// Apply filter for this supplier
					me.applySupplierFilter(me.supplier_value);
					
					// Show notification
					frappe.show_alert({
						message: __(`Showing items for your supplier account: ${me.supplier_value}`),
						indicator: 'blue'
					}, 5);
				} else {
					console.log("No supplier found linked to current user");
					frappe.show_alert({
						message: __('No supplier is linked to your user account.'),
						indicator: 'orange'
					}, 5);
				}
			}
		});
	},
	
	getSupplierFromEmployee: function() {
		var me = this;
		
		// First get the employee linked to the current user
		frappe.call({
			method: 'frappe.client.get_value',
			args: {
				doctype: 'Employee',
				filters: { 'user_id': frappe.session.user },
				fieldname: ['name', 'custom_supplier']
			},
			callback: function(r) {
				if (r.message && r.message.custom_supplier) {
					me.supplier_value = r.message.custom_supplier;
					console.log("Found supplier from employee record:", me.supplier_value);
					
					// Apply filter for this supplier
					me.applySupplierFilter(me.supplier_value);
					
					// Show notification
					frappe.show_alert({
						message: __(`Showing items for your associated supplier: ${me.supplier_value}`),
						indicator: 'blue'
					}, 5);
				} else {
					console.log("No supplier found linked to employee record");
					frappe.show_alert({
						message: __('No supplier is associated with your employee record.'),
						indicator: 'orange'
					}, 5);
				}
			}
		});
	},
	
	applySupplierFilter: function(supplier) {
		if (!supplier || !this.listview) return;
		
		var me = this;
		
		console.log("Applying supplier filter to Item list:", supplier);
		
		// Clear existing filters
		this.listview.filter_area.clear();
		
		// Add supplier filter using our custom server-side method
		this.fetchItemsForSupplier(supplier);
	},
	
	fetchItemsForSupplier: function(supplier) {
		var me = this;
		
		// Use our custom server-side method to get the items
		frappe.call({
			method: 'o2o_erpnext.api.item.get_items_for_supplier',
			args: {
				supplier: supplier
			},
			callback: function(r) {
				if (r.message && r.message.length > 0) {
					console.log(`Found ${r.message.length} items for supplier ${supplier}`);
					me.applyItemsFilter(r.message);
				} else {
					console.log(`No items found for supplier ${supplier}`);
					me.listview.filter_area.add([
						['Item', 'name', '=', 'NO_ITEMS_FOR_THIS_SUPPLIER']
					]);
					
					frappe.show_alert({
						message: __('No items found for your supplier.'),
						indicator: 'orange'
					}, 5);
				}
				
				me.applyUIRestrictions();
			}
		});
	},
	
	applyItemsFilter: function(items) {
		var me = this;
		
		if (!items || !items.length || !this.listview) return;
		
		// Apply the "in" filter for item codes
		this.listview.filter_area.add([
			['Item', 'name', 'in', items]
		]);
		
		// Override filter methods to maintain filter
		this.overrideFilterMethods(items);
	},
	
	overrideFilterMethods: function(items) {
		var me = this;
		var supplier = this.supplier_value;
		
		// Override the get method to ensure our filter always stays applied
		var originalGet = this.listview.filter_area.get;
		
		this.listview.filter_area.get = function() {
			var filters = originalGet.apply(this, arguments);
			
			// Check if our filter exists (either supplier filter or items filter)
			var hasItemsFilter = filters.some(function(f) {
				return (Array.isArray(f) && f[1] === 'name' && f[2] === 'in' && Array.isArray(f[3])) ||
				       (f.fieldname === 'name' && f.condition === 'in' && Array.isArray(f.value));
			});
			
			// If not, add it back to the filters array
			if (!hasItemsFilter && items && items.length) {
				filters.push(['Item', 'name', 'in', items]);
			}
			
			return filters;
		};
		
		// Override the clear method to prevent complete clearing
		var originalClear = this.listview.filter_area.clear;
		
		this.listview.filter_area.clear = function() {
			// Call original clear
			originalClear.apply(this, arguments);
			
			// Immediately re-add our filter without triggering refresh
			if (items && items.length) {
				this.filters.push({
					fieldname: 'name',
					label: 'Name',
					condition: 'in',
					value: items
				});
			} else {
				// Fallback to impossible filter if no items
				this.filters.push({
					fieldname: 'name',
					label: 'Name',
					condition: '=',
					value: 'NO_ITEMS_FOR_THIS_SUPPLIER'
				});
			}
		};
	},
	
	applyUIRestrictions: function() {
		// Add CSS to restrict UI
		if (!document.getElementById('item-restriction-style')) {
			var style = document.createElement('style');
			style.id = 'item-restriction-style';
			style.innerHTML = `
				.filter-selector, .filter-button, .tag-filters-area, .clear-filters { 
					display: none !important; 
				}
				.filter-box .filter-area { 
					pointer-events: none !important; 
				}
				.filter-tag .remove-filter {
					display: none !important;
				}
			`;
			document.head.appendChild(style);
		}
	},
	
	hideIDColumn: function() {
		// Method 1: Hide using CSS
		if (!document.getElementById('hide-item-id-column-style')) {
			var style = document.createElement('style');
			style.id = 'hide-item-id-column-style';
			style.innerHTML = `
				/* Hide ID column header */
				[data-doctype="Item"] .list-header-subject .list-row-col:nth-child(2),
				[data-doctype="Item"] .list-headers .list-row-col:nth-child(2) {
					display: none !important;
				}
				
				/* Hide ID column in rows */
				[data-doctype="Item"] .list-row .list-row-col:nth-child(2) {
					display: none !important;
				}
				
				/* Alternative selector for ID column */
				[data-doctype="Item"] [data-fieldname="name"] {
					display: none !important;
				}
			`;
			document.head.appendChild(style);
		}
		
		// Method 2: Hide using jQuery (as backup)
		setTimeout(function() {
			// Hide ID column header
			$('.list-headers .list-row-col').filter(function() {
				return $(this).text().trim() === 'ID';
			}).hide();
			
			// Hide ID values in rows
			$('[data-fieldname="name"]').hide();
			
			// Alternative: Hide by column index (ID is usually the 2nd column)
			$('.list-row-container .list-row').each(function() {
				$(this).find('.list-row-col:eq(1)').hide();
			});
		}, 100);
	}
};

/**
 * Add Export Items button to list view toolbar
 */
function add_export_button(listview) {
	if (!listview || !listview.page) {
		console.error('Invalid listview');
		return;
	}
	
	// Add button using Frappe's standard API
	listview.page.add_button(__('Export Items'), function() {
		export_items_dialog(listview);
	}, 'primary').addClass('btn-primary');
}

/**
 * Open dialog for selecting fields to export
 */
function export_items_dialog(listview) {
	// Get selected items
	const selected_items = listview.get_checked_items();
	
	if (!selected_items || selected_items.length === 0) {
		frappe.throw(__('Please select items first to export'));
		return;
	}
	
	// Fetch available fields
	frappe.call({
		method: 'o2o_erpnext.item_export.get_item_fields',
		callback: function(r) {
			if (r.message) {
				show_field_selection_dialog(selected_items, r.message);
			}
		},
		error: function(r) {
			frappe.msgprint(__('Error fetching fields. Please try again.'));
		}
	});
}

/**
 * Show the field selection dialog
 */
function show_field_selection_dialog(selected_items, fields_data) {
	// Track selected fields
	let selected_fields = new Set();
	
	// Create dialog HTML
	let html = `
		<div style="padding: 15px;">
			<div style="margin-bottom: 15px;">
				<h6 style="margin: 10px 0;">Quick Actions:</h6>
				<button class="btn btn-sm btn-default select-all-btn" style="margin: 5px 5px 5px 0;">
					<i class="fa fa-check"></i> Select All Fields
				</button>
				<button class="btn btn-sm btn-default select-mandatory-btn" style="margin: 5px 5px 5px 0;">
					<i class="fa fa-star"></i> Select Mandatory Fields
				</button>
				<button class="btn btn-sm btn-default unselect-all-btn" style="margin: 5px 5px 5px 0;">
					<i class="fa fa-times"></i> Unselect All
				</button>
			</div>
			
			<hr>
			
			<div style="margin-bottom: 15px;">
				<input type="text" class="field-search form-control" placeholder="Search fields..." style="margin-bottom: 10px;">
			</div>
			
			<div class="field-selection-container" style="max-height: 400px; overflow-y: auto; border: 1px solid #ddd; padding: 10px; border-radius: 4px;">
				<h6 style="margin-top: 0; margin-bottom: 10px; background: #f8f9fa; padding: 8px; margin: -10px -10px 10px -10px;">
					<strong>Mandatory Fields</strong>
				</h6>
				<div id="mandatory-fields">
	`;
	
	// Add mandatory fields
	fields_data.mandatory_fields.forEach(field => {
		html += create_field_checkbox(field, true);
	});
	
	html += `
				</div>
				
				<h6 style="margin-top: 15px; margin-bottom: 10px; background: #f8f9fa; padding: 8px; margin: -10px -10px 10px -10px;">
					<strong>Optional Fields</strong>
				</h6>
				<div id="optional-fields">
	`;
	
	// Add optional fields
	fields_data.optional_fields.forEach(field => {
		html += create_field_checkbox(field, false);
	});
	
	html += `
				</div>
			</div>
			
			<div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #ddd;">
				<p style="color: #666; font-size: 12px;">
					<strong>Items to export:</strong> ${selected_items.length} selected
				</p>
			</div>
		</div>
	`;
	
	// Create the dialog
	let dialog = new frappe.ui.Dialog({
		title: __('Export Items to Excel'),
		fields: [
			{
				fieldtype: 'HTML',
				fieldname: 'export_html',
				options: html
			}
		],
		primary_action_label: __('Export'),
		primary_action(d) {
			if (selected_fields.size === 0) {
				frappe.msgprint({
					title: __('No Fields Selected'),
					indicator: 'red',
					message: __('Please select at least one field to export.')
				});
				return;
			}
			
			// Perform export
			perform_export(selected_items, Array.from(selected_fields));
			d.hide();
		},
		secondary_action_label: __('Cancel'),
		secondary_action(d) {
			d.hide();
		}
	});
	
	dialog.show();
	
	// Setup event handlers after dialog is shown
	setTimeout(() => {
		const container = dialog.$wrapper.find('.field-selection-container');
		const search_input = dialog.$wrapper.find('.field-search');
		
		// Select All button
		dialog.$wrapper.find('.select-all-btn').click(function() {
			container.find('input[type="checkbox"]').prop('checked', true);
			container.find('input[type="checkbox"]').each(function() {
				selected_fields.add($(this).data('fieldname'));
			});
		});
		
		// Select Mandatory button
		dialog.$wrapper.find('.select-mandatory-btn').click(function() {
			container.find('input[type="checkbox"]').prop('checked', false);
			selected_fields.clear();
			$('#mandatory-fields input[type="checkbox"]').prop('checked', true);
			$('#mandatory-fields input[type="checkbox"]').each(function() {
				selected_fields.add($(this).data('fieldname'));
			});
		});
		
		// Unselect All button
		dialog.$wrapper.find('.unselect-all-btn').click(function() {
			container.find('input[type="checkbox"]').prop('checked', false);
			selected_fields.clear();
		});
		
		// Field checkbox change handler
		container.find('input[type="checkbox"]').change(function() {
			const fieldname = $(this).data('fieldname');
			if ($(this).is(':checked')) {
				selected_fields.add(fieldname);
			} else {
				selected_fields.delete(fieldname);
			}
		});
		
		// Search functionality
		search_input.on('keyup', function() {
			const search_term = $(this).val().toLowerCase();
			container.find('.field-checkbox-wrapper').each(function() {
				const label = $(this).find('label').text().toLowerCase();
				const fieldname = $(this).find('input').data('fieldname').toLowerCase();
				
				if (label.includes(search_term) || fieldname.includes(search_term)) {
					$(this).show();
				} else {
					$(this).hide();
				}
			});
		});
		
	}, 100);
}

/**
 * Create HTML for a single field checkbox
 */
function create_field_checkbox(field, is_mandatory) {
	const mandatory_badge = field.mandatory ? ' <span class="badge badge-warning" style="margin-left: 5px; font-size: 10px;">MANDATORY</span>' : '';
	const is_custom = field.is_custom ? ' <span class="badge" style="margin-left: 5px; font-size: 10px; background: #6c757d;">CUSTOM</span>' : '';
	
	return `
		<div class="field-checkbox-wrapper" style="padding: 8px; border-bottom: 1px solid #e9ecef;">
			<div style="display: flex; align-items: center;">
				<input type="checkbox" data-fieldname="${field.fieldname}" style="margin-right: 10px;">
				<div style="flex: 1;">
					<label style="margin: 0; cursor: pointer; display: inline;">
						<strong>${field.label}</strong>
						<span style="color: #666; font-size: 11px;">(${field.fieldname})</span>
						${mandatory_badge}
						${is_custom}
					</label>
					<div style="color: #999; font-size: 11px; margin-top: 2px;">
						Field Type: ${field.fieldtype}
					</div>
				</div>
			</div>
		</div>
	`;
}

/**
 * Perform the actual export
 */
function perform_export(selected_items, selected_fields) {
	frappe.call({
		method: 'o2o_erpnext.item_export.export_items_to_excel',
		args: {
			item_ids: JSON.stringify(selected_items),
			selected_fields: JSON.stringify(selected_fields)
		},
		freeze: true,
		freeze_message: __('Generating Excel file...'),
		callback: function(r) {
			if (r.message && r.message.status === 'success') {
				frappe.msgprint({
					title: __('Success'),
					indicator: 'green',
					message: __('Items exported successfully. Downloading file...')
				});
				
				// Trigger file download
				let download_url = frappe.urllib.get_full_url(
					"/api/method/o2o_erpnext.item_export.download_exported_file?" +
					"filename=" + encodeURIComponent(r.message.filename)
				);
				window.open(download_url);
			}
		},
		error: function(r) {
			console.log('Export error:', r);
		}
	});
}
