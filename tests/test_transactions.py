def setup_transaction(client):
    # initiate
    client.post("/events/", json={
        "event_id": "tx-init",
        "event_type": "payment_initiated",
        "transaction_id": "tx-setup",
        "merchant_id": "m2",
        "merchant_name": "Merchant 2",
        "amount": 200,
        "currency": "INR",
        "timestamp": "2026-01-08T12:11:58+00:00"
    })

    # process
    client.post("/events/", json={
        "event_id": "tx-proc",
        "event_type": "payment_processed",
        "transaction_id": "tx-setup",
        "merchant_id": "m2",
        "merchant_name": "Merchant 2",
        "amount": 200,
        "currency": "INR",
        "timestamp": "2026-01-08T12:12:00+00:00"
    })


def test_list_transactions(client):
    setup_transaction(client)

    res = client.get("/transactions/")
    assert res.status_code == 200
    assert "data" in res.json()


def test_filter_transactions(client):
    setup_transaction(client)

    res = client.get("/transactions/?merchant_id=m2")

    assert res.status_code == 200
    for tx in res.json()["data"]:
        assert tx["merchant_id"] == "m2"


def test_transaction_detail(client):
    setup_transaction(client)

    res = client.get("/transactions/tx-setup")

    assert res.status_code == 200
    data = res.json()

    assert "transaction" in data
    assert "events" in data