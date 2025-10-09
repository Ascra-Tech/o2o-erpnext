# O2O ERPNext Bidirectional Sync

A comprehensive Frappe app providing **bidirectional synchronization** between ERPNext Purchase Invoices and ProcureUAT (CodeIgniter) invoice system with SSH tunneling support.

## 🚀 Features

- ✅ **Bidirectional Synchronization**: Automatic sync between ERPNext and ProcureUAT
- ✅ **SSH Tunnel Support**: Secure database connections via SSH tunneling
- ✅ **Vendor/Supplier Mapping**: Intelligent mapping between systems
- ✅ **Payment Status Sync**: Real-time payment status synchronization
- ✅ **GST/Tax Calculation Mapping**: Comprehensive tax handling
- ✅ **Conflict Detection & Resolution**: Smart handling of data conflicts
- ✅ **Comprehensive Error Logging**: Detailed sync logs and error tracking
- ✅ **Manual Sync Utilities**: Force sync and bulk operations
- ✅ **Invoice Cancellation Support**: Proper handling of cancelled invoices
- ✅ **Automated Cleanup**: Scheduled cleanup of old sync logs

## 📋 System Requirements

- **Frappe Framework**: v14.x or higher
- **ERPNext**: v14.x or higher
- **Python**: 3.10+
- **MySQL/MariaDB**: 5.7+ (for ProcureUAT database)
- **pymysql**: 1.0.0+

## 🏗️ Architecture

```
┌─────────────────────┐         ┌──────────────────────┐
│   ERPNext System    │◄───────►│  ProcureUAT System   │
│  (Frappe Framework) │  Sync   │   (CodeIgniter)      │
└─────────────────────┘         └──────────────────────┘
         │                                 │
         ▼                                 ▼
┌─────────────────────┐         ┌──────────────────────┐
│  Purchase Invoice   │         │   invoices table     │
│     DocType         │         │   vendors table      │
└─────────────────────┘         └──────────────────────┘
         │
         ▼
┌─────────────────────┐
│ Invoice Sync Log    │
│     DocType         │
└─────────────────────┘
```

## 🚀 Quick Start

### Installation
```bash
cd ~/frappe-bench
bench get-app o2o_erpnext https://github.com/1byZero/o2o-erpnext
bench --site your-site install-app o2o_erpnext
```

### Setup Custom Fields
```bash
bench --site your-site console
>>> from o2o_erpnext.setup.custom_fields import install_custom_fields
>>> install_custom_fields()
>>> exit()
```

### Configure Database Connection
Create a **Database Connection** record:
- Connection Name: `ProcureUAT`
- Host: `65.0.222.210`
- Database: `procureuat`
- Username: `erpnext_sync`
- Password: `SecurePass2025!@#`

### Test Connection
```bash
bench --site your-site console
>>> from o2o_erpnext.sync.sync_utils import test_database_connection
>>> test_database_connection()
>>> exit()
```

## 🔧 Usage Examples

### Test Database Connection
```python
from o2o_erpnext.sync.sync_utils import test_database_connection
result = test_database_connection()
```

### Force Sync Specific Invoice
```python
from o2o_erpnext.sync.sync_utils import manual_sync_invoice_to_external
result = manual_sync_invoice_to_external('PINV-2025-00001')
```

### Bulk Sync from External
```python
from o2o_erpnext.sync.sync_utils import bulk_sync_from_external
result = bulk_sync_from_external(from_date='2025-01-01', limit=50)
```

## 📅 Scheduled Jobs

| Frequency | Function | Purpose |
|-----------|----------|---------|
| **Hourly** | `scheduled_sync_from_external` | Sync new/modified invoices from ProcureUAT |
| **Weekly** | `scheduled_cleanup_logs` | Clean up old successful sync logs |

## 📚 Documentation

- **[Complete Documentation](o2o%20Research/BIDIRECTIONAL_SYNC_DOCUMENTATION.md)** - Comprehensive guide
- **[Installation Guide](o2o_erpnext/setup/INSTALLATION_GUIDE.md)** - Step-by-step setup
- **[Database Schema](o2o%20Research/procureuat_db_schema.md)** - ProcureUAT database structure

## 🔍 Troubleshooting

### Common Issues

1. **SSH Connection Failed**
   - Check PEM file permissions: `chmod 400 o2o-uat-lightsail.pem`
   - Verify server connectivity

2. **Database Connection Failed**
   - Verify credentials in Database Connection record
   - Check firewall settings

3. **Sync Failures**
   - Review Invoice Sync Log for error details
   - Check vendor/supplier mappings

### Useful Commands
```bash
# Check scheduler status
bench --site your-site doctor

# View logs
tail -f ~/frappe-bench/logs/scheduler.log

# Restart services
bench restart
```

## Contributing
We welcome contributions! Please read our contributing guidelines before submitting pull requests.

## Support
For support and questions, please [open an issue](https://github.com/1byZero/o2o-erpnext/issues)

## License
This project is licensed under the MIT License - see the LICENSE file for details.

## Version History
- v2.0.0 - Latest release with major updates
- v1.0.2 - Previous stable release