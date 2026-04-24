def setup_discrepancy(client):
    # processed but not settled
    payload = {
        "event_id": "rec-1",
        "event_type": "payment_processed",
        "transaction_id": "tx-rec",
        "merchant_id": "m3",
        "merchant_name": "Merchant 3",
        "amount": 300,
        "currency": "INR",
        "timestamp": "2026-01-08T12:11:58.085567+00:00"
    }
    client.post("/events/", json=payload)


def test_reconciliation_summary(client):
    setup_discrepancy(client)

    res = client.get("/reconciliation/summary")

    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_discrepancies(client):
    setup_discrepancy(client)

    res = client.get("/reconciliation/discrepancies")

    assert res.status_code == 200
    assert isinstance(res.json(), list)