# Copyright (c) 2026, School Administration and contributors
# For license information, please see license.txt
"""
Registrar business rules (blueprint Phase 1). Per the migration's guiding
principle (blueprint §4.3): DocTypes own schema and permissions only; every
rule that used to live inline in a VB button-click handler lives here once,
instead of duplicated across forms — the legacy prerequisite check alone was
found re-implemented 5 times with subtle inconsistencies.
"""

import frappe
from frappe import _
from frappe.utils import flt


@frappe.whitelist()
def check_prerequisites(student: str, course: str) -> dict:
	"""Single canonical prerequisite check, replacing the legacy's 5 duplicated
	(and inconsistent) implementations. Returns {ok, reason} rather than
	throwing, so callers (enroll(), and the frontend pre-flight check) can
	decide what to do with a failure.
	"""
	settings = frappe.get_cached_doc("Education Settings")
	if not settings.check_prerequisite:
		return {"ok": True, "reason": None}

	# Find this course's prerequisite via the student's active curriculum.
	student_doc = frappe.get_doc("Student", student)
	program_enrollment = frappe.get_all(
		"Program Enrollment",
		filters={"student": student},
		fields=["name", "program"],
		order_by="creation desc",
		limit=1,
	)
	if not program_enrollment:
		return {"ok": False, "reason": _("Student has no Program Enrollment on record.")}

	curriculum = frappe.get_all(
		"SMS Curriculum",
		filters={"course": program_enrollment[0].program, "is_active": 1},
		limit=1,
	)
	if not curriculum:
		# No curriculum on file for this program — nothing to check against.
		return {"ok": True, "reason": None}

	curriculum_doc = frappe.get_doc("SMS Curriculum", curriculum[0].name)
	prerequisite = None
	for row in curriculum_doc.subjects:
		if row.subject == course:
			prerequisite = row.prerequisite
			break

	if not prerequisite:
		return {"ok": True, "reason": None}

	prior = frappe.get_all(
		"Course Enrollment",
		filters={"student": student, "course": prerequisite},
		fields=["name", "status", "final_rating", "points"],
	)
	passed = [row for row in prior if row.status == "Completed" and row.final_rating not in ("INC", "DRP", "")]
	if not passed:
		return {
			"ok": False,
			"reason": _("Prerequisite {0} has not been completed.").format(prerequisite),
		}

	if settings.check_prerequisite_grade:
		# Stricter than "passed" (status == Completed, already required above):
		# the prerequisite's raw numeric grade must clear the configured
		# passing_grade threshold, not just whatever line the grading scale
		# happened to mark as passing.
		best_grade = max(
			(flt(row.final_rating) for row in passed if _is_number(row.final_rating)),
			default=None,
		)
		if best_grade is None or best_grade < flt(settings.passing_grade):
			return {
				"ok": False,
				"reason": _("Prerequisite {0} grade does not meet the required standard ({1}).").format(
					prerequisite, settings.passing_grade
				),
			}

	return {"ok": True, "reason": None}


@frappe.whitelist()
def enroll(student: str, student_group: str) -> dict:
	"""Enroll a student into one class (Student Group). Consolidates the
	legacy's duplicate-enlistment, class-capacity, and schedule-conflict
	checks that used to be re-implemented per form.
	"""
	sg = frappe.get_doc("Student Group", student_group)
	if not sg.course:
		frappe.throw(_("Student Group {0} has no Course set.").format(student_group))

	# 1. Duplicate-enrollment guard
	existing = frappe.get_all(
		"Course Enrollment",
		filters={"student": student, "student_group": student_group},
	)
	if existing:
		frappe.throw(_("{0} is already enrolled in {1}.").format(student, student_group))

	# 2. Prerequisite check
	check = check_prerequisites(student, sg.course)
	if not check["ok"]:
		frappe.throw(check["reason"])

	# 3. Class capacity — locked read to avoid the legacy's read-modify-write
	# race condition (blueprint §7 R-9: regClasses.enrolled was double-
	# incremented via 4+ independent legacy code paths).
	if sg.max_strength:
		current = frappe.db.sql(
			"""SELECT COUNT(*) FROM `tabCourse Enrollment`
			WHERE student_group=%s FOR UPDATE""",
			(student_group,),
		)[0][0]
		if current >= sg.max_strength:
			frappe.throw(_("Class {0} is at capacity ({1}/{1}).").format(student_group, sg.max_strength))

	# 4. Schedule-conflict guard — the legacy's FacultyInUse/RoomInUse/
	# DataInUse checks never actually worked (blueprint §8 Q1); this is a
	# real implementation, not a port.
	if sg.start_time and sg.end_time:
		day_fields = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
		my_days = {d for d in day_fields if sg.get(d)}
		if my_days:
			others = frappe.get_all(
				"Course Enrollment",
				filters={"student": student},
				fields=["student_group"],
			)
			for row in others:
				if not row.student_group:
					continue
				other_sg = frappe.get_cached_doc("Student Group", row.student_group)
				other_days = {d for d in day_fields if other_sg.get(d)}
				if not (my_days & other_days):
					continue
				if other_sg.start_time and other_sg.end_time and _times_overlap(
					sg.start_time, sg.end_time, other_sg.start_time, other_sg.end_time
				):
					frappe.throw(
						_("Schedule conflict with {0} on a shared day/time.").format(row.student_group)
					)

	program_enrollment = frappe.get_all(
		"Program Enrollment",
		filters={"student": student, **({"program": sg.program} if sg.program else {})},
		order_by="creation desc",
		limit=1,
		pluck="name",
	)
	if not program_enrollment:
		frappe.throw(
			_("{0} has no Program Enrollment{1} — enroll in the program before enrolling in a class.").format(
				student, _(" for {0}").format(sg.program) if sg.program else ""
			)
		)

	enrollment = frappe.get_doc(
		{
			"doctype": "Course Enrollment",
			"student": student,
			"course": sg.course,
			"student_group": student_group,
			"program": sg.program,
			"program_enrollment": program_enrollment[0],
			"enrollment_date": frappe.utils.today(),
			"status": "Enrolled",
		}
	)
	enrollment.insert(ignore_permissions=frappe.has_permission("Course Enrollment", "create"))
	return {"name": enrollment.name}


def _times_overlap(a_start, a_end, b_start, b_end) -> bool:
	return a_start < b_end and b_start < a_end


@frappe.whitelist()
def drop_enrollment(course_enrollment: str, reason: str | None = None) -> dict:
	doc = frappe.get_doc("Course Enrollment", course_enrollment)
	doc.status = "Dropped"
	if reason:
		doc.grade_remarks = "Dropped"
	doc.save(ignore_permissions=frappe.has_permission("Course Enrollment", "write", doc=doc))
	return {"name": doc.name, "status": doc.status}


@frappe.whitelist()
def compute_grade_points(course_enrollment: str) -> dict:
	"""Single canonical grade-to-points conversion, replacing the legacy's
	3-4 independently re-implemented versions — one of which (frmRegPrintRanking)
	had a confirmed bug (a `FinalRating = 0` vs `> 0` condition that silently
	broke conversion for ordinary 1.00-3.00 grades). Uses the school's Grading
	Scale (education app) rather than a hardcoded table.
	"""
	doc = frappe.get_doc("Course Enrollment", course_enrollment)
	if doc.final_rating in (None, "", "INC", "DRP"):
		return {"points": None, "is_passing": None}

	try:
		numeric_grade = flt(doc.final_rating)
	except (TypeError, ValueError):
		frappe.throw(_("Final Rating {0} is not a numeric grade.").format(doc.final_rating))

	course = frappe.get_cached_doc("Course", doc.course)
	scale_name = course.default_grading_scale
	if not scale_name:
		frappe.throw(
			_("Course {0} has no default_grading_scale configured — cannot compute points.").format(doc.course)
		)

	scale = frappe.get_doc("Grading Scale", scale_name)
	best_match = None
	for interval in sorted(scale.intervals, key=lambda r: flt(r.threshold)):
		if numeric_grade >= flt(interval.threshold):
			best_match = interval

	if not best_match:
		frappe.throw(_("No grading interval matches {0} on scale {1}.").format(numeric_grade, scale_name))

	points = flt(best_match.grade_code) if best_match.grade_code and _is_number(best_match.grade_code) else None
	is_passing = bool(best_match.is_passing)

	doc.db_set("points", points, notify=False)
	if is_passing and doc.status != "Completed":
		doc.db_set("status", "Completed", notify=False)
	elif not is_passing:
		doc.db_set("grade_remarks", "Failed", notify=False)

	return {"points": points, "is_passing": is_passing, "grade_code": best_match.grade_code}


def _is_number(value) -> bool:
	try:
		float(value)
		return True
	except (TypeError, ValueError):
		return False


@frappe.whitelist()
def get_class_roster(student_group: str) -> list[dict]:
	"""Backing call for the frontend's class-roster/gradebook screen."""
	return frappe.get_all(
		"Course Enrollment",
		filters={"student_group": student_group},
		fields=[
			"name",
			"student",
			"student_name",
			"prelim",
			"midterm",
			"final",
			"final_rating",
			"grade_remarks",
			"points",
			"status",
		],
		order_by="student_name asc",
	)
