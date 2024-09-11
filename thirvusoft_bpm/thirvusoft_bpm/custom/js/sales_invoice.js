frappe.ui.form.on('Sales Invoice', {
    customer : function(frm){
        if (frm.doc.customer){
            frappe.db.get_value("Student",{"customer":frm.doc.customer,"enabled":1},["name","virtual_account"]).then( result => {
                if (result.message){
                    frm.set_value("student",result.message.name)
                    frm.set_value("custom_virtual_account",result.message.virtual_account)
                    frm.refresh_fields(["student","custom_virtual_account"])
                }
            })
        }
    }
})