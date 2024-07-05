import frappe
from thirvusoft_bpm.thirvusoft_bpm.custom.py.guardian import update_student_table
def validate_wapp_enable(doc,event):
    check = 0
    for i in doc.guardians:
        update_student_table(i.guardian)
        if i.enable_whatsapp_message == 1:
            check = 1
            break
    if check == 0:
        frappe.throw('Kindly enable atleast one guardian for Whatsapp Message')

def create_customer(doc,event):
    customer=frappe.new_doc("Customer")
    customer.customer_name=doc.first_name
    customer.customer_type="Individual"
    customer.save()
    address=frappe.new_doc("Address")
    address.address_line1=doc.address_line_1
    address.state=doc.city
    address.city=doc.state
    address.append("links",{
        "link_doctype":"customer",
        "link_name":customer.name,
        "link_title":customer.customer_name
    })
    address.save()
    
    