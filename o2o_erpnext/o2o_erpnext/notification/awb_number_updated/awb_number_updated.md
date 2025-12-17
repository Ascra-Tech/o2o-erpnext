Dear Sir/Madam,<br>
Please be informed the following purchase requisition has beedn updated by AWB number & shipping details.<br>
To raise a fresh request please check https://new.o2op2p.ind.in/app<br>
<table border=2 >
    <tr align="center">
        <th>Sr. No.</th>
        <th>PR No</th>
        <th>AWB Number</th>
        <th>Remark</th>
    </tr>
    <tr align="center">
        <td>1</td>
        <td>{{ doc.items[0].purchase_order if doc.items else "" }}</td>
        <td>{{ doc.custom_awb_number }}</td>
        <td>{{ doc.remarks }}</td>
    </tr>
</table>