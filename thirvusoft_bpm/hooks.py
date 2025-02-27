from . import __version__ as app_version

app_name = "thirvusoft_bpm"
app_title = "Thirvusoft Bpm"
app_publisher = "BPM"
app_description = "BPM"
app_icon = "octicon octicon-file-directory"
app_color = "grey"
app_email = "thirvusoft@gmail.com"
app_license = "MIT"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/thirvusoft_bpm/css/thirvusoft_bpm.css"
# app_include_js = "/assets/thirvusoft_bpm/js/thirvusoft_bpm.js"

# include js, css files in header of web template
# web_include_css = "/assets/thirvusoft_bpm/css/thirvusoft_bpm.css"
# web_include_js = "/assets/thirvusoft_bpm/js/thirvusoft_bpm.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "thirvusoft_bpm/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
				"Fees" : "thirvusoft_bpm/custom/js/fees.js",
				"Company" : "thirvusoft_bpm/custom/js/company.js",
				"Guardian":"thirvusoft_bpm/custom/js/guardian.js",
				"Payment Entry":"thirvusoft_bpm/custom/js/payment_entry.js",
				"Sales Invoice": "thirvusoft_bpm/custom/js/sales_invoice.js"
			}
doctype_list_js = {
	"Fees" : "thirvusoft_bpm/custom/js/fees_list.js",
	"Sales Invoice":"thirvusoft_bpm/custom/js/sales_invoice_list.js"
	}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "thirvusoft_bpm.install.before_install"
# after_install = "thirvusoft_bpm.install.after_install"

after_migrate = "thirvusoft_bpm.thirvusoft_bpm.custom.py.customisation.payment_entry_customizations"

# Uninstallation
# ------------

# before_uninstall = "thirvusoft_bpm.uninstall.before_uninstall"
# after_uninstall = "thirvusoft_bpm.uninstall.after_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "thirvusoft_bpm.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
#	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
#	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

override_doctype_class = {
	"Payment Gateway Account": "thirvusoft_bpm.thirvusoft_bpm.custom.py.payment_gateway_account.Autoname",
    "Program Enrollment Tool": "thirvusoft_bpm.thirvusoft_bpm.custom.py.program_enrollment.CustomEnrollment",
	"Payment Entry": "thirvusoft_bpm.thirvusoft_bpm.custom.py.payment_entry.CustomPayment",
	'Payment Request': "thirvusoft_bpm.thirvusoft_bpm.custom.py.payment_request.CustomPaymentRequest",
	"Student" : "thirvusoft_bpm.thirvusoft_bpm.custom.py.student.CustomStudent"

}

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Payment Request": {
		"validate": "thirvusoft_bpm.thirvusoft_bpm.custom.py.payment_request.get_advance_entries",
		"on_submit":"thirvusoft_bpm.thirvusoft_bpm.custom.py.payment_request.background_submit"

	},
    "Fees": {
		"validate": "thirvusoft_bpm.thirvusoft_bpm.custom.py.fees.previous_outstanding_amount",
		"on_change": "thirvusoft_bpm.thirvusoft_bpm.custom.py.fees.previous_outstanding_amount",


	},
    "Journal Entry": {
		"on_submit": "thirvusoft_bpm.thirvusoft_bpm.custom.py.journal_entry.update_fees",
		"on_cancel": "thirvusoft_bpm.thirvusoft_bpm.custom.py.journal_entry.update_fees",

	},
    "Payment Entry": {
		"on_submit": "thirvusoft_bpm.thirvusoft_bpm.custom.py.payment_entry.on_submit",
		"validate":"thirvusoft_bpm.thirvusoft_bpm.custom.py.payment_entry.update_letter_head"

	},
	"Purchase Order": {
		"on_submit": "thirvusoft_bpm.thirvusoft_bpm.custom.py.purchase_order.send_purchase_msg",
	},
	"Request for Quotation": {
		"on_submit": "thirvusoft_bpm.thirvusoft_bpm.custom.py.request_for_quotation.send_purchase_msg",
	},
    "Student": {
	 	"validate": ["thirvusoft_bpm.thirvusoft_bpm.custom.py.student.validate_wapp_enable" 
                ]
	},
    "Sales Invoice": {
        # "after_insert": "thirvusoft_bpm.thirvusoft_bpm.custom.py.sales_invoice.after_insert",
        "validate": "thirvusoft_bpm.thirvusoft_bpm.custom.py.sales_invoice.validate",
	},
    "Integration Request": {
		"validate": "thirvusoft_bpm.thirvusoft_bpm.custom.py.integration_request.update_expiry_date",

	},
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
#	"all": [
#		"thirvusoft_bpm.tasks.all"
#	],
#	"daily": [
#		"thirvusoft_bpm.tasks.daily"
#	],
#	"hourly": [
#		"thirvusoft_bpm.tasks.hourly"
#	],
#	"weekly": [
#		"thirvusoft_bpm.tasks.weekly"
#	]
#	"monthly": [
#		"thirvusoft_bpm.tasks.monthly"
#	]
# }

# Testing
# -------

# before_tests = "thirvusoft_bpm.install.before_tests"

# Overriding Methods
# ------------------------------
#
override_whitelisted_methods = {
	# "frappe.desk.doctype.event.event.get_events": "thirvusoft_bpm.event.get_events"
	"erpnext.accounts.doctype.payment_request.payment_request.make_payment_request" : "thirvusoft_bpm.thirvusoft_bpm.custom.py.payment_request.custom_make_payment_request"
}
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
#	"Task": "thirvusoft_bpm.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]


# User Data Protection
# --------------------

user_data_fields = [
	{
		"doctype": "{doctype_1}",
		"filter_by": "{filter_by}",
		"redact_fields": ["{field_1}", "{field_2}"],
		"partial": 1,
	},
	{
		"doctype": "{doctype_2}",
		"filter_by": "{filter_by}",
		"partial": 1,
	},
	{
		"doctype": "{doctype_3}",
		"strict": False,
	},
	{
		"doctype": "{doctype_4}"
	}
]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
#	"thirvusoft_bpm.auth.validate"
# ]

fixtures = [
    {
        "doctype": "Server Script",
        "filters": [["name", "=", "Payment Entry Automation"]]  # Export only this script
    }
]
