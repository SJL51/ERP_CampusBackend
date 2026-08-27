# Copyright (c) 2026, School Administration and contributors
# For license information, please see license.txt
"""
Registrar module (blueprint Phase 1) custom fields, extending real installed
DocTypes rather than duplicating them — see IMPLEMENTATION-MAPPING.md's
Registrar section for the field-by-field rationale.

Link-target translation (blueprint name -> real DocType this app extends):
  SMS Student  -> Student (education)      SMS Course (degree) -> Program (education)
  SMS Subject  -> Course (education)        SMS Class -> Student Group (education)
  SMS Section  -> Student Batch Name (education)   SMS Room -> Room (education)
  SMS Branch   -> Branch (erpnext)          SMS Employee -> Employee (erpnext, until Personnel phase)
  SMS Code     -> SMS Code (campus_erp, already built in Phase 0)
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

CUSTOM_FIELDS = {
	"Student": [
		{
			"fieldname": "sms_registrar_tab",
			"fieldtype": "Tab Break",
			"label": "Registrar (PH)",
			"insert_after": "country",
		},
		{"fieldname": "birth_place", "label": "Birth Place", "fieldtype": "Data", "insert_after": "sms_registrar_tab"},
		{"fieldname": "town", "label": "Town", "fieldtype": "Data", "insert_after": "birth_place"},
		{"fieldname": "province", "label": "Province", "fieldtype": "Data", "insert_after": "town"},
		{"fieldname": "lrn", "label": "LRN (DepEd Learner Reference No.)", "fieldtype": "Data", "insert_after": "province"},
		{"fieldname": "column_break_sms_1", "fieldtype": "Column Break", "insert_after": "lrn"},
		{"fieldname": "sms_status", "label": "Status", "fieldtype": "Select",
			"options": "Active\nInactive\nGraduated\nDropped", "default": "Active", "insert_after": "column_break_sms_1"},
		{"fieldname": "branch", "label": "Branch", "fieldtype": "Link", "options": "Branch", "insert_after": "sms_status"},
		{"fieldname": "stdnt_cno", "label": "Student Control No.", "fieldtype": "Data", "read_only": 1, "insert_after": "branch"},
		{"fieldname": "signature", "label": "Signature", "fieldtype": "Attach Image", "insert_after": "stdnt_cno"},
		{"fieldname": "academic_section", "fieldtype": "Section Break", "label": "Academic Standing", "insert_after": "signature"},
		{"fieldname": "general_average", "label": "General Average", "fieldtype": "Float", "read_only": 1, "insert_after": "academic_section"},
		{"fieldname": "column_break_sms_2", "fieldtype": "Column Break", "insert_after": "general_average"},
		{"fieldname": "scholarship", "label": "Scholarship", "fieldtype": "Link", "options": "SMS Code",
			"description": "Filtered to SMS Code.code_type = Scholarship", "insert_after": "column_break_sms_2"},
		{"fieldname": "discount_type", "label": "Discount Type", "fieldtype": "Link", "options": "SMS Code",
			"description": "Filtered to SMS Code.code_type = Fee", "insert_after": "scholarship"},
		{"fieldname": "transfer_section", "fieldtype": "Section Break", "label": "Transfer & Graduation History", "insert_after": "discount_type"},
		{"fieldname": "transferee", "label": "Transferee", "fieldtype": "Check", "insert_after": "transfer_section"},
		{"fieldname": "prev_course", "label": "Previous Course", "fieldtype": "Data", "depends_on": "eval:doc.transferee", "insert_after": "transferee"},
		{"fieldname": "last_course_attended", "label": "Last Course Attended", "fieldtype": "Data", "depends_on": "eval:doc.transferee", "insert_after": "prev_course"},
		{"fieldname": "year_last_attended", "label": "Year Last Attended", "fieldtype": "Int", "depends_on": "eval:doc.transferee", "insert_after": "last_course_attended"},
		{"fieldname": "column_break_sms_3", "fieldtype": "Column Break", "insert_after": "year_last_attended"},
		{"fieldname": "graduated", "label": "Graduated", "fieldtype": "Check", "read_only": 1,
			"description": "Set by SMS Graduation Batch's approve_graduation, not hand-edited", "insert_after": "column_break_sms_3"},
		{"fieldname": "year_graduated", "label": "Year Graduated", "fieldtype": "Int", "read_only": 1, "insert_after": "graduated"},
		{"fieldname": "school_history_section", "fieldtype": "Section Break", "label": "School History (PH Basic Ed)", "collapsible": 1, "insert_after": "year_graduated"},
		{"fieldname": "elementary", "label": "Elementary School", "fieldtype": "Data", "insert_after": "school_history_section"},
		{"fieldname": "year_elementary", "label": "Year Graduated (Elementary)", "fieldtype": "Int", "insert_after": "elementary"},
		{"fieldname": "column_break_sms_4", "fieldtype": "Column Break", "insert_after": "year_elementary"},
		{"fieldname": "junior_high", "label": "Junior High School", "fieldtype": "Data", "insert_after": "column_break_sms_4"},
		{"fieldname": "year_junior_high", "label": "Year Graduated (Junior High)", "fieldtype": "Int", "insert_after": "junior_high"},
		{"fieldname": "column_break_sms_5", "fieldtype": "Column Break", "insert_after": "year_junior_high"},
		{"fieldname": "secondary", "label": "Senior High School", "fieldtype": "Data", "insert_after": "column_break_sms_5"},
		{"fieldname": "year_secondary", "label": "Year Graduated (Senior High)", "fieldtype": "Int", "insert_after": "secondary"},
		{"fieldname": "column_break_sms_6", "fieldtype": "Column Break", "insert_after": "year_secondary"},
		{"fieldname": "tertiary", "label": "Tertiary School", "fieldtype": "Data", "insert_after": "column_break_sms_6"},
		{"fieldname": "year_tertiary", "label": "Year Graduated (Tertiary)", "fieldtype": "Int", "insert_after": "tertiary"},
		{"fieldname": "credentials_section", "fieldtype": "Section Break", "label": "Credentials Checklist", "insert_after": "year_tertiary"},
		{"fieldname": "credentials", "label": "Credentials Checklist", "fieldtype": "Table", "options": "SMS Student Credential", "insert_after": "credentials_section"},
	],
	"Student Log": [
		{"fieldname": "violation", "label": "Violation", "fieldtype": "Data",
			"depends_on": "eval:doc.type=='Disciplinary'", "insert_after": "log"},
		{"fieldname": "sanction", "label": "Sanction", "fieldtype": "Small Text",
			"depends_on": "eval:doc.type=='Disciplinary'", "insert_after": "violation"},
	],
	"Program": [
		{"fieldname": "sms_registrar_section", "fieldtype": "Section Break", "label": "Registrar (PH)", "insert_after": "program_abbreviation"},
		{"fieldname": "course_code", "label": "Course Code", "fieldtype": "Data",
			"description": "Compact code, distinct from the descriptive program_name", "insert_after": "sms_registrar_section"},
		{"fieldname": "sem_type", "label": "Term Structure", "fieldtype": "Select",
			"options": "Quarter\nPrelim-Midterm-Finals\nTrisemester\nFull Payment Only", "insert_after": "course_code"},
		{"fieldname": "column_break_sms_prog_1", "fieldtype": "Column Break", "insert_after": "sem_type"},
		{"fieldname": "is_diploma_course", "label": "Issues Diploma (not Certificate)", "fieldtype": "Check",
			"description": "Replaces the legacy 'BS'-prefix string-sniffing", "insert_after": "column_break_sms_prog_1"},
		{"fieldname": "branch", "label": "Branch", "fieldtype": "Link", "options": "Branch", "insert_after": "is_diploma_course"},
		{"fieldname": "misc_fee_code", "label": "Misc Fee Code", "fieldtype": "Link", "options": "Fee Category", "insert_after": "branch"},
		{"fieldname": "course_desc", "label": "Long Description", "fieldtype": "Text Editor", "insert_after": "misc_fee_code"},
	],
	"Course": [
		{"fieldname": "sms_registrar_section", "fieldtype": "Section Break", "label": "Registrar (PH)", "insert_after": "description"},
		{"fieldname": "subject_code", "label": "Subject Code", "fieldtype": "Data", "insert_after": "sms_registrar_section"},
		{"fieldname": "unit", "label": "Unit", "fieldtype": "Float", "insert_after": "subject_code"},
		{"fieldname": "column_break_sms_course_1", "fieldtype": "Column Break", "insert_after": "unit"},
		{"fieldname": "lec", "label": "Lecture Units", "fieldtype": "Float", "insert_after": "column_break_sms_course_1"},
		{"fieldname": "lab", "label": "Lab Units", "fieldtype": "Float", "insert_after": "lec"},
		{"fieldname": "is_nstp_or_ms", "label": "Exclude from GPA (NSTP/MS)", "fieldtype": "Check",
			"description": "Replaces the legacy branch_code='02'-only hardcode", "insert_after": "lab"},
		{"fieldname": "course_desc", "label": "Long Description", "fieldtype": "Text Editor", "insert_after": "is_nstp_or_ms"},
	],
	"Student Group": [
		{"fieldname": "sms_schedule_section", "fieldtype": "Section Break", "label": "Schedule (PH Registrar)", "insert_after": "instructors"},
		{"fieldname": "room", "label": "Room", "fieldtype": "Link", "options": "Room", "insert_after": "sms_schedule_section"},
		{"fieldname": "start_time", "label": "Start Time", "fieldtype": "Time", "insert_after": "room"},
		{"fieldname": "end_time", "label": "End Time", "fieldtype": "Time", "insert_after": "start_time"},
		{"fieldname": "column_break_sms_sg_1", "fieldtype": "Column Break", "insert_after": "end_time"},
		{"fieldname": "monday", "label": "Mon", "fieldtype": "Check", "insert_after": "column_break_sms_sg_1"},
		{"fieldname": "tuesday", "label": "Tue", "fieldtype": "Check", "insert_after": "monday"},
		{"fieldname": "wednesday", "label": "Wed", "fieldtype": "Check", "insert_after": "tuesday"},
		{"fieldname": "thursday", "label": "Thu", "fieldtype": "Check", "insert_after": "wednesday"},
		{"fieldname": "friday", "label": "Fri", "fieldtype": "Check", "insert_after": "thursday"},
		{"fieldname": "saturday", "label": "Sat", "fieldtype": "Check", "insert_after": "friday"},
		{"fieldname": "sunday", "label": "Sun", "fieldtype": "Check", "insert_after": "saturday"},
		{"fieldname": "remarks", "label": "Remarks", "fieldtype": "Small Text", "insert_after": "sunday"},
	],
	"Course Enrollment": [
		{"fieldname": "student_group", "label": "Class (Student Group)", "fieldtype": "Link", "options": "Student Group",
			"description": "Needed when a Course runs multiple Student Group sections in one term", "insert_after": "student_name"},
		{"fieldname": "sms_grading_section", "fieldtype": "Section Break", "label": "Grading (PH fixed-period)", "insert_after": "student_group"},
		{"fieldname": "prelim", "label": "Prelim", "fieldtype": "Float", "insert_after": "sms_grading_section"},
		{"fieldname": "midterm", "label": "Midterm", "fieldtype": "Float", "insert_after": "prelim"},
		{"fieldname": "final", "label": "Final", "fieldtype": "Float", "insert_after": "midterm"},
		{"fieldname": "column_break_sms_ce_1", "fieldtype": "Column Break", "insert_after": "final"},
		{"fieldname": "re_exam", "label": "Re-Exam", "fieldtype": "Float", "insert_after": "column_break_sms_ce_1"},
		{"fieldname": "final_rating", "label": "Final Rating", "fieldtype": "Data",
			"description": "Kept textual — legacy allows INC/DRP values a numeric field can't hold", "insert_after": "re_exam"},
		{"fieldname": "grade_remarks", "label": "Remarks", "fieldtype": "Select",
			"options": "\nPassed\nFailed\nIncomplete\nDropped\nFor Re-exam", "insert_after": "final_rating"},
		{"fieldname": "points", "label": "Grade Points", "fieldtype": "Float", "read_only": 1,
			"description": "Computed via campus_erp.api.registrar.compute_grade_points", "insert_after": "grade_remarks"},
		{"fieldname": "status", "label": "Status", "fieldtype": "Select",
			"options": "Enrolled\nDropped\nCompleted", "default": "Enrolled",
			"description": "Class-completion status only — the registration-workflow pipeline lives on Finance's Student Assessment (blueprint §3.1.2)",
			"insert_after": "points"},
	],
	"Grading Scale Interval": [
		{"fieldname": "is_passing", "label": "Is Passing", "fieldtype": "Check", "insert_after": "grade_description"},
	],
	"Education Settings": [
		{"fieldname": "sms_registrar_tab", "fieldtype": "Tab Break", "label": "Registrar (PH)", "insert_after": "school_college_logo"},
		{"fieldname": "check_prerequisite", "label": "Check Prerequisite", "fieldtype": "Check", "insert_after": "sms_registrar_tab"},
		{"fieldname": "check_prerequisite_grade", "label": "Check Prerequisite Grade", "fieldtype": "Check", "insert_after": "check_prerequisite"},
		{"fieldname": "passing_grade", "label": "Passing Grade", "fieldtype": "Float", "default": "75", "insert_after": "check_prerequisite_grade"},
		{"fieldname": "column_break_sms_es_1", "fieldtype": "Column Break", "insert_after": "passing_grade"},
		{"fieldname": "exclude_nstp_from_gpa", "label": "Exclude NSTP/MS from GPA", "fieldtype": "Check", "default": "1", "insert_after": "column_break_sms_es_1"},
		{"fieldname": "print_cor", "label": "Enable Print COR", "fieldtype": "Check", "default": "1", "insert_after": "exclude_nstp_from_gpa"},
		{"fieldname": "print_pre_reg", "label": "Enable Print Pre-Registration", "fieldtype": "Check", "default": "1", "insert_after": "print_cor"},
		{"fieldname": "cor_layout", "label": "COR Layout", "fieldtype": "Select",
			"options": "Standard (fees visible)\nFees Hidden", "insert_after": "print_pre_reg"},
	],
	"Room": [
		{"fieldname": "room_no", "label": "Room No.", "fieldtype": "Data", "insert_after": "room_name"},
		{"fieldname": "building", "label": "Building", "fieldtype": "Data", "insert_after": "room_no"},
		{"fieldname": "branch", "label": "Branch", "fieldtype": "Link", "options": "Branch", "insert_after": "building"},
	],
	"Student Batch Name": [
		{"fieldname": "course", "label": "Course (Program)", "fieldtype": "Link", "options": "Program", "insert_after": "batch_name"},
		{"fieldname": "year_level", "label": "Year Level", "fieldtype": "Int", "insert_after": "course"},
		{"fieldname": "max_students", "label": "Max Students", "fieldtype": "Int", "insert_after": "year_level"},
		{"fieldname": "branch", "label": "Branch", "fieldtype": "Link", "options": "Branch", "insert_after": "max_students"},
	],
	"Branch": [
		{"fieldname": "sms_print_assets_section", "fieldtype": "Section Break", "label": "Print Assets (PH Registrar)", "insert_after": "branch"},
		{"fieldname": "logo_header", "label": "Logo / Header", "fieldtype": "Attach Image", "insert_after": "sms_print_assets_section"},
		{"fieldname": "sig_registrar", "label": "Registrar Signature", "fieldtype": "Attach Image", "insert_after": "logo_header"},
		{"fieldname": "column_break_sms_branch_1", "fieldtype": "Column Break", "insert_after": "sig_registrar"},
		{"fieldname": "bg_front", "label": "Certificate Background (Front)", "fieldtype": "Attach Image", "insert_after": "column_break_sms_branch_1"},
		{"fieldname": "bg_back", "label": "Certificate Background (Back)", "fieldtype": "Attach Image", "insert_after": "bg_front"},
	],
}


def sync_registrar_property_setters():
	"""Extends existing Select options rather than adding new fields."""
	frappe.make_property_setter(
		{
			"doctype": "Student Log",
			"fieldname": "type",
			"property": "options",
			"value": "General\nAcademic\nMedical\nAchievement\nDisciplinary",
			"property_type": "Text",
		},
		validate_fields_for_doctype=False,
	)


def sync_registrar_custom_fields():
	"""Idempotent — safe to call from after_migrate every time (blueprint Phase 1)."""
	create_custom_fields(CUSTOM_FIELDS, update=True)
	sync_registrar_property_setters()
	frappe.clear_cache()
