import frappe
from frappe import _
from frappe.utils import flt
from erpnext.accounts.general_ledger import make_gl_entries, make_reverse_gl_entries
from erpnext.controllers.accounts_controller import AccountsController


class SMSStudentAssessment(AccountsController):
	def validate(self):
		self.student_name = frappe.db.get_value("Student", self.student, "student_name")
		self.validate_enrollment()
		self.validate_one_active_assessment()
		self.calculate_totals()
		self.set_missing_accounts_and_fields()

	def validate_enrollment(self):
		if self.program_enrollment:
			enrollment_student = frappe.db.get_value("Program Enrollment", self.program_enrollment, "student")
			if enrollment_student != self.student:
				frappe.throw(_("Program Enrollment {0} does not belong to {1}").format(self.program_enrollment, self.student))

	def validate_one_active_assessment(self):
		if self.is_reassessment:
			return
		existing = frappe.get_all(
			"SMS Student Assessment",
			filters={
				"student": self.student,
				"school_term": self.school_term,
				"docstatus": ["!=", 2],
				"name": ["!=", self.name or "New SMS Student Assessment"],
			},
		)
		if existing:
			frappe.throw(_("{0} already has an active assessment for {1}. Use Reassessment instead.").format(self.student, self.school_term))

	def calculate_totals(self):
		self.assessment = flt(self.tuition) + flt(self.misc_fee) + flt(self.other_fee)
		self.new_tuition = flt(self.tuition) - flt(self.other_discount) - flt(self.misc_discount)
		self.total_fee = (
			flt(self.new_tuition) + flt(self.misc_fee) + flt(self.other_fee)
			- flt(self.subsidy) + flt(self.old_account) - flt(self.old_account_payment)
		)
		self.receivable = flt(self.total_fee) - flt(self.payment)

	def set_missing_accounts_and_fields(self):
		if not self.company:
			self.company = frappe.defaults.get_defaults().get("company")
		if not self.company:
			return
		if not self.currency:
			self.currency = frappe.get_cached_value("Company", self.company, "default_currency")
		if not self.cost_center:
			self.cost_center = frappe.get_cached_value("Company", self.company, "cost_center")
		if not self.receivable_account:
			self.receivable_account = frappe.get_cached_value("Company", self.company, "default_receivable_account")

	def on_submit(self):
		self.make_gl_entries()

	def on_cancel(self):
		self.ignore_linked_doctypes = ("GL Entry", "Payment Ledger Entry")
		make_reverse_gl_entries(voucher_type=self.doctype, voucher_no=self.name)

	def make_gl_entries(self):
		if not self.total_fee:
			return
		default_income_account = frappe.get_cached_value("Company", self.company, "default_income_account")
		entries = [
			self.get_gl_dict(
				{
					"account": self.receivable_account,
					"party_type": "Student",
					"party": self.student,
					"against": default_income_account,
					"debit": self.total_fee,
					"debit_in_account_currency": self.total_fee,
					"against_voucher": self.name,
					"against_voucher_type": self.doctype,
					"cost_center": self.cost_center,
				},
				item=self,
			)
		]
		totals_by_account = {}
		for row in self.assessment_detail:
			account = get_income_account_for_fee_code(row.fee_code, self.company) or default_income_account
			totals_by_account[account] = totals_by_account.get(account, 0) + flt(row.amount)
		if not totals_by_account:
			totals_by_account[default_income_account] = self.total_fee
		for account, amount in totals_by_account.items():
			if not amount:
				continue
			entries.append(
				self.get_gl_dict(
					{
						"account": account,
						"against": self.student,
						"credit": amount,
						"credit_in_account_currency": amount,
						"cost_center": self.cost_center,
					},
					item=self,
				)
			)
		make_gl_entries(entries, cancel=(self.docstatus == 2), update_outstanding="No", merge_entries=True)


def get_income_account_for_fee_code(fee_code, company):
	if not fee_code:
		return None
	category = frappe.get_cached_doc("Fee Category", fee_code)
	for row in category.item_defaults:
		if row.company == company and row.income_account:
			return row.income_account
	return None
