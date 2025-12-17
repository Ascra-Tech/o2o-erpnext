Dear Sir/Madam,<br><br>
Please be informed that the following purchase receipt has been approved and the consignment will be delivered shortly.<br><br>

<table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width: 100%;">
    <tr style="background-color: #f0f0f0; text-align: center; font-weight: bold;">
        <th>Sr. No.</th>
        <th>Date</th>
        <th>PR Number</th>
    </tr>
    <tr style="text-align: center;">
        <td>1</td>
        <td>{{ doc.get_formatted("posting_date") }}</td>
        <td>{{ doc.items[0].purchase_order if doc.items else "" }}</td>
    </tr>
</table>

<br>Thank you for your attention.<br><br>
Best regards,<br>
{{ doc.company }}