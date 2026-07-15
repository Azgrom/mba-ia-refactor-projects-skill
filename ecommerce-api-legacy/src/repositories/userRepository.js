// Persistence for users. Query construction and projection live here, never in
// controllers or services.
class UserRepository {
    constructor(db) {
        this.db = db;
    }

    findIdByEmail(email) {
        return this.db.get('SELECT id FROM users WHERE email = ?', [email]);
    }

    async create(name, email, passwordHash, db = this.db) {
        const result = await db.run(
            'INSERT INTO users (name, email, pass) VALUES (?, ?, ?)',
            [name, email, passwordHash]
        );
        return result.lastID;
    }

    async deleteById(id) {
        const result = await this.db.run('DELETE FROM users WHERE id = ?', [id]);
        return result.changes;
    }
}

module.exports = { UserRepository };
