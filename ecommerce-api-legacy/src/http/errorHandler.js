const { AppError } = require('../errors');

// Terminal error middleware. Known application errors map to their declared
// status and client-safe message (sent as text to preserve the legacy response
// shape); anything unexpected becomes a generic 500 without leaking internals.
function errorHandler() {
    // eslint-disable-next-line no-unused-vars
    return (err, req, res, next) => {
        if (err instanceof AppError) {
            return res.status(err.status).send(err.clientMessage);
        }
        console.error('Unexpected request failure:', err.message);
        return res.status(500).send('Erro interno');
    };
}

module.exports = { errorHandler };
