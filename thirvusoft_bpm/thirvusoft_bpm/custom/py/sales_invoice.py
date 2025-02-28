import frappe
import json
from frappe.utils import flt, cint
from erpnext.controllers.accounts_controller import (
    get_advance_journal_entries,
    get_advance_payment_entries_for_regional,
)
from thirvusoft_bpm.thirvusoft_bpm.custom.py.payment_request import custom_make_payment_request

@frappe.whitelist()
def trigger_bulk_message(list_of_docs):
    list_of_docs = json.loads(list_of_docs)
    frappe.enqueue(create_payment_request, list_of_docs=list_of_docs)
    frappe.msgprint("Payment Request Will Be Created in the Background Within 20 Minutes.")

@frappe.whitelist()
def update_advance(list_of_docs, accounts):
    list_of_docs = json.loads(list_of_docs)
    accounts = [i.get('account') for i in json.loads(accounts)]
    
    for invoice in list_of_docs:
        doc = frappe.get_doc("Sales Invoice", invoice)
        set_advances(doc, accounts)
        doc.save()

def create_payment_request(list_of_docs=None):
    if not list_of_docs:
        return False

    update_dict = {}

    # Create Bulk Transaction Log
    new_transaction = frappe.new_doc('Bulk Transaction Log')
    for invoice in list_of_docs:
        customer = frappe.db.get_value("Sales Invoice", invoice, "customer")
        student = frappe.db.get_value("Student", {"customer": customer}, "name")
        
        new_transaction.append('bulk_transaction_log_table', {
            'reference_doctype': "Sales Invoice",
            'reference_name': invoice,
            'student': student,
            'status': "Pending"
        })

    new_transaction.save()
    
    update_dict = {invoice: new_transaction.name for invoice in list_of_docs}

    # Process Each Invoice
    for invoice in list_of_docs:
        invoice_doc = frappe.get_doc("Sales Invoice", invoice)
        if not (invoice_doc.name and invoice_doc.student_email and invoice_doc.customer):
            continue
        
        pr_doc = custom_make_payment_request(
            dt="Sales Invoice",
            dn=invoice_doc.name,
            party_type="Customer",
            party=invoice_doc.customer,
            recipient_id=invoice_doc.student_email
        )

        if not pr_doc:
            continue

        doc = frappe.get_doc("Payment Request", pr_doc.name)
        doc.mode_of_payment = 'Gateway'
        doc.payment_request_type = 'Inward'
        doc.print_format = frappe.db.get_value(
            "Property Setter",
            dict(property="default_print_format", doc_type="Sales Invoice"),
            "value",
        )

        # Get Previous Outstanding Amount
        previous_outstanding_amount = get_outstanding_amount(
            invoice_doc.debit_to, invoice_doc.customer
        )

        doc.grand_total = invoice_doc.outstanding_amount
        doc.save(ignore_permissions=True)

        frappe.db.set_value(
            'Bulk Transaction Log Table',
            {'parent': update_dict[invoice], 'reference_doctype': 'Sales Invoice', 'reference_name': invoice},
            'status', 'Completed'
        )

    return True

@frappe.whitelist(allow_guest=True)
def guardian_emails(student):
    enrollments = frappe.get_all(
        "Program Enrollment",
        {"student": student},
        ["name", "program", "creation"],
        order_by='creation desc',
        page_length=1
    )

    emails = frappe.db.sql("""
        SELECT g.email_address AS student_emails
        FROM `tabStudent` s
        JOIN `tabStudent Guardian` sg ON sg.parent = s.name
        JOIN `tabGuardian` g ON sg.guardian = g.name
        WHERE s.name = %s AND s.enabled = 1
        GROUP BY g.name
    """, (student,), as_dict=1)

    concatenated_emails = ",".join([entry["student_emails"] for entry in emails if entry["student_emails"]])

    return {
        "program_enrollment": enrollments[0]["name"] if enrollments else "",
        "program": enrollments[0]["program"] if enrollments else "",
        "concatenated_emails": concatenated_emails
    }

def after_insert(doc, method=None):
    fetch_discount(doc)

def validate(doc, method=None):
    doc.custom_previous_outstanding_amount = get_outstanding_amount(
        doc.debit_to, doc.customer
    )
    doc.custom_net_payable = (doc.rounded_total + doc.custom_previous_outstanding_amount) - doc.total_advance

def fetch_discount(doc):
    if not doc.customer:
        return

    dis_doc = frappe.get_all("Discount", filters={"customer": doc.customer}, pluck="name")

    for item in doc.items:
        comp_dis = frappe.get_all(
            "Component Discount",
            filters={
                "parent": ["in", dis_doc],
                "start_date": ["<=", doc.posting_date],
                "end_date": [">=", doc.posting_date],
                "fee_components": item.item_code
            },
            pluck="discount_percentage",
            order_by="creation desc",
            limit=1
        )

        if comp_dis:
            item.discount_percentage = comp_dis[0]
            item.discount_amount = (item.rate / 100) * comp_dis[0]
            item.rate -= item.discount_amount
            item.amount = item.rate * item.qty

def get_outstanding_amount(account, party):
    """
    Fetch the correct outstanding balance from GL Entry.
    """
    outstanding_amount = frappe.db.sql("""
        SELECT SUM(debit_in_account_currency) - SUM(credit_in_account_currency)
        FROM `tabGL Entry`
        WHERE account = %s AND party = %s AND docstatus = 1
    """, (account, party))

    return flt(outstanding_amount[0][0]) if outstanding_amount and outstanding_amount[0][0] else 0.0

def set_advances(self, accounts):
    advances = get_advance_entries(self, accounts)

    self.set("advances", [])
    advance_allocated = 0

    for d in advances:
        amount = self.get("base_rounded_total") or self.base_grand_total
        allocated_amount = min(amount - advance_allocated, d.amount)
        advance_allocated += flt(allocated_amount)

        advance_row = {
            "doctype": self.doctype + " Advance",
            "reference_type": d.reference_type,
            "reference_name": d.reference_name,
            "reference_row": d.reference_row,
            "remarks": d.remarks,
            "advance_amount": flt(d.amount),
            "allocated_amount": allocated_amount,
            "ref_exchange_rate": flt(d.exchange_rate),
            "account": d.get("paid_from") or d.get("paid_to"),
        }

        self.append("advances", advance_row)

def get_advance_entries(self, accounts):
    party_type = "Customer" if self.doctype == "Sales Invoice" else "Supplier"
    party = self.customer if self.doctype == "Sales Invoice" else self.supplier
    amount_field = "credit_in_account_currency" if self.doctype == "Sales Invoice" else "debit_in_account_currency"
    order_field = "sales_order" if self.doctype == "Sales Invoice" else "purchase_order"
    order_doctype = "Sales Order" if self.doctype == "Sales Invoice" else "Purchase Order"

    party_accounts = [self.debit_to] + accounts
    order_list = list(set(d.get(order_field) for d in self.get("items") if d.get(order_field)))

    journal_entries = get_advance_journal_entries(
        party_type, party, party_accounts, amount_field, order_doctype, order_list, include_unallocated=True
    )

    payment_entries = get_advance_payment_entries_for_regional(
        party_type, party, party_accounts, order_doctype, order_list, include_unallocated=True
    )

    return journal_entries + payment_entries

