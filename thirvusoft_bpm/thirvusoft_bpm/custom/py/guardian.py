import frappe
@frappe.whitelist()
def update_student_table(name):
    if name:
        gd_doc = frappe.get_doc("Guardian",name)
        gd_doc.ts_students = []
        students = frappe.get_all("Student Guardian", filters={"guardian": gd_doc.name}, fields=["parent"])
        frappe.db.sql('''delete from `tabTS Student Guardian` where parent= '{0}' '''.format(gd_doc.name))
        for student in students:
            gd_doc.append("ts_students",
                {
                    "student": student.parent,
                    "student_name": frappe.db.get_value("Student", student.parent, "student_name"),
                }
            )
        # gd_doc.update({'ts_students':table_list})
        gd_doc.save()
        gd_doc.reload()
    return 1
        
