def test_ingest_event(client):
    payload = {
        "event_id": "test-1",
        "event_type": "payment_initiated",
        "transaction_id": "tx-1",
        "merchant_id": "m1",
        "merchant_name": "Test Merchant",
        "amount": 1000,
        "currency": "INR",
        "timestamp": "2026-01-08T12:11:58.085567+00:00"
    }

    res = client.post("/events/", json=payload)

    assert res.status_code == 200
    assert "successfully" in res.json()["message"]


def test_duplicate_event(client):
    payload = {
        "event_id": "dup-1",
        "event_type": "payment_initiated",
        "transaction_id": "tx-dup",
        "merchant_id": "m1",
        "merchant_name": "Test Merchant",
        "amount": 500,
        "currency": "INR",
        "timestamp": "2026-01-08T12:11:58.085567+00:00"
    }

    res1 = client.post("/events/", json=payload)
    res2 = client.post("/events/", json=payload)

    assert res2.status_code == 200
    assert "Duplicate" in res2.json()["message"]