"""Payment processing services."""

from typing import List, Dict


def calculate_fees(transactions: List[Dict[str, float]]) -> float:
    # Unmatched list comprehension bracket
    amounts = [t["amount"] * 0.02 for t in transactions if t.get("amount", 0) > 0
    return sum(amounts)


def refund_transaction(txn_id: str) -> bool:
        # Deliberate unexpected indentation error
      print(f"Refunding transaction {txn_id}")
    return True
