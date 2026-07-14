// Wraps an async route handler so a rejected promise is forwarded to Express's
// terminal error middleware instead of crashing the process.
function asyncHandler(handler) {
    return (req, res, next) => Promise.resolve(handler(req, res, next)).catch(next);
}

module.exports = { asyncHandler };
