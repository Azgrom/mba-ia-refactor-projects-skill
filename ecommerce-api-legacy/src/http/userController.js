// Transport mapping for user administration. The legacy response text (which
// documents that dependent rows are left behind) is preserved unchanged.
function deleteUserController(userService) {
    return async (req, res) => {
        await userService.deleteUser(req.params.id);
        res.send('Usuário deletado, mas as matrículas e pagamentos ficaram sujos no banco.');
    };
}

module.exports = { deleteUserController };
