from erpnext.controllers.accounts_controller import get_advance_journal_entries, get_advance_payment_entries_for_regional
import frappe
import json
from frappe.utils import flt, cint
from thirvusoft_bpm.thirvusoft_bpm.custom.py.payment_request import custom_make_payment_request
# from erpnext.accounts.doctype.payment_request.payment_request import make_payment_request

@frappe.whitelist()

def trigger_bulk_message(list_of_docs):
    list_of_docs = json.loads(list_of_docs)
    # frappe.enqueue(create_payment_request, list_of_docs = list_of_docs)
    create_payment_request(list_of_docs)
    frappe.msgprint("Payment Request Will Be Creating In Backgroud Within 20 Minutes.")

@frappe.whitelist()
def update_advance(list_of_docs, accounts):
    list_of_docs = json.loads(list_of_docs)
    accounts = [i.get('account') for i in json.loads(accounts)]
    for d in list_of_docs:
        doc = frappe.get_doc("Sales Invoice", d)
        set_advances(doc, accounts)
        doc.save()

    
def create_payment_request(list_of_docs=None):
    update_dict = {}
    if list_of_docs:
        new_transaction = frappe.new_doc('Bulk Transaction Log')
        for invoice in list_of_docs:
            customer = frappe.db.get_value("Sales Invoice",invoice,"customer")
            
            new_transaction.append('bulk_transaction_log_table',{
                'reference_doctype':"Sales Invoice",
                'reference_name':invoice,
                'student':frappe.db.get_value("Student",{"customer":customer},'name'),
                'status':"Pending"
            })
            new_transaction.save()
            update_dict.update({invoice:new_transaction.name})
       

    if list_of_docs:
        for invoice in list_of_docs:
            invoice_doc = frappe.get_doc("Sales Invoice",invoice)
            if (invoice_doc.name and invoice_doc.student_email and invoice_doc.customer):
                # doc= frappe.get_doc("Payment Request")
                pr_doc = custom_make_payment_request(dt="Sales Invoice",dn=invoice_doc.name,party_type= "Customer",party= invoice_doc.customer,recipient_id= invoice_doc.student_email)
                doc = frappe.get_doc("Payment Request",pr_doc.name)
                doc.mode_of_payment = 'Gateway'
                doc.payment_request_type = 'Inward'
                doc.print_format = frappe.db.get_value(
                    "Property Setter",
                    dict(property="default_print_format", doc_type="Sales invoice"),
                    "value",
                )
                # if doc.grand_total > 0:
                filters = {'customer':invoice_doc.customer,'outstanding_amount':['!=',0],'docstatus':1}
                if invoice_doc.name:
                    filters.update({'name':['!=',invoice_doc.name]})
                sum_ = frappe.get_all('Sales Invoice',filters,['sum(outstanding_amount) as sum'])
                previous_outstanding_amount = sum_[0].get('sum') if sum_ else 0
                # doc.grand_total += previous_outstanding_amount
                doc.grand_total = invoice_doc.outstanding_amount
                # doc.grand_total = invoice_doc.outstanding_amount
                doc.save(ignore_permissions = True)
                frappe.db.set_value('Bulk Transaction Log Table',{'parent':update_dict[invoice],'parentfield': "bulk_transaction_log_table",'reference_doctype':'Sales Invoice','reference_name':invoice},'status','Completed')
                name = frappe.get_doc('Bulk Transaction Log',new_transaction.name)
                name.save()
                    # doc.submit()
                
    return True

@frappe.whitelist(allow_guest = True)
def guardian_emails(student):
    concatenated_emails = ""
    enrollments = frappe.get_all("Program Enrollment",{"student":student},["name","program","creation"],order_by='creation desc',page_length=1)
    emails = frappe.db.sql("""select g.email_address as student_emails 
            from `tabStudent` s ,
            `tabStudent Guardian` sg,
            `tabGuardian` g 
            where s.name = '{student}' and s.enabled = 1 and 
            sg.parenttype = 'Student' and sg.parentfield = 'guardians' 
            and sg.parent = s.name and sg.guardian = g.name 
            group by g.name """.format(student = student),as_dict = 1)
    if emails:
        concatenated_emails = ",".join(
            [entry["student_emails"] for entry in emails if entry["student_emails"]])
    return {"program_enrollment" : enrollments[0]["name"] if enrollments else "","program":enrollments[0]["program"] if enrollments else "","concatenated_emails":concatenated_emails}       


def after_insert(doc, method=None):
    fetch_discount(doc)

def validate(doc, method=None):
    if doc.is_new():
        fetch_discount(doc)
    outstanding_amount = get_outstanding_amount(
        doc.doctype, doc.debit_to, doc.customer, "Customer"
    )
    doc.custom_previous_outstanding_amount = outstanding_amount
    doc.custom_net_payable = (doc.rounded_total + doc.custom_previous_outstanding_amount) - doc.total_advance


def fetch_discount(doc):
    if not doc.customer:
        return
    
    if not frappe.get_value("Company", doc.company, "custom_enable_discount"):
        return

    dis_doc = frappe.get_all("Discount", filters={"customer": doc.customer}, pluck="name")
    

    for item in doc.items:
        comp_dis = frappe.get_all("Component Discount",
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
            item.discount_amount = (item.rate/100)*comp_dis[0]
            item.rate = item.rate - item.discount_amount
            item.amount = item.rate*item.qty

def get_outstanding_amount(against_voucher_type, account, party, party_type):
	bal = flt(
		frappe.db.sql(
			"""
		select sum(debit_in_account_currency) - sum(credit_in_account_currency)
		from `tabGL Entry`
		where against_voucher_type=%s 
		and account = %s and party = %s and party_type = %s""",
			(against_voucher_type, account, party, party_type),
		)[0][0]
		or 0.0
	)

	return bal

def set_advances(self, accounts):
    res = get_advance_entries(
        self=self,
        accounts=accounts,
        include_unallocated=not cint(self, self.get("only_include_allocated_payments"))
    )

    self.set("advances", [])
    advance_allocated = 0
    for d in res:
        if self.get("party_account_currency") == self.company_currency:
            amount = self.get("base_rounded_total") or self.base_grand_total
        else:
            amount = self.get("rounded_total") or self.grand_total
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
        }
        if d.get("paid_from"):
            advance_row["account"] = d.paid_from
        if d.get("paid_to"):
            advance_row["account"] = d.paid_to

        self.append("advances", advance_row)

def get_advance_entries(self, accounts, include_unallocated=True):
    party_account = []
    if self.doctype == "Sales Invoice":
        party_type = "Customer"
        party = self.customer
        amount_field = "credit_in_account_currency"
        order_field = "sales_order"
        order_doctype = "Sales Order"
        party_account.append(self.debit_to)

    party_account.extend(
        accounts
    )

    order_list = list(set(d.get(order_field) for d in self.get("items") if d.get(order_field)))

    journal_entries = get_advance_journal_entries(
        party_type, party, party_account, amount_field, order_doctype, order_list, include_unallocated
    )

    payment_entries = get_advance_payment_entries_for_regional(
        party_type, party, party_account, order_doctype, order_list, include_unallocated
    )

    res = journal_entries + payment_entries

    return res