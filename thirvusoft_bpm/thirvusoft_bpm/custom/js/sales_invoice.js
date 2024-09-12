frappe.ui.form.on('Sales Invoice', {
    customer : function(frm){
        if (frm.doc.customer){
            frappe.db.get_value("Student",{"customer":frm.doc.customer,"enabled":1},["name","virtual_account"]).then( result => {
                if (result.message){
                    frm.set_value("student",result.message.name)
                    // frm.set_value("custom_virtual_account",result.message.virtual_account)
                    frm.refresh_fields(["student"])
                }
            })
        }
    },
    student : function(frm){
        if (frm.doc.student){
            guardian_emails(frm)
        }
    }
})


function guardian_emails(frm){
    frappe.call({
        method: "thirvusoft_bpm.thirvusoft_bpm.custom.py.sales_invoice.guardian_emails",
        args : {
            student : frm.doc.student
        },
        callback(r) {
            if (r.message)
                frm.set_value("student_email",r.message.concatenated_emails)
                frm.set_value("program_enrollment",r.message.program_enrollment)
                frm.set_value("program",r.message.program)
                frm.refresh_fields(["student_email","program_enrollment","program"])
        }

    })
}