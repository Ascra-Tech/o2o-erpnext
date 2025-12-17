Dear Sir/Madam,<br>
Please be informed that that the following purchase requisition has been modified by the concerned authority as list below<br>
To raise the fresh request please click check the further details please click on https://o2op2p-demo.frappe.cloud/app

<p><b>Purchase Order</b>: {{ doc.name }}<br>
<b>Company</b>: {{ doc.company }}</p>

<h3>Original Request:</h3>
<table border=2 >
    <tr align="center">
        <th>Sr. No.</th>
        <th>Date</th>
        <th>PR No</th>
        <th>Product Name</th>
        <th>Quantity</th>
        <th>Amount</th>
    </tr>
    {% for item in doc.custom_purchasing_details_original %}
        {% if frappe.utils.flt(item.quantity, 2) > 0.0 %}
            <tr align="center">
                <td>{{ loop.index }}</td>
                <td>{% if item.required_by %}{{ item.required_by }}{% else %}{{ doc.get_formatted("schedule_date") }}{% endif %}</td>
                <td>{{ doc.name }}</td>
                <td>{{ item.item_name }}</td>
                <td>{{ frappe.utils.flt(item.quantity, 2) }}</td>
                <td>{{ item.amount }}</td>
            </tr>
        {% endif %}
    {% endfor %}
</table>
<h3>Modified Request:</h3>
<table border=2 >
    <tr align="center">
        <th>Sr. No.</th>
        <th>Date</th>
        <th>PR No</th>
        <th>Product Name</th>
        <th>Quantity</th>
        <th>Amount</th>
    </tr>
    {% for items in doc.items %}
        {% if frappe.utils.flt(items.qty, 2) > 0.0 %}
            <tr align="center">
                <td>{{ loop.index }}</td>
                <td>{{ items.get_formatted("schedule_date") }}</td>
                <td>{{ doc.name }}</td>
                <td>{{ items.item_name }}</td>
                <td>{{ frappe.utils.flt(items.qty, 2) }}</td>
                <td>{{ items.amount }}</td>
            </tr>
        {% endif %}
    {% endfor %}
</table>