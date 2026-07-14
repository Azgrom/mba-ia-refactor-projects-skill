// Typed application errors. Each carries the HTTP status and the exact
// client-safe message the transport boundary should emit, so controllers never
// select status codes inline and the error middleware maps them in one place.
class AppError extends Error {
    constructor(message, status) {
        super(message);
        this.name = this.constructor.name;
        this.status = status;
        this.clientMessage = message;
    }
}

class BadRequestError extends AppError {
    constructor(message = 'Bad Request') {
        super(message, 400);
    }
}

class PaymentDeniedError extends AppError {
    constructor(message = 'Pagamento recusado') {
        super(message, 400);
    }
}

class CourseNotFoundError extends AppError {
    constructor(message = 'Curso não encontrado') {
        super(message, 404);
    }
}

class UnauthorizedError extends AppError {
    constructor(message = 'Unauthorized') {
        super(message, 401);
    }
}

module.exports = {
    AppError,
    BadRequestError,
    PaymentDeniedError,
    CourseNotFoundError,
    UnauthorizedError,
};
