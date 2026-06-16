db = db.getSiblingDB('ride_hailing_ops');

db.createCollection('support_tickets');
db.createCollection('fraud_cases');
db.createCollection('rider_app_sessions');

db.support_tickets.createIndex({ support_ticket_id: 1 }, { unique: true });
db.support_tickets.createIndex({ city_id: 1, event_time: -1 });

db.fraud_cases.createIndex({ fraud_case_id: 1 }, { unique: true });
db.fraud_cases.createIndex({ city_id: 1, risk_band: 1, event_time: -1 });

db.rider_app_sessions.createIndex({ session_id: 1 }, { unique: true });
db.rider_app_sessions.createIndex({ rider_id: 1, event_time: -1 });
