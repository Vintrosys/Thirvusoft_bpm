frappe.listview_settings['Sales Invoice'] = {
    	add_fields: [
		"customer",
		"customer_name",
		"base_grand_total",
		"outstanding_amount",
		"due_date",
		"company",
		"currency",
		"is_return",
	],
	get_indicator: function (doc) {
		const status_colors = {
			Draft: "grey",
			Unpaid: "orange",
			Paid: "green",
			Return: "gray",
			"Credit Note Issued": "gray",
			"Unpaid and Discounted": "orange",
			"Partly Paid and Discounted": "yellow",
			"Overdue and Discounted": "red",
			Overdue: "red",
			"Partly Paid": "yellow",
			"Internal Transfer": "darkgrey",
		};
		return [__(doc.status), status_colors[doc.status], "status,=," + doc.status];
	},
	right_column: "grand_total",
    onload: function(list_view) {
        list_view.page.add_actions_menu_item(__("Bulk Payment Request"), function() {
            const selected_docs = list_view.get_checked_items();
            const list_of_docs = list_view.get_checked_items(true);
            for (let doc of selected_docs) {
                if (doc.docstatus !== 1) {
                    frappe.throw(__("Payment Request can only be generated from a submitted document"));
                }
            }
            console.log("list_of_docs",list_of_docs)
            frappe.confirm(__("Do you want to Trigger Bulk Payment Request?"),
            function() {
				frappe.call({
                    method:"thirvusoft_bpm.thirvusoft_bpm.custom.py.sales_invoice.trigger_bulk_message",
                    args:{
						'list_of_docs':list_of_docs
					},
					callback:function(frm){
                        // frappe.show_alert({message:__('Payment Request Created Successfully'), indicator:'green'});
                    }
                })
			},
			function() {
                console.log("Operation Aborted")
            }
        )
        })
		list_view.page.add_actions_menu_item(__("Set Advance"), function() {
            const selected_docs = list_view.get_checked_items();
            const list_of_docs = list_view.get_checked_items(true);
            for (let doc of selected_docs) {
                if (doc.docstatus != 0) {
                    frappe.throw(__("We can set Advance only for Draft Sales Invoice."));
                }
				if (selected_docs[0].company != doc.company){
					frappe.throw(__("Selected Sales Invoice much be in Same Company."));
				}
            }
			var data = [
				{
					"account": selected_docs[0].debit_to
				}
			]
			const dialog = new frappe.ui.Dialog({
				title: __("Select Multi-Advance Account"),
				fields: [
					{
						fieldname: "advance_account",
						fieldtype: "Table",
						label: __("Select Advance Account"),
						data: data,
						get_data: () => {
							return data;
						},
						fields: [
							{
								fieldtype: "Link",
								fieldname: "account",
								options: "Account",
								in_list_view: 1,
								label: "Account",
								get_query: () => {
									return {
										filters: {
											company: selected_docs[0].company,
											account_type: "Receivable",
											is_group: 0,
										},
									};
								},
							},
						],
					}	
				],
				primary_action: () => {
					const args = dialog.get_values()["advance_account"];
					frappe.call({
						method:"thirvusoft_bpm.thirvusoft_bpm.custom.py.sales_invoice.update_advance",
						args:{
							"list_of_docs": list_of_docs,
							"accounts": args
						},
						callback:function(frm){
							frappe.show_alert({message:__('Advance Updated Successfully'), indicator:'green'});
						}
					})
					dialog.hide();
				},
				primary_action_label: __("Update {0} records", [list_of_docs.length]),
			});
			dialog.show();
        })
    }
}