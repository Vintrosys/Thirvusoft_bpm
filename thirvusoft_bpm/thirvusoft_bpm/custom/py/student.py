import frappe
from thirvusoft_bpm.thirvusoft_bpm.custom.py.guardian import update_student_table
def validate_wapp_enable(doc,event):
    check = 0
    for i in doc.guardians:
        update_student_table(i.guardian)
        if i.enable_whatsapp_message == 1:
            check = 1
            break
    # if check == 0:
    #     frappe.throw('Kindly enable atleast one guardian for Whatsapp Message')



    
    