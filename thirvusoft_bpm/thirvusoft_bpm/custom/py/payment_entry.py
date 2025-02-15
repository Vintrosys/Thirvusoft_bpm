import frappe
from erpnext.accounts.doctype.payment_request.payment_request import PaymentRequest
from bs4 import BeautifulSoup
import re
from urllib.parse import quote
# from frappe.core.doctype.communication.email import get_attach_link
import requests
from frappe.utils.file_manager import save_file
from frappe.utils.pdf import get_pdf
from frappe.utils.background_jobs import enqueue
from erpnext.accounts.doctype.payment_entry.payment_entry import PaymentEntry
from hrms.overrides.employee_payment_entry import EmployeePaymentEntry

class CustomPayment(EmployeePaymentEntry):
    def validate_transaction_reference(self):
        bank_account = self.paid_to if self.payment_type == "Receive" else self.paid_from
        bank_account_type = frappe.db.get_value("Account", bank_account, "account_type")

        # if bank_account_type == "Bank":
        # 	if not self.reference_no or not self.reference_date:
        # 		frappe.throw(_("Reference No and Reference Date is mandatory for Bank transaction"))

def update_letter_head(doc,event):
    doc.letter_head = frappe.get_value('Payment Letter Head',{'parent':doc.company,'party_type':doc.party_type},'letter_head')
    
@frappe.whitelist()
def send_message_confirmation(doc,event):
    for ref in doc.references:
        if ref.reference_doctype == 'Fees' and ref.reference_name and frappe.db.get_value('Company',doc.company,'enable_payment_confirmation_message') ==1:
            def_v = ''
            encoded_s = ''
            html = ''
            html2 = ''
            fees_doc = frappe.get_doc('Fees',ref.reference_name)

            message  = frappe.db.get_value('Payment Gateway Account',{'company':doc.company,'is_default':1},'confirmation_message')
            if message:
                context = {
                    'doc':doc
                }
                
                html = frappe.render_template(message, context)
                v=(" ".join("".join(re.sub("\<[^>]*\>", "<br>",html ).split("<br>")).split(' ') ))
                encoded_s = quote(v)

            guardians=frappe.db.sql(""" select phone_number,guardian_name from `tabStudent Guardian` md where enable_whatsapp_message = 1 and parent='{0}'""".format(doc.party),as_dict=1)
            instance_id =  frappe.db.get_single_value('Whatsapp Settings','instance_id')
            access_token =  frappe.db.get_single_value('Whatsapp Settings','access_token')
            default_print_format = frappe.db.get_value(
                    "Property Setter",
                    dict(property="default_print_format", doc_type=doc.doctype),
                    "value",
                )
            for i in guardians:
                def_message  = frappe.db.get_value('Payment Gateway Account',{'company':fees_doc.company,'is_default':1},'default_header_for_whatsapp_mail_message')
                if def_message:
                    def_context = {
                        'doc':frappe.get_doc('Student',fees_doc.student),
                        'guardian':i['guardian_name']
                    }
                        
                    html2 = frappe.render_template(def_message, def_context)
                    def_v =(" ".join("".join(re.sub("\<[^>]*\>", "<br>",html2 ).split("<br>")).split(' ') ))

                pdf_bytes = frappe.get_print(doc.doctype, doc.name, doc=doc, print_format=default_print_format)
                pdf_name = doc.name + '.pdf'
                pdf_url = frappe.utils.file_manager.save_file(pdf_name, get_pdf(pdf_bytes), doc.doctype, doc.name)           
                urls = f'https://{frappe.local.site}{pdf_url.file_url}'
                try:
                    if urls and i["phone_number"] and frappe.db.get_single_value('Whatsapp Settings','enable') == 1:
                        mobile_number = i["phone_number"].replace("+", "")
                        api_url = frappe.db.get_single_value('Whatsapp Settings','url')
                        url = f'{api_url}send.php?number=91{mobile_number}&type=media&message={def_v + encoded_s}&media_url={urls}&filename={pdf_name}&instance_id={instance_id}&access_token={access_token}'
                        payload={}
                        headers = {}
                        response = requests.request("GET", url, headers=headers, data=payload)
                        log_doc = frappe.new_doc("Whatsapp Log")
                        log_doc.update({
                            "mobile_no": mobile_number,
                            
                            "status":"Success",
                            "payload": f"{url}",
                            "response" : response,
                            "last_execution": frappe.utils.now()
                        })
                        log_doc.flags.ignore_permissions = True
                        log_doc.flags.ignore_mandatory = True
                        log_doc.reference_doctype = "Payment Entry"
                        log_doc.reference_name = doc.name
                        log_doc.insert()
                    frappe.delete_doc('File',pdf_url.name,ignore_permissions=True)
                except Exception as e:
                    if urls and i["phone_number"] and frappe.db.get_single_value('Whatsapp Settings','enable') == 1:
                        mobile_number = i["phone_number"].replace("+", "")
                        api_url = frappe.db.get_single_value('Whatsapp Settings','url')
                        url = f'{api_url}send.php?number=91{mobile_number}&type=media&message={def_v + encoded_s}&media_url={urls}&filename={pdf_name}&instance_id={instance_id}&access_token={access_token}'
                        payload={}
                        headers = {}
                        log_doc = frappe.new_doc("Whatsapp Log")
                        log_doc.update({
                            "mobile_no": mobile_number,
                            
                            "status":"Failed",
                            "payload": f"{url}",
                            "response" : e,
                            "last_execution": frappe.utils.now()
                        })
                        log_doc.flags.ignore_permissions = True
                        log_doc.flags.ignore_mandatory = True
                        log_doc.reference_doctype = "Payment Entry"
                        log_doc.reference_name = doc.name
                        log_doc.insert()
                    frappe.delete_doc('File',pdf_url.name,ignore_permissions=True)

            final_msg = def_v + encoded_s
            final_msg.replace('%',' ')
            """send email with payment link"""
            default_mail=frappe.db.get_value("Company", {"name":doc.company}, "default_email")
            email_args = {
                "recipients": fees_doc.student_email,
                "sender": None,
                "bcc": default_mail or None,
                "subject": f'Payment Entry for {doc.name}',
                "message": html2 + html,
                "now": True,
                "attachments": [
                    frappe.attach_print(
                        doc.doctype,
                        doc.name,
                        file_name=doc.name,
                        print_format=default_print_format,
                    )
                ],
            }
            enqueue(method=frappe.sendmail, queue="short", timeout=300, is_async=True, **email_args)

    send_purchase_msg(doc)


# Supplier Whatsapp Message
def send_purchase_msg(doc):
    if doc.party_type == 'Supplier' and doc.party and frappe.db.get_single_value('Whatsapp Settings','enable') == 1 and frappe.db.get_single_value('Whatsapp Settings','enable_message_for_payment_entry') == 1:
        if not frappe.db.get_single_value('Whatsapp Settings','payment_entry'):
            frappe.throw("Kindly fill the Message Template for Payment Entry")
        else:   
            supplier_no = frappe.db.get_value('Supplier',doc.party,'mobile_no')
            def_v = ''
            encoded_s = ''
            html = ''
            html2 = ''
            instance_id =  frappe.db.get_single_value('Whatsapp Settings','instance_id')
            access_token =  frappe.db.get_single_value('Whatsapp Settings','access_token')
            default_print_format = frappe.db.get_value(
                    "Property Setter",
                    dict(property="default_print_format", doc_type=doc.doctype),
                    "value",
                )
            pay_message  = frappe.db.get_single_value('Whatsapp Settings','payment_entry')
            if pay_message:
                context = {
                    'doc':doc
                }
                
                html = frappe.render_template(pay_message, context)
                v=(" ".join("".join(re.sub("\<[^>]*\>", "<br>",html ).split("<br>")).split(' ') ))
                encoded_s = quote(v)


            pdf_bytes = frappe.get_print(doc.doctype, doc.name, doc=doc, print_format=default_print_format)
            pdf_name = doc.name + '.pdf'
            pdf_url = frappe.utils.file_manager.save_file(pdf_name, get_pdf(pdf_bytes), doc.doctype, doc.name)           
            urls = f'https://{frappe.local.site}{pdf_url.file_url}'               
            try:
                if urls and supplier_no:
                    mobile_number = supplier_no.replace("+", "")
                    api_url = frappe.db.get_single_value('Whatsapp Settings','url')
                    url = f'{api_url}send.php?number=91{mobile_number}&type=media&message={def_v + encoded_s}&media_url={urls}&filename={pdf_name}&instance_id={instance_id}&access_token={access_token}'
                    payload={}
                    headers = {}
                    response = requests.request("GET", url, headers=headers, data=payload)
                    
                    log_doc = frappe.new_doc("Whatsapp Log")
                    log_doc.update({
                        "mobile_no": mobile_number,
                        
                        "status":"Success",
                        "payload": f"{url}",
                        "response" : response,
                        "last_execution": frappe.utils.now()
                    })
                    log_doc.flags.ignore_permissions = True
                    log_doc.flags.ignore_mandatory = True
                    log_doc.reference_doctype = "Payment Entry"
                    log_doc.reference_name = doc.name
                    log_doc.insert()
                frappe.delete_doc('File',pdf_url.name,ignore_permissions=True)
            except Exception as e:
                if urls and supplier_no:
                    mobile_number = supplier_no.replace("+", "")
                    api_url = frappe.db.get_single_value('Whatsapp Settings','url')
                    url = f'{api_url}send.php?number=91{mobile_number}&type=media&message={def_v + encoded_s}&media_url={urls}&filename={pdf_name}&instance_id={instance_id}&access_token={access_token}'
                    payload={}
                    headers = {}
                    log_doc = frappe.new_doc("Whatsapp Log")
                    log_doc.update({
                        "mobile_no": mobile_number,
                        
                        "status":"Failed",
                        "payload": f"{url}",
                        "response" : e,
                        "last_execution": frappe.utils.now()
                    })
                    log_doc.flags.ignore_permissions = True
                    log_doc.flags.ignore_mandatory = True
                    log_doc.reference_doctype = "Payment Entry"
                    log_doc.reference_name = doc.name
                    log_doc.insert()
                frappe.delete_doc('File',pdf_url.name,ignore_permissions=True)
