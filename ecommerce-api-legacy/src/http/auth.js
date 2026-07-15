const crypto = require('crypto');
const { UnauthorizedError } = require('../errors');

// Guards administrative endpoints. A caller must present the admin token via
// `Authorization: Bearer <token>`; anonymous or wrong-token requests are
// rejected with 401 before reaching the handler.
function requireAdmin(config) {
    const expected = Buffer.from(String(config.adminToken));

    return (req, res, next) => {
        const header = req.get('authorization') || '';
        const match = header.match(/^Bearer\s+(.+)$/i);
        if (!match) return next(new UnauthorizedError());

        const provided = Buffer.from(match[1]);
        if (
            provided.length !== expected.length ||
            !crypto.timingSafeEqual(provided, expected)
        ) {
            return next(new UnauthorizedError());
        }
        return next();
    };
}

module.exports = { requireAdmin };
