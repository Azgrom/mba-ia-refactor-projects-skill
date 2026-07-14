// Application service for user administration.
class UserService {
    constructor({ users }) {
        this.users = users;
    }

    async deleteUser(id) {
        await this.users.deleteById(id);
    }
}

module.exports = { UserService };
