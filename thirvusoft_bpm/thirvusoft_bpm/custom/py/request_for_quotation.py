import frappe
import re
from urllib.parse import quote
# from frappe.core.doctype.communication.email import get_attach_link
import requests
from frappe.utils.file_manager import save_file
from frappe.utils.pdf import get_pdf

# Supplier Whatsapp Message
def send_purchase_msg(doc,event):
    if doc.doctype == 'Request for Quotation':
        field_check = 'request_for_quotation'
    for sup in doc.suppliers:
        if sup.supplier and frappe.db.get_single_value('Whatsapp Settings','enable') == 1 and frappe.db.get_single_value('Whatsapp Settings','enable_message_for_request_for_quotation') == 1:
            if not frappe.db.get_single_value('Whatsapp Settings',field_check):
                frappe.throw(f"Kindly fill the Message Template for {doc.doctype}")
            else:   
                supplier_no = frappe.db.get_value('Supplier',sup.supplier,'mobile_no')
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
                pay_message  = frappe.db.get_single_value('Whatsapp Settings',field_check)
                if pay_message:
                    context = {
                        'doc':doc,
                        'supplier':sup.supplier,
                        'supplier_name':sup.supplier_name
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
                        log_doc.reference_doctype = doc.doctype
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
                        log_doc.reference_doctype = doc.doctype
                        log_doc.reference_name = doc.name
                        log_doc.insert()
                    frappe.delete_doc('File',pdf_url.name,ignore_permissions=True)

