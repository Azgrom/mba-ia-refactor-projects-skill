const { PaymentStatus } = require('../domain/payment');

// Builds the financial report from the flat, ordered join rows: groups by course
// (preserving row order), sums PAID revenue, and lists each enrollment's student.
class ReportService {
    constructor({ report }) {
        this.report = report;
    }

    async buildFinancialReport() {
        const rows = await this.report.fetchReportRows();
        const byCourse = new Map();

        for (const row of rows) {
            if (!byCourse.has(row.course_id)) {
                byCourse.set(row.course_id, { course: row.course_title, revenue: 0, students: [] });
            }
            const entry = byCourse.get(row.course_id);

            // A course with no enrollments produces a single all-null row.
            if (row.enrollment_id == null) continue;

            if (row.payment_status === PaymentStatus.PAID) {
                entry.revenue += row.payment_amount;
            }
            entry.students.push({
                student: row.student_name || 'Unknown',
                paid: row.payment_amount != null ? row.payment_amount : 0,
            });
        }

        return Array.from(byCourse.values());
    }
}

module.exports = { ReportService };
