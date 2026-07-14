// Persistence for the writes a checkout performs: enrollment, payment, and the
// audit log entry. Each method accepts the active connection/transaction so the
// service can run them inside one atomic unit of work.
class CheckoutRepository {
    async createEnrollment(db, userId, courseId) {
        const result = await db.run(
            'INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)',
            [userId, courseId]
        );
        return result.lastID;
    }

    async createPayment(db, enrollmentId, amount, status) {
        const result = await db.run(
            'INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)',
            [enrollmentId, amount, status]
        );
        return result.lastID;
    }

    async createAuditLog(db, action) {
        await db.run(
            "INSERT INTO audit_logs (action, created_at) VALUES (?, datetime('now'))",
            [action]
        );
    }
}

module.exports = { CheckoutRepository };
