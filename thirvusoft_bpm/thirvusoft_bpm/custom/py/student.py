import frappe
from frappe import _
from thirvusoft_bpm.thirvusoft_bpm.custom.py.guardian import update_student_table
from education.education.doctype.student.student import Student

def validate_wapp_enable(doc,event):
    check = 0
    for i in doc.guardians:
        update_student_table(i.guardian)
        if i.enable_whatsapp_message == 1:
            check = 1
            break
    # if check == 0:
    #     frappe.throw('Kindly enable atleast one guardian for Whatsapp Message')


### Override class because we need if customer is created then customer id equal to student id
class CustomStudent(Student):
    def create_customer(self):
        customer = frappe.get_doc(
            {
                "doctype": "Customer",
                "customer_name": self.student_name,
                "customer_group": self.customer_group
                or frappe.db.get_single_value("Selling Settings", "customer_group"),
                "customer_type": "Individual",
                "image": self.image,
                "name" : self.name
            }
        ).insert()

        frappe.db.set_value("Student", self.name, "customer", customer.name)
        frappe.msgprint(
            _("Customer {0} created and linked to Student").format(customer.name), alert=True
        )