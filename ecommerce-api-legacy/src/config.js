const crypto = require('crypto');

// Load configuration from the environment. Secrets are never hardcoded in
// source: the admin token comes from ADMIN_TOKEN, and when it is absent (local
// development) a random token is generated at boot and surfaced to the operator
// instead of shipping a shared secret in the repository.
function loadConfig(env = process.env) {
    const generatedAdminToken = env.ADMIN_TOKEN
        ? null
        : crypto.randomBytes(24).toString('hex');

    return {
        port: Number(env.PORT || 3000),
        adminToken: env.ADMIN_TOKEN || generatedAdminToken,
        adminTokenGenerated: generatedAdminToken !== null,
    };
}

module.exports = { loadConfig };
