from education.education.doctype.program_enrollment_tool.program_enrollment_tool import ProgramEnrollmentTool
from frappe import _
from education.education.api import enroll_student

import frappe
class CustomEnrollment(ProgramEnrollmentTool):
	@frappe.whitelist()
	def enroll_students(self):
		total = len(self.students)
		for i, stud in enumerate(self.students):
			frappe.publish_realtime(
				"program_enrollment_tool", dict(progress=[i + 1, total]), user=frappe.session.user
			)
			if stud.student:
				prog_enrollment = frappe.new_doc("Program Enrollment")
				prog_enrollment.student = stud.student
				prog_enrollment.student_name = stud.student_name
				prog_enrollment.student_category = stud.student_category
				prog_enrollment.program = self.new_program
				prog_enrollment.academic_year = self.new_academic_year
				prog_enrollment.academic_term = self.new_academic_term
				# Customisation
				prog_enrollment.mode_of_transportation = frappe.db.get_value('Program Enrollment',{'student':stud.student,'student_name':stud.student_name,'academic_year':self.academic_year,'program':self.program,'docstatus':['!=',2]},'mode_of_transportation')
				prog_enrollment.trip_distance = frappe.db.get_value('Program Enrollment',{'student':stud.student,'student_name':stud.student_name,'academic_year':self.academic_year,'program':self.program,'docstatus':['!=',2]},'trip_distance')
				prog_enrollment.trip_band =  frappe.db.get_value('Program Enrollment',{'student':stud.student,'student_name':stud.student_name,'academic_year':self.academic_year,'program':self.program,'docstatus':['!=',2]},'trip_band')
				prog_enrollment.pickup_location= frappe.db.get_value('Program Enrollment',{'student':stud.student,'student_name':stud.student_name,'academic_year':self.academic_year,'program':self.program,'docstatus':['!=',2]},'pickup_location')
				prog_enrollment.route_no= frappe.db.get_value('Program Enrollment',{'student':stud.student,'student_name':stud.student_name,'academic_year':self.academic_year,'program':self.program,'docstatus':['!=',2]},'route_no')
				prog_enrollment.drop_location = frappe.db.get_value('Program Enrollment',{'student':stud.student,'student_name':stud.student_name,'academic_year':self.academic_year,'program':self.program,'docstatus':['!=',2]},'drop_location')
				prog_enrollment.drop_route = frappe.db.get_value('Program Enrollment',{'student':stud.student,'student_name':stud.student_name,'academic_year':self.academic_year,'program':self.program,'docstatus':['!=',2]},'drop_route')
				# Customisation
				prog_enrollment.student_batch_name = (
					stud.student_batch_name if stud.student_batch_name else self.new_student_batch
				)
				prog_enrollment.save()
			elif stud.student_applicant:
				prog_enrollment = enroll_student(stud.student_applicant)
				prog_enrollment.academic_year = self.academic_year
				prog_enrollment.academic_term = self.academic_term
				prog_enrollment.student_batch_name = (
					stud.student_batch_name if stud.student_batch_name else self.new_student_batch
				)
				prog_enrollment.save()
		frappe.msgprint(_("{0} Students have been enrolled").format(total))
