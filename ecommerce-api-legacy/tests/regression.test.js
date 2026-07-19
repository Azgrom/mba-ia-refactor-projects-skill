const assert = require('node:assert/strict');
const http = require('node:http');
const test = require('node:test');

const { buildApp } = require('../src/appFactory');
const { CheckoutService } = require('../src/services/checkoutService');

async function withServer(fn) {
    process.env.ADMIN_TOKEN = 'test-admin-token';
    const { app } = await buildApp();
    const server = await new Promise((resolve, reject) => {
        const srv = app.listen(0, '127.0.0.1');
        srv.once('listening', () => resolve(srv));
        srv.once('error', reject);
    });

    try {
        const { port } = server.address();
        return await fn(port);
    } finally {
        await new Promise((resolve, reject) => {
            server.close((err) => (err ? reject(err) : resolve()));
        });
    }
}

function request(port, method, path, { token } = {}) {
    const headers = {};
    if (token) headers.Authorization = `Bearer ${token}`;

    return new Promise((resolve, reject) => {
        const req = http.request({ hostname: '127.0.0.1', port, method, path, headers }, (res) => {
            let raw = '';
            res.setEncoding('utf8');
            res.on('data', (chunk) => { raw += chunk; });
            res.on('end', () => {
                let body = raw;
                try {
                    body = JSON.parse(raw);
                } catch (_) {
                    // Legacy text responses are valid contracts.
                }
                resolve({ status: res.statusCode, body, raw });
            });
        });
        req.on('error', reject);
        req.end();
    });
}

test('denied checkout for a new user does not create partial user state', async () => {
    const events = [];
    const db = {
        transaction: async (work) => {
            events.push('transaction');
            return work(db);
        },
    };
    const users = {
        findIdByEmail: async () => null,
        create: async () => {
            events.push('user-created');
            return 42;
        },
    };
    const courses = {
        findActiveById: async () => ({ id: 1, price: 997 }),
    };
    const checkout = {
        createEnrollment: async () => {
            events.push('enrollment-created');
            return 10;
        },
        createPayment: async () => events.push('payment-created'),
        createAuditLog: async () => events.push('audit-created'),
    };

    const service = new CheckoutService({ db, users, courses, checkout });

    await assert.rejects(
        () => service.checkoutCourse({
            name: 'Denied User',
            email: 'denied@example.test',
            password: 'secret',
            courseId: 1,
            card: '5111222233334444',
        }),
        { name: 'PaymentDeniedError' }
    );
    assert.deepEqual(events, []);
});

test('financial report accepts a bounded limit while preserving the array response', async () => {
    await withServer(async (port) => {
        const response = await request(port, 'GET', '/api/admin/financial-report?limit=1', {
            token: 'test-admin-token',
        });

        assert.equal(response.status, 200);
        assert.equal(Array.isArray(response.body), true);
        assert.equal(response.body.length, 1);
        assert.deepEqual(Object.keys(response.body[0]), ['course', 'revenue', 'students']);
    });
});

test('financial report rejects invalid bounds as a bad request', async () => {
    await withServer(async (port) => {
        const response = await request(port, 'GET', '/api/admin/financial-report?limit=abc', {
            token: 'test-admin-token',
        });

        assert.equal(response.status, 400);
        assert.equal(response.raw, 'Bad Request');
    });
});
