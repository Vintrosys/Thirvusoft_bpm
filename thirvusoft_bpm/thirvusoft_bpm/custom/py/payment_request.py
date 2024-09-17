import frappe
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import quote
from erpnext.accounts.doctype.payment_request.payment_request import PaymentRequest
# from frappe.core.doctype.communication.email import get_attach_link
from frappe.utils.pdf import get_pdf
from frappe.utils.file_manager import save_file
from frappe.utils.background_jobs import enqueue

submit = False

class CustomPaymentRequest(PaymentRequest):
    def validate(self):
        super().validate()
        if self.reference_doctype == "Sales Invoice" and self.reference_name and self.is_new():
            self.set_gateway_account()     

    def get_message(self):
        """return message with payment gateway link"""
        if self.party_type == 'Student':
            context = {
                "doc": frappe.get_doc(self.reference_doctype, self.reference_name),
                "payment_url": self.payment_url,
                'student_balance':self.student_balance,
                'virtual_account':frappe.get_value('Student',self.party,'virtual_account') or "--"
            }
        elif self.party_type == 'Customer':
            context = {
                "doc": frappe.get_doc(self.reference_doctype, self.reference_name),
                "payment_url": self.payment_url,
                'student_balance':self.student_balance,
                'virtual_account':frappe.get_value(self.reference_doctype, self.reference_name,'virtual_account') or "--"
            }
        else:
            context = {
                "doc": frappe.get_doc(self.reference_doctype, self.reference_name),
                "payment_url": self.payment_url,
                'student_balance':self.student_balance,
            }
        if self.message:
            return frappe.render_template(self.message, context)

    def send_email(self):
        """send email with payment link"""
        if self.reference_doctype == "Fees" and self.reference_name:
            fees = frappe.db.get_value("Fees", {"name":self.reference_name}, "company")
            if fees:
                default_mail=frappe.db.get_value("Company", {"name":fees}, "default_email")
        if self.reference_doctype == "Sales Invoice" and self.reference_name:
            invoice = frappe.db.get_value("Sales Invoice", {"name":self.reference_name}, "company")
            if invoice:
                default_mail=frappe.db.get_value("Company", {"name":invoice}, "default_email")
        if not self.bulk_transaction:
            args = {
            "recipients": self.email_to,
            "sender": None,
            "bcc": default_mail or None,
            "subject": self.subject,
            "message": self.get_message(),
            "now": True,
            "attachments": [
                frappe.attach_print(
                        self.reference_doctype,
                        self.reference_name,
                        file_name=self.reference_name,
                        print_format=self.print_format,
                    )
                ],
            }
        else:
            args = {
            "recipients": self.email_to,
            "sender": None,
            "bcc": default_mail or None,
            "subject": self.subject,
            "message": self.get_message(),
            "now": True
            }
            
        email_args = args
        enqueue(method=frappe.sendmail, queue="short", timeout=300, is_async=True, **email_args)

    def set_gateway_account(self):
        company = frappe.db.get_value(self.reference_doctype,self.reference_name,"company")
        payment_gateway_aacount , payment_account , message = frappe.db.get_value("Payment Gateway Account",{"company":company},["name","payment_account","message"])
        self.payment_gateway_account = payment_gateway_aacount
        self.payment_account = payment_account 
        self.message = message


def get_advance_entries(doc,event):
    # if doc.party_type == "Student" and doc.party and frappe.db.get_value('Student',doc.party,'virtual_account'):
    #     doc.virtual_account  = frappe.db.get_value('Student',doc.party,'virtual_account')
    if doc.reference_doctype == 'Fees' and doc.reference_name:
        fees = frappe.get_doc('Fees',doc.reference_name)
        gl_entry = frappe.get_all('GL Entry',{'debit':['>',0],'is_cancelled':0,'credit':0,'party_type':doc.party_type,'party':doc.party,'against_voucher':doc.reference_name,'voucher_no':['!=',doc.reference_name]},['account','debit'])
        doc.advance_payments = []
        doc.total_advance_payment = 0
        fees.advance_payments = []
        fees.total_advance_payment = 0
        for entry in gl_entry:
            doc.append('advance_payments',{
                'account':entry['account'],
                'amount':entry['debit']
            })
            fees.append('advance_payments',{
                'account':entry['account'],
                'amount':entry['debit']
            })
            doc.total_advance_payment += entry['debit']
            fees.total_advance_payment += entry['debit']
        fees.save()
        invoice_doc = fees
    elif doc.reference_doctype == 'Sales Invoice' and doc.reference_name:
        invoice = frappe.get_doc('Sales Invoice',doc.reference_name)
        gl_entry = frappe.get_all('GL Entry',{'debit':['>',0],'is_cancelled':0,'credit':0,'party_type':doc.party_type,'party':doc.party,'against_voucher':doc.reference_name,'voucher_no':['!=',doc.reference_name]},['account','debit'])
        doc.advance_payments = []
        doc.total_advance_payment = 0
        invoice.advance_payments = []
        invoice.total_advance_payment = 0
        for entry in gl_entry:
            doc.append('advance_payments',{
                'account':entry['account'],
                'amount':entry['debit']
            })
            invoice.append('advance_payments',{
                'account':entry['account'],
                'amount':entry['debit']
            })
            doc.total_advance_payment += entry['debit']
            invoice.total_advance_payment += entry['debit']
        invoice.save()
        invoice_doc = invoice

    
    if doc.reference_doctype  in  ["Sales Invoice","Fees"]:
        #1.5 discount percentage
        if doc.grand_total > 0 and frappe.db.get_value('Company',invoice_doc.company,'charges_applicable') and not doc.without_charges:
            doc.without_charges = doc.grand_total
            doc.grand_total =  ( doc.without_charges * (frappe.db.get_value('Company',invoice_doc.company,'razorpay_charges')/100)) + doc.without_charges
        elif doc.grand_total > 0 and not frappe.db.get_value('Company',invoice_doc.company,'charges_applicable') and doc.without_charges:
            doc.grand_total =  doc.without_charges
        #Non Payment Message
        if doc.grand_total <= 0 and doc.payment_gateway_account:
            doc.message = frappe.db.get_value('Payment Gateway Account',doc.payment_gateway_account,'non_payment_message')
        elif doc.bulk_transaction:
            doc.message = frappe.db.get_value('Payment Gateway Account',doc.payment_gateway_account,'default_message_for_bulk_payment_remainder')


def background_submit(doc,event):
    global submit
    if not submit:
        frappe.msgprint('Submission has been moved to Background.. Kindly check after some time..')
        submit = True
    frappe.enqueue(whatsapp_message, doc=doc, queue="long")


def whatsapp_message(doc):
    if frappe.db.get_single_value('Whatsapp Settings','enable') == 1 and doc.reference_doctype == 'Fees' and doc.reference_name:
        html = CustomPaymentRequest.get_message(doc)
        v=(" ".join("".join(re.sub("\<[^>]*\>", "<br>",html ).split("<br>")).split(' ') ))
        v = v.replace('click here to pay', f'click here to pay: {doc.payment_url}')
        encoded_s = quote(v)

        guardians=frappe.db.sql(""" select phone_number,guardian_name from `tabStudent Guardian` md where enable_whatsapp_message = 1 and parent='{0}'""".format(doc.party),as_dict=1)
        instance_id =  frappe.db.get_single_value('Whatsapp Settings','instance_id')
        access_token =  frappe.db.get_single_value('Whatsapp Settings','access_token')
        company = frappe.get_value('Fees',doc.reference_name,'company')

        for i in guardians:
            def_message  = frappe.db.get_value('Payment Gateway Account',{'company':company,'is_default':1},'default_header_for_whatsapp_mail_message')
            def_context = {
                'doc':frappe.get_doc('Student',doc.party),
                'guardian':i['guardian_name']
            }
                
            html2 = frappe.render_template(def_message, def_context)
            def_v =(" ".join("".join(re.sub("\<[^>]*\>", "<br>",html2 ).split("<br>")).split(' ') ))


            fees_doc  = frappe.get_doc('Fees',doc.reference_name)
            pdf_bytes = frappe.get_print(doc.reference_doctype, doc.reference_name, doc=fees_doc, print_format=doc.print_format)
            pdf_name = doc.reference_name + '.pdf'
            pdf_url = frappe.utils.file_manager.save_file(pdf_name, get_pdf(pdf_bytes), doc.doctype, doc.name)           
            urls = f'https://{frappe.local.site}{pdf_url.file_url}'
            try:
                if urls and i["phone_number"]:
                    mobile_number = i["phone_number"].replace("+", "")
                    api_url = frappe.db.get_single_value('Whatsapp Settings','url')
                    if not doc.bulk_transaction:
                        url = f'{api_url}send.php?number=91{mobile_number}&type=media&message={def_v+encoded_s}&media_url={urls}&filename={pdf_name}&instance_id={instance_id}&access_token={access_token}'
                    else:
                        url = f'{api_url}send.php?number=91{mobile_number}&type=text&message={def_v+encoded_s}&instance_id={instance_id}&access_token={access_token}'
                    payload={}
                    headers = {}
                    response = requests.request("GET", url, headers=headers, data=payload)
                    #frappe.printerr(response.__dict__)
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
                    log_doc.reference_doctype = "Payment Request"
                    log_doc.reference_name = doc.name
                    log_doc.insert()
                frappe.delete_doc('File',pdf_url.name,ignore_permissions=True)
            except Exception as e:
                if urls and i["phone_number"]:
                    mobile_number = i["phone_number"].replace("+", "")
                    api_url = frappe.db.get_single_value('Whatsapp Settings','url')
                    if not doc.bulk_transaction:
                        url = f'{api_url}send.php?number=91{mobile_number}&type=media&message={def_v+encoded_s}&media_url={urls}&filename={pdf_name}&instance_id={instance_id}&access_token={access_token}'
                    else:
                        url = f'{api_url}send.php?number=91{mobile_number}&type=text&message={def_v+encoded_s}&instance_id={instance_id}&access_token={access_token}'
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
                    log_doc.reference_doctype = "Payment Request"
                    log_doc.reference_name = doc.name
                    log_doc.insert()
                frappe.delete_doc('File',pdf_url.name,ignore_permissions=True)