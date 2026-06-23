"""Transfers between accounts in a ledger."""
from accounts import Account, InsufficientFunds  # noqa: F401


class Ledger:
    def __init__(self):
        self._accounts = {}

    def open(self, name):
        account = Account(name)
        self._accounts[name] = account
        return account

    def get(self, name):
        return self._accounts[name]

    def transfer(self, src, dst, amount):
        """Move amount from src to dst. Must respect the source's available
        funds (held money cannot be transferred)."""
        source = self._accounts[src]
        dest = self._accounts[dst]
        source.withdraw(amount)
        dest.deposit(amount)
