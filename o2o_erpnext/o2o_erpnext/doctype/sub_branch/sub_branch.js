frappe.ui.form.on('Sub Branch', {
    refresh: function(frm) {
        // Add a custom button to view all linked employees
        frm.add_custom_button(__('View Linked Employees'), function() {
            frm.call({
                doc: frm.doc,
                method: 'get_employees',
                callback: function(r) {
                    if (r.message && r.message.length) {
                        // Create a dialog to show linked employees
                        let d = new frappe.ui.Dialog({
                            title: 'Employees in Sub Branch',
                            width: 800,
                            fields: [
                                {
                                    fieldname: 'employees_html',
                                    fieldtype: 'HTML'
                                }
                            ]
                        });
                        
                        // Create HTML table of employees
                        let html = '<div class="table-responsive"><table class="table table-bordered">';
                        html += '<thead><tr><th>Employee ID</th><th>Name</th><th>Department</th><th>Designation</th></tr></thead>';
                        html += '<tbody>';
                        
                        r.message.forEach(emp => {
                            html += `<tr>
                                <td><a href="/app/employee/${emp.name}">${emp.name}</a></td>
                                <td>${emp.employee_name || ''}</td>
                                <td>${emp.department || ''}</td>
                                <td>${emp.designation || ''}</td>
                            </tr>`;
                        });
                        
                        html += '</tbody></table></div>';
                        
                        d.fields_dict.employees_html.$wrapper.html(html);
                        d.show();
                    } else {
                        frappe.msgprint(__('No employees linked to this sub branch'));
                    }
                }
            });
        });
    }
});