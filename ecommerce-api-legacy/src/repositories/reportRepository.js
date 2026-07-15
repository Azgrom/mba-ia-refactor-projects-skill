// Persistence for the financial report. A single LEFT JOIN replaces the legacy
// per-course/per-enrollment/per-user/per-payment N+1 fan-out, and the explicit
// ORDER BY makes the result deterministic. Only the columns the report needs are
// projected — no full user or payment rows leave storage.
class ReportRepository {
    constructor(db) {
        this.db = db;
    }

    fetchReportRows() {
        return this.db.all(`
            SELECT
                c.id      AS course_id,
                c.title   AS course_title,
                e.id      AS enrollment_id,
                u.name    AS student_name,
                p.amount  AS payment_amount,
                p.status  AS payment_status
            FROM courses c
            LEFT JOIN enrollments e ON e.course_id = c.id
            LEFT JOIN users u ON u.id = e.user_id
            LEFT JOIN payments p ON p.enrollment_id = e.id
            ORDER BY c.id ASC, e.id ASC
        `);
    }
}

module.exports = { ReportRepository };
