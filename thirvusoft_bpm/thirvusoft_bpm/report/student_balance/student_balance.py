# Copyright (c) 2023, BPM and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	columns, data = get_columns(filters), get_data(filters)
	return columns, data


def get_columns(filters):
	columns = [
		{
			"label": _("Party"),
			"fieldtype": "Link",
			"fieldname": "party",
			"options":"Student",
			"width": 100
		},
		{
			"label": _("Party Name"),
			"fieldtype": "Data",
			"fieldname": "party_name",
			"width": 150
		},
		{
			"label": _("Voucher Type"),
			"fieldtype": "Link",
			"fieldname": "voucher_type",
			"options":"DocType",
			"width": 130,
			"hidden":1
		},
  		{
			"label": _("Year"),
			"fieldtype": "Link",
			"fieldname": "fiscal_year",
			'options':"Fiscal Year",
			"width": 100
		},
		{
			"label": _("Posting Date"),
			"fieldtype": "Date",
			"fieldname": "posting_date",
			"width": 130
		},
		{
			"label": _("Voucher No"),
			"fieldtype": "Dynamic Link",
			"fieldname": "voucher_no",
			"options":"voucher_type",
			"width": 150
		},
		{
			"label": _("Against Voucher Type"),
			"fieldtype": "Link",
			"fieldname": "against_voucher_type",
			"options":"DocType",
			"width": 100,
			"hidden":1
		},
		{
			"label": _("Against Voucher"),
			"fieldtype": "Dynamic Link",
			"fieldname": "against_voucher",
			"options":"against_voucher_type",
			"width": 150
		},
		
		{
			"label": _("Sum of Debit(INR)"),
			"fieldtype": "Currency",
			"fieldname": "debit",
			"width": 145
		},
		{
			"label": _("Sum of Credit(INR)"),
			"fieldtype": "Currency",
			"fieldname": "credit",
			"width": 145
		},
 		{
			"label": _("(Cr) Unallocated Amt"),
			"fieldtype": "Currency",
			"fieldname": "unallocated_amount",
			"width": 150
		},
		{
			"label": _("Balance (Dr - Cr)"),
			"fieldtype": "Currency",
			"fieldname": "net",
			"width": 130
		},
	]
	
	return columns

def get_data(filters):
	data = []
	conditions = ' gl.docstatus = 1 and gl.party_type = "Student"'

	if filters.get('company'):
		company = filters.get('company')
		conditions += f' and gl.company = "{company}"'

	if filters.get('from_fiscal_year'):
		from_fiscal_year = filters.get('from_fiscal_year')

	if filters.get('to_fiscal_year'):
		to_fiscal_year = filters.get('to_fiscal_year')
		
	if filters.get('account'):
		account = filters.get('account') 
		conditions += f' and gl.account = "{account}"'

	if filters.get('student'):
		student = filters.get('student')
		conditions += f' and gl.party = "{student}"'

	if from_fiscal_year and to_fiscal_year:
		start_date = frappe.get_value('Fiscal Year',from_fiscal_year,'year_start_date')
		end_date = frappe.get_value('Fiscal Year',to_fiscal_year,'year_end_date')

	sample_data = frappe.db.sql('''
                            select 
                            	gl.party as party,
                              	stud.first_name as party_name,
                               	gl.voucher_type,
                                gl.voucher_no,
                                gl.against_voucher_type,
                                GROUP_CONCAT(DISTINCT gl.against_voucher SEPARATOR ', ') as against_voucher,
        						gl.fiscal_year,
              					DATE_FORMAT(convert(gl.posting_date, char),'%Y-%m-%d') as posting_date,
                   				sum(gl.debit) as debit,
                       			sum(case when ifnull(gl.against_voucher, '')!='' then gl.credit else 0 end) as credit,
                          		(sum(gl.debit) - sum(gl.credit)) as net,
								sum(case when ifnull(gl.against_voucher, '')='' then gl.credit else 0 end) as unallocated_amount
                            from `tabGL Entry` as gl 
							left join `tabStudent` as stud on stud.name = gl.party 
							where 
								gl.is_cancelled = 0 and
								case 
        							when ifnull(gl.against_voucher, '') != ''
        								then (
											select 
												agn_vchr.docstatus
											from `tabFees` agn_vchr
											where
												agn_vchr.name = gl.against_voucher
											limit 1
										) = 1 
									else 1
          						end and
       							gl.posting_date between '{1}' and '{2}' 
								and {3}
							group by gl.voucher_no
       						order by 
								gl.party,
								CASE
									WHEN IFNULL(gl.debit, 0) != 0
										THEN 0
									ELSE 1
								END,
								gl.posting_date,
								gl.debit,
								gl.credit,
								gl.voucher_no
								
       '''.format(company,start_date,end_date,conditions),as_dict= True)
	# sample_data=[]
	# a=[]
	# a_debit, a_credit=[],[]
	# for  i in gl_data:
	# 	check = a[-1].get('party') if a else None
	# 	if check != i['party']:
	# 		a_debit=sorted(a_debit, key=lambda x: x['posting_date'])
	# 		a_credit=sorted(a_credit, key=lambda x: x['posting_date'])
	# 		sample_data.extend(a_credit+a_debit)
			
	# 		if i["credit"]:
	# 			a_credit=[i]
	# 		else:
	# 			a_debit=[i]
	# 	else:
	# 		if i["credit"]:
	# 			a_credit.append(i)
	# 		else:
	# 			a_debit.append(i)
	# 	a.append(i)
	# a_debit=sorted(a_debit, key=lambda x: x['posting_date'])
	# a_credit=sorted(a_credit, key=lambda x: x['posting_date'])
	# frappe.errprint([{"date":i["posting_date"]} for i in a_credit])
	# frappe.errprint([{"date":i["posting_date"]} for i in a_debit])
	# frappe.errprint(a_credit)
	# frappe.errprint(a_debit)
	# sample_data.extend(a_credit+a_debit)
	check = sample_data[0].get('party') if sample_data else None
	debit = 0
	credit = 0
	net = 0
	unallocated_amount = 0
	total_debit = 0
	total_credit = 0
	total_net = 0
	total_unallocated_amount = 0
	row_check = 0
	for i in sample_data:
		if check == i.get('party') and i != sample_data[-1]:
		
			if i != sample_data[0]:
				i.update({'party':""})

			debit+=i.get('debit') or 0
			credit+=i.get('credit') or 0
			net+=i.get('net') or 0
			unallocated_amount+=i.get("unallocated_amount") or 0

			total_debit +=i.get('debit') or 0
			total_credit +=i.get('credit') or 0
			total_net += i.get('net') or 0
			total_unallocated_amount+=i.get('unallocated_amount') or 0
			if not row_check and i.get('debit')>0:

				row_check = 1
			data.append(i)
		elif i == sample_data[-1]:
			party = i.get('party')
			i.update({'party':""})

			debit+=i.get('debit') or 0
			credit+=i.get('credit') or 0
			net+=i.get('net') or 0
			unallocated_amount+=i.get("unallocated_amount") or 0

			total_debit +=i.get('debit') or 0
			total_credit +=i.get('credit') or 0
			total_net += i.get('net') or 0
			total_unallocated_amount+=i.get('unallocated_amount') or 0

			data.append(i)
			check = party
			row_check = 0
			# fees_invoice = frappe.db.sql('''select fees.name as voucher_no
			# 						,fees.name as against_voucher,fy.name as fiscal_year
			# 						from `tabFees` as fees left join `tabFiscal Year` as fy
			# 						on fees.posting_date between fy.year_start_date and fy.year_end_date
			# 						where fees.student = '{0}' and fees.posting_date 
			# 						between '{1}' and '{2}' '''.format(party,start_date,end_date),as_dict=True)
			# data.append({'party':"<b></b>"})
			# data += fees_invoice
			data.append({'party':"<b>Result</b>",'debit':debit,'credit':credit,'net':net, 'unallocated_amount': unallocated_amount})
			data.append({'party':"<b>Total Result</b>",'debit':total_debit,'credit':total_credit,'net':total_net, 'unallocated_amount': total_unallocated_amount})
			credit = 0
			debit =0 
			net = 0
			unallocated_amount=0
		else:
			check = i.get('party')
			row_check = 0
			# debit+=i.get('debit') or 0
			# credit+=i.get('credit') or 0
			# net+=i.get('net') or 0

			total_debit +=i.get('debit') or 0
			total_credit +=i.get('credit') or 0
			total_net += i.get('net') or 0
			total_unallocated_amount+=i.get('unallocated_amount') or 0

			# fees_invoice = frappe.db.sql('''select fees.name as voucher_no
			# 			,fees.name as against_voucher,fy.name as fiscal_year
			# 			from `tabFees` as fees left join `tabFiscal Year` as fy
			# 			on fees.posting_date between fy.year_start_date and fy.year_end_date
			# 			where fees.student = '{0}' and fees.posting_date 
			# 			between '{1}' and '{2}' '''.format(i.get('party'),start_date,end_date),as_dict=True)
			# data += fees_invoice
			data.append({'party':"<b>Result</b>",'debit':debit,'credit':credit,'net':net, 'unallocated_amount': unallocated_amount})
			credit = i.get('credit') or 0
			unallocated_amount=i.get("unallocated_amount") or 0
			debit =i.get('debit')  or 0
			net = i.get('net') or 0
			data.append(i)
	return data

@frappe.whitelist()
def validate_to_date(from_fiscal_year,to_fiscal_year):
	end_date = frappe.get_value('Fiscal Year',to_fiscal_year,'year_end_date')
	start_date = frappe.get_value('Fiscal Year',from_fiscal_year,'year_start_date')
	if end_date < start_date:
		frappe.throw("End Date should be greater than Start Date")