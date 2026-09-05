import frappe

@frappe.whitelist()
def search_personnel(query):
    words = [w for w in query.strip().split() if w]
    if not words:
        return []
    conditions = []
    values = {}
    for i, word in enumerate(words):
        param = f"w{i}"
        values[param] = f"%{word}%"
        conditions.append(
            f"(first_name like %({param})s or last_name like %({param})s or middle_name like %({param})s)"
        )
    where_clause = " and ".join(conditions)
    return frappe.db.sql(
        f"""
        select name as personnel_info, employee_id, first_name, last_name, middle_name, department
        from `tabPersonnel Info`
        where {where_clause}
        limit 10
        """,
        values,
        as_dict=True,
    )

@frappe.whitelist()
def list_recent_leaves(search=None, limit=20):
    filters = []
    if search:
        filters = [["employee_name", "like", f"%{search}%"]]
    return frappe.get_all(
        "SMS Personnel Leaves",
        filters=filters,
        fields=["name", "parent as personnel_info", "employee_id", "employee_name", "department",
                "leave_type", "from_date", "to_date", "half_day", "reason", "date", "status",
                "days_approved", "with_pay", "without_pay", "immediate_superior", "hrd_head"],
        order_by="date desc",
        limit_page_length=limit,
    )
    
@frappe.whitelist()
def add_leave_application(employee_id, leave_type, from_date, to_date, half_day=0, reason=None, other_leave_reason=None):
    parent = frappe.get_doc("Personnel Info", employee_id)
    row = parent.append("leaves", {
        "employee_id": employee_id,
        "employee_name": f"{parent.first_name} {parent.last_name}",
        "department": parent.department,
        "date": frappe.utils.today(),
        "leave_type": leave_type,
        "other_leave_reason": other_leave_reason,
        "from_date": from_date,
        "to_date": to_date,
        "half_day": half_day,
        "reason": reason,
        "status": "Pending",
    })
    parent.save()
    return {"success": True, "name": row.name}

@frappe.whitelist()
def list_pending_leaves(search=None, limit=20):
    filters = [["status", "=", "Pending"]]
    if search:
        filters.append(["employee_name", "like", f"%{search}%"])
    return frappe.get_all(
        "SMS Personnel Leaves",
        filters=filters,
        fields=["name", "parent as personnel_info", "employee_id", "employee_name", "department",
                "leave_type", "from_date", "to_date", "half_day", "reason", "date", "status",
                "days_approved", "with_pay", "without_pay", "immediate_superior", "hrd_head"],
        order_by="date desc",
        limit_page_length=limit,
    )

@frappe.whitelist()
def approve_leave_application(employee_id, row_name, days_approved=None, with_pay=None, without_pay=None, immediate_superior=None, hrd_head=None):
    parent = frappe.get_doc("Personnel Info", employee_id)
    for row in parent.leaves:
        if row.name == row_name:
            row.status = "Approved"
            row.days_approved = days_approved
            row.with_pay = with_pay
            row.without_pay = without_pay
            row.immediate_superior = immediate_superior
            row.hrd_head = hrd_head
            break
    else:
        frappe.throw(f"Leave row {row_name} not found on employee {employee_id}")
    parent.save()
    return {"success": True}

@frappe.whitelist()
def reject_leave_application(employee_id, row_name, immediate_superior=None, hrd_head=None):
    parent = frappe.get_doc("Personnel Info", employee_id)
    for row in parent.leaves:
        if row.name == row_name:
            row.status = "Rejected"
            row.immediate_superior = immediate_superior
            row.hrd_head = hrd_head
            break
    else:
        frappe.throw(f"Leave row {row_name} not found on employee {employee_id}")
    parent.save()
    return {"success": True}

@frappe.whitelist()
def list_recent_loans(search=None, limit=20):
    filters = []
    if search:
        filters = [["employee_name", "like", f"%{search}%"]]
    return frappe.get_all(
        "SMS Personnel Loan",
        filters=filters,
        fields=["name", "parent as personnel_info", "employee_id", "employee_name", "department",
                "al_no", "date", "loan_type", "basic_pay", "previous_loan", "amount", "reason",
                "status", "interest_rate", "term", "interest_cost", "amortization", "loan_balance", "recommended_by", "approved_by"],
        order_by="date desc",
        limit_page_length=limit,
    )

@frappe.whitelist()
def add_loan_application(employee_id, loan_type, amount, reason=None, basic_pay=None, previous_loan=None):
    parent = frappe.get_doc("Personnel Info", employee_id)
    al_no = frappe.model.naming.make_autoname("LN.#####")
    row = parent.append("loan_ledgers", {
        "employee_id": employee_id,
        "employee_name": f"{parent.first_name} {parent.last_name}",
        "department": parent.department,
        "al_no": al_no,
        "date": frappe.utils.today(),
        "loan_type": loan_type,
        "basic_pay": basic_pay,
        "previous_loan": previous_loan,
        "amount": amount,
        "reason": reason,
        "status": "Pending",
    })
    parent.save()
    return {"success": True, "name": row.name, "al_no": al_no}

@frappe.whitelist()
def list_pending_loans(search=None, limit=20):
    filters = [["status", "=", "Pending"]]
    if search:
        filters.append(["employee_name", "like", f"%{search}%"])
    return frappe.get_all(
        "SMS Personnel Loan",
        filters=filters,
        fields=["name", "parent as personnel_info", "employee_id", "employee_name", "department",
                "al_no", "date", "loan_type", "basic_pay", "previous_loan", "amount", "reason",
                "status", "interest_rate", "term", "interest_cost", "amortization", "loan_balance", "recommended_by", "approved_by"],
        order_by="date desc",
        limit_page_length=limit,
    )

@frappe.whitelist()
def compute_loan_terms(amount, interest_rate, term):
    """
    Flat-rate add-on interest, not reducing-balance — UNVERIFIED against actual
    policy, see CLAUDE.md Known Gaps. Kept server-side so the frontend's
    "Compute" button and any future report/payslip logic can't drift apart.
    """
    amount = float(amount)
    interest_rate = float(interest_rate)
    term = int(term)
    interest_cost = amount * (interest_rate / 100)
    loan_balance = amount + interest_cost
    amortization = loan_balance / term if term else 0
    return {
        "interest_cost": round(interest_cost, 2),
        "amortization": round(amortization, 2),
        "loan_balance": round(loan_balance, 2),
    }

@frappe.whitelist()
def approve_loan_application(employee_id, row_name, interest_rate=None, term=None, interest_cost=None, amortization=None, loan_balance=None, recommended_by=None, approved_by=None):
    if "HR Manager" not in frappe.get_roles():
        frappe.throw("You are not permitted to approve loan applications.", frappe.PermissionError)

    parent = frappe.get_doc("Personnel Info", employee_id)
    for row in parent.loan_ledgers:
        if row.name == row_name:
            if row.status != "Pending":
                frappe.throw(f"This loan cannot be approved from its current status ({row.status}).")
            row.status = "Approved"
            row.interest_rate = interest_rate
            row.term = term
            row.interest_cost = interest_cost
            row.amortization = amortization
            row.loan_balance = loan_balance
            row.recommended_by = recommended_by
            row.approved_by = frappe.session.user  # derive from session, don't trust client input
            break
    else:
        frappe.throw(f"Loan row {row_name} not found on employee {employee_id}")
    parent.save()
    return {"success": True}

@frappe.whitelist()
def reject_loan_application(employee_id, row_name, recommended_by=None, approved_by=None):
    parent = frappe.get_doc("Personnel Info", employee_id)
    for row in parent.loan_ledgers:
        if row.name == row_name:
            row.status = "Rejected"
            row.recommended_by = recommended_by
            row.approved_by = approved_by
            break
    else:
        frappe.throw(f"Loan row {row_name} not found on employee {employee_id}")
    parent.save()
    return {"success": True}

@frappe.whitelist()
def get_personnel_kpis():
    total = frappe.db.count("Personnel Info")
    rows = frappe.db.sql(
        "select employee_status, count(*) as n from `tabPersonnel Info` group by employee_status",
        as_dict=True,
    )
    counts = {"Regular": 0, "Contractual": 0, "Part Timer": 0, "Probationary": 0}
    for row in rows:
        status = row.get("employee_status")
        if status in counts:
            counts[status] = row["n"]
    return {
        "total": total,
        "regular": counts["Regular"],
        "contractual": counts["Contractual"],
        "part_timer": counts["Part Timer"],
        "probationary": counts["Probationary"],
    }

@frappe.whitelist()
def get_employee(personnel_info):
    return frappe.db.get_value(
        "Personnel Info",
        personnel_info,
        ["name as personnel_info", "employee_id", "first_name", "last_name", "department"],
        as_dict=True,
    )

@frappe.whitelist()
def list_approved_loans(search=None, limit=20):
    filters = [["status", "=", "Approved"]]
    if search:
        filters.append(["employee_name", "like", f"%{search}%"])
    return frappe.get_all(
        "SMS Personnel Loan",
        filters=filters,
        fields=["name", "parent as personnel_info", "employee_id", "employee_name", "department",
                "al_no", "date", "loan_type", "amount", "interest_rate", "term",
                "interest_cost", "amortization", "loan_balance", "recommended_by", "approved_by"],
        order_by="date desc",
        limit_page_length=limit,
    )

@frappe.whitelist()
def release_loan_application(personnel_info, row_name, released_by=None):
    parent = frappe.get_doc("Personnel Info", personnel_info)
    for row in parent.loan_ledgers:
        if row.name == row_name:
            if row.status == "Released":
                frappe.throw("This loan has already been released.")
            if row.status != "Approved":
                frappe.throw("This loan cannot be released unless it is in Approved status.")
            if not row.approved_by:
                frappe.throw("This loan cannot be released until it has a recorded Approved By value.")
            row.status = "Released"
            row.released_by = released_by
            row.date_released = frappe.utils.now_datetime()
            break
    else:
        frappe.throw(f"Loan row {row_name} not found on Personnel Info {personnel_info}")
    parent.save()
    return {"success": True}
