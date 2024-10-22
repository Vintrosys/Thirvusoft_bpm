import frappe
import json
from erpnext.accounts.doctype.payment_request.payment_request import make_payment_request

@frappe.whitelist()

def trigger_bulk_message(list_of_docs):
    list_of_docs = json.loads(list_of_docs)
    frappe.enqueue(create_payment_request, list_of_docs = list_of_docs)
    frappe.msgprint("Payment Request Will Be Creating In Backgroud Within 20 Minutes.")

    
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
                doc= frappe.new_doc("Payment Request")
                doc.update(make_payment_request(dt="Sales Invoice",dn=invoice_doc.name,party_type= "Customer",party= invoice_doc.customer,recipient_id= invoice_doc.student_email))
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
                doc.save()
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