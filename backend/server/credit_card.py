import logging
import json
import hashlib
from lib import connect_to_db, requires_auth
from flask import request
from flask import Blueprint

credit_card_routes = Blueprint('credit_card', __name__)
logger = logging.getLogger('waitress')


@credit_card_routes.route('/credit_card/destination/all_events', methods=['POST'])
@requires_auth
def destination_all_events():
    db = connect_to_db()

    request_body_as_text = request.get_data(as_text=True)

    db.execute(
        f"""
                INSERT INTO event_credit_card (
                    request_body, 
                    request_body_hash
                )
                VALUES (%s, %s)
                ON CONFLICT (request_body_hash) DO NOTHING;
                """,
        (
            request_body_as_text,
            hashlib.md5(request_body_as_text.encode('utf-8')).hexdigest(),
        )
    )

    return {"result": {"success": {}}}


@credit_card_routes.route('/credit_card/latest_events', methods=['GET'])
def latest_events():
    db = connect_to_db()

    db.execute("SELECT request_body FROM event_credit_card  ORDER BY id DESC LIMIT 10;")
    rows = db.fetchall()
    column_names = [col[0] for col in db.description]

    results = []
    for row in rows:
        row_key_value_pairs = dict(zip(column_names, row))
        payload_object = (json.loads(row_key_value_pairs['request_body']))['payload']
        results.append({
            "partition_key": payload_object["partition_key"],
            "serial_column": payload_object["serial_column"],
            "occurred_at": payload_object["occurred_at"],
            "event_type": payload_object["event_type"],
            "event_payload": payload_object["event_payload"]
        })

    return results

 
@credit_card_routes.route('/credit_card/destination/fraud_review', methods=['POST'])
@requires_auth
def destination_fraud_review():
    row = json.loads(request.get_data(as_text=True))
    event_payload_data = json.loads(row["payload"]["event_payload"])

    if event_payload_data["amount"] < 4000:
        return {"result": {"success": {}}}

    db = connect_to_db()
    db.execute(
        f"""
                INSERT INTO credit_card_fraud (
                    account_number,
                    amount,
                    authorization_id,
                    currency,
                    event_id
                )
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (event_id) DO NOTHING;
                """,
        (
            event_payload_data["account_number"],
            event_payload_data["amount"],
            event_payload_data["authorization_id"],
            event_payload_data["currency"],
            event_payload_data["event_id"],
        )
    )

    return {"result": {"success": {}}}


@credit_card_routes.route('/credit_card/fraud_review', methods=['GET'])
def fraud_review():
    db = connect_to_db()

    db.execute(
        "SELECT account_number, authorization_id, event_id, currency, amount AS amount_flagged  FROM credit_card_fraud  ORDER BY id DESC LIMIT 200;")
    rows = db.fetchall()
    column_names = [col[0] for col in db.description]

    results = []
    for row in rows:
        results.append(dict(zip(column_names, row)))

    return results
