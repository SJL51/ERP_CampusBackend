# Copyright (c) 2026, School Administration and contributors
# For license information, please see license.txt

import frappe

# Maps each blueprint module (§2) to the roles that should see it in the
# frontend sidebar. Mirrors the consolidated role matrix (blueprint §3.1.6).
MODULE_ROLE_MAP = {
	"Registrar": {
		"SMS Registrar",
		"SMS Asst Registrar",
		"SMS Instructor",
		"Academics User",
		"System Manager",
	},
	"Finance": {
		# Covers both Finance Billing and Finance Purchasing (blueprint §2) —
		# they share one frontend nav entry.
		"SMS Finance Manager",
		"SMS Finance Clerk",
		"SMS Cashier",
		"SMS Finance User",
		"SMS GL Approver",
		"SMS Finance Officer",
		"SMS Auditor",
		"SMS Canteen Cashier",
		"SMS Purchasing Officer",
		"SMS Receiving Officer",
		"SMS Recommending Officer",
		"SMS Approving Officer",
		"SMS Requestor",
		"Accounts User",
		"Accounts Manager",
		"System Manager",
	},
	"Personnel": {
		"SMS HR Manager",
		"SMS HR Officer",
		"SMS Payroll Officer",
		"SMS Leave Recommending Officer",
		"SMS Leave Approving Officer",
		"SMS Loan Recommending Officer",
		"SMS Loan Approving Officer",
		"HR Manager",
		"HR User",
		"System Manager",
	},
	"Asset": {
		"SMS Property Custodian",
		"SMS Asst Property Custodian",
		"System Manager",
	},
	"Library": {
		"SMS Librarian",
		"System Manager",
	},
	"Administration": {
		"SMS Administrator",
		"System Manager",
	},
}


def get_visible_modules(roles: list[str]) -> list[str]:
	role_set = set(roles)
	return [module for module, allowed in MODULE_ROLE_MAP.items() if role_set & allowed]


@frappe.whitelist()
def me():
	"""Replaces the legacy's scattered `If UCase(access) = "..."` checks
	(blueprint §4.1) with one server-resolved role/module list the frontend
	uses to decide what to render — see blueprint §5.5 (Authentication Flow)."""
	if frappe.session.user == "Guest":
		frappe.throw("Not logged in", frappe.AuthenticationError)

	roles = frappe.get_roles(frappe.session.user)
	return {
		"user": frappe.session.user,
		"full_name": frappe.utils.get_fullname(frappe.session.user),
		"roles": roles,
		"modules": get_visible_modules(roles),
		# The frontend is a separate origin from the Frappe desk, so it never
		# gets frappe.boot.csrf_token for free — hand it back here instead.
		"csrf_token": frappe.sessions.get_csrf_token(),
	}
