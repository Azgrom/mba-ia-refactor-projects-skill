const crypto = require('crypto');

// Adaptive, salted password hashing using Node's built-in scrypt (no external
// dependency). Stored form is `salt:derivedKey` in hex. Verification is
// constant-time. Never log or serialize either the password or the hash.
const KEY_LENGTH = 64;

function hashPassword(password) {
    const salt = crypto.randomBytes(16).toString('hex');
    const derivedKey = crypto.scryptSync(String(password), salt, KEY_LENGTH).toString('hex');
    return `${salt}:${derivedKey}`;
}

function verifyPassword(password, stored) {
    if (typeof stored !== 'string' || !stored.includes(':')) return false;
    const [salt, expected] = stored.split(':');
    const derivedKey = crypto.scryptSync(String(password), salt, KEY_LENGTH).toString('hex');
    const expectedBuffer = Buffer.from(expected, 'hex');
    const actualBuffer = Buffer.from(derivedKey, 'hex');
    if (expectedBuffer.length !== actualBuffer.length) return false;
    return crypto.timingSafeEqual(expectedBuffer, actualBuffer);
}

module.exports = { hashPassword, verifyPassword };
