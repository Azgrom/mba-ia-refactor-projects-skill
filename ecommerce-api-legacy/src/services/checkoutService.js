const { hashPassword } = require('../domain/password');
const { PaymentStatus, decidePaymentStatus } = require('../domain/payment');
const { BadRequestError, CourseNotFoundError, PaymentDeniedError } = require('../errors');

// Orchestrates the checkout use case: validate input, resolve the course and
        // user, decide the payment, and persist user + enrollment + payment + audit atomically.
class CheckoutService {
    constructor({ db, users, courses, checkout }) {
        this.db = db;
        this.users = users;
        this.courses = courses;
        this.checkout = checkout;
    }

    async checkoutCourse({ name, email, password, courseId, card }) {
        // Boundary validation: presence plus a string card, so a non-string card
        // can no longer reach String.prototype.startsWith and crash the process.
        if (!name || !email || courseId == null || typeof card !== 'string' || !card) {
            throw new BadRequestError();
        }

        const course = await this.courses.findActiveById(courseId);
        if (!course) throw new CourseNotFoundError();

        const status = decidePaymentStatus(card);
        if (status === PaymentStatus.DENIED) throw new PaymentDeniedError();

        const existingUser = await this.users.findIdByEmail(email);
        const enrollmentId = await this.db.transaction(async (tx) => {
            const userId = existingUser
                ? existingUser.id
                : await this.users.create(name, email, hashPassword(password || '123456'), tx);
            const enrId = await this.checkout.createEnrollment(tx, userId, courseId);
            await this.checkout.createPayment(tx, enrId, course.price, status);
            await this.checkout.createAuditLog(tx, `Checkout curso ${courseId} por ${userId}`);
            return enrId;
        });

        return { msg: 'Sucesso', enrollment_id: enrollmentId };
    }
}

module.exports = { CheckoutService };
