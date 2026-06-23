"""A minimal account with holds.

A "hold" reserves part of the balance (e.g. a pending charge). Money that is
held is still in the balance but must NOT be spendable: the available funds are
balance minus the sum of holds, and withdrawals must respect that.
"""


class InsufficientFunds(Exception):
    pass


class Account:
    def __init__(self, name):
        self.name = name
        self.balance = 0
        self._holds = []

    def deposit(self, amount):
        if amount < 0:
            raise ValueError("amount must be >= 0")
        self.balance += amount

    def available(self):
        """Spendable funds: balance minus everything currently held."""
        return self.balance - sum(self._holds)

    def place_hold(self, amount):
        if amount < 0:
            raise ValueError("amount must be >= 0")
        if amount > self.available():
            raise InsufficientFunds(self.name)
        self._holds.append(amount)

    def release_hold(self, amount):
        self._holds.remove(amount)

    def withdraw(self, amount):
        if amount < 0:
            raise ValueError("amount must be >= 0")
        if amount > self.balance:
            raise InsufficientFunds(self.name)
        self.balance -= amount
