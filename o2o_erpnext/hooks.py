app_name = "o2o_erpnext"
app_title = "o2o ErpNext"
app_publisher = "Ascratech LLP"
app_description = "o2o App for ErpNext"
app_icon = "octicon octicon-file-directory"
app_color = "grey"
app_email = "amit@ascratech.com"
app_license = "GNU General Public License (v3)"

# Apps
# ------------------

# Required Apps
required_apps = ["frappe/erpnext"]


# Each item in the list will be shown as an app in the apps page

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/o2o_erpnext/css/o2o_erpnext.css"

# include js, css files in header of web template
# web_include_css = "/assets/o2o_erpnext/css/o2o_erpnext.css"
# web_include_js = "/assets/o2o_erpnext/js/o2o_erpnext.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "o2o_erpnext/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# Add server-side validation hooks


# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}

# Remove global include since we're using doctype_js now
# app_include_js = [
# 	"/assets/o2o_erpnext/js/purchase_invoice_sync.js",
# ]


# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "o2o_erpnext/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "o2o_erpnext.utils.jinja_methods",
# 	"filters": "o2o_erpnext.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "o2o_erpnext.install.before_install"
after_install = "o2o_erpnext.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "o2o_erpnext.uninstall.before_uninstall"
# after_uninstall = "o2o_erpnext.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "o2o_erpnext.utils.before_app_install"
# after_app_install = "o2o_erpnext.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "o2o_erpnext.utils.before_app_uninstall"
# after_app_uninstall = "o2o_erpnext.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "o2o_erpnext.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

override_doctype_class = {
    "Purchase Invoice": "o2o_erpnext.overrides.purchase_invoice.CustomPurchaseInvoice"
}

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# Scheduled Tasks
# ---------------



# Testing
# -------

# before_tests = "o2o_erpnext.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "o2o_erpnext.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "o2o_erpnext.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["o2o_erpnext.utils.before_request"]
# after_request = ["o2o_erpnext.utils.after_request"]

# Job Events
# ----------
# before_job = ["o2o_erpnext.utils.before_job"]
# after_job = ["o2o_erpnext.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"o2o_erpnext.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

fixtures = [
    #"Role",
    #"Role Profile",
    "Client Script",
    #"Server Script",
    #"Tax Category",
    "Workspace",
    #"Custom HTML Block",
    #Custom DocPerm",
    #"Workflow",
    #"Workflow State",
    #"Workflow Action",
    #"Print Format",
    #"Number Card",
    #"Report",
    #"Workflow Action Master",
    #"Module Profile",
]

# Document Events - Consolidated
# ---------------
# Hook on document methods and events

doc_events = {
    "Purchase Invoice": {
        "validate": [
            "o2o_erpnext.api.purchase_invoice_controller.validate_remote_duplicate_on_submit"
        ],
        "get_permission_query_conditions": "o2o_erpnext.api.purchase_invoice.get_permission_query_conditions",
        "has_permission": "o2o_erpnext.api.purchase_invoice.has_permission",
        # Automatic Push to Portal on Submit
        "on_submit": [
            "o2o_erpnext.api.purchase_invoice_controller.validate_remote_duplicate_on_submit",
            "o2o_erpnext.api.purchase_invoice_controller.create_remote_invoice_on_submit"
        ],
        "on_update_after_submit": "o2o_erpnext.sync.erpnext_to_external_updated.auto_push_invoice_on_submit"
        # "on_cancel": "o2o_erpnext.sync.erpnext_to_external_updated.handle_invoice_cancellation"  # Function not implemented yet
    },
    "Sales Order": {
        "validate": "o2o_erpnext.custom_sales_order.CustomSalesOrder.validate_delivery_date"
    },
    "Purchase Order": {
        "validate": "o2o_erpnext.api.purchase_order.validate_purchase_order_hook",
        # "on_submit": "o2o_erpnext.api.purchase_order.on_submit_purchase_order",  # Commented out - function doesn't exist
        "has_permission": "o2o_erpnext.api.purchase_order.has_permission"
    },
    "Purchase Receipt": {
        "get_permission_query_conditions": "o2o_erpnext.api.purchase_receipt.get_permission_query_conditions",
        "has_permission": "o2o_erpnext.api.purchase_receipt.has_permission"
    },
    "Sub Branch": {
        "get_permission_query_conditions": "o2o_erpnext.o2o_erpnext.doctype.sub_branch.sub_branch.get_permission_query_conditions",
        "has_permission": "o2o_erpnext.o2o_erpnext.doctype.sub_branch.sub_branch.has_permission",
        "get_list": "o2o_erpnext.o2o_erpnext.doctype.sub_branch.sub_branch.get_list"
    },
    "Supplier": {
        "after_insert": "o2o_erpnext.supplier_hooks.create_party_specific_item",
        # "before_delete": "o2o_erpnext.supplier_hooks.delete_party_specific_items"
    }
}

permission_query_conditions = {
    "Purchase Order": "o2o_erpnext.api.purchase_order.get_permission_query_conditions"
}



doctype_js = {
    "Branch": "o2o_erpnext/doctype/branch/branch.js",
    "Sub Branch": "o2o_erpnext/doctype/sub_branch/sub_branch.js",
    "Purchase Order": "public/js/purchase_order.js",
}

doctype_list_js = {
    "Purchase Invoice": [
        "public/js/purchase_invoice_list.js",
        "public/js/purchase_invoice_filters.js"
    ]
}

# Commands
# --------
commands = [
    "o2o_erpnext.commands.test_connection"
]

# Reports
# -------
reports = [
    {
        "doctype": "Purchase Order", 
        "name": "Supplier PO",
        "report_type": "Script Report",
        "module": "o2o ErpNext"
    }
]