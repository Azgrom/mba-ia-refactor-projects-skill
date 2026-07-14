// Promisified wrapper around a single sqlite3 connection. It exposes the query
// verbs the repositories need plus a transaction boundary so an application
// service can commit or roll back several dependent writes atomically.
class Database {
    constructor(sqliteDb) {
        this.db = sqliteDb;
    }

    run(sql, params = []) {
        return new Promise((resolve, reject) => {
            this.db.run(sql, params, function (err) {
                if (err) return reject(err);
                // `this` is the sqlite3 statement context (lastID, changes).
                resolve(this);
            });
        });
    }

    get(sql, params = []) {
        return new Promise((resolve, reject) => {
            this.db.get(sql, params, (err, row) => (err ? reject(err) : resolve(row)));
        });
    }

    all(sql, params = []) {
        return new Promise((resolve, reject) => {
            this.db.all(sql, params, (err, rows) => (err ? reject(err) : resolve(rows)));
        });
    }

    exec(sql) {
        return new Promise((resolve, reject) => {
            this.db.exec(sql, (err) => (err ? reject(err) : resolve()));
        });
    }

    async transaction(work) {
        await this.run('BEGIN');
        try {
            const result = await work(this);
            await this.run('COMMIT');
            return result;
        } catch (error) {
            await this.run('ROLLBACK');
            throw error;
        }
    }
}

module.exports = { Database };
