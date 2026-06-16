-- TC-04: inject historical churn-signal data directly into gold.fact_trip
-- RIDER-CHURN-001: 5 trips in early May 2026, then returned 2026-06-16 (42-day gap)
-- RIDER-ACTIVE-001: consistent June trips (class diversity - not churned)

INSERT INTO gold.fact_trip (
    trip_fact_key, trip_id, rider_key, driver_key, vehicle_key, city_key,
    time_key, promotion_key, payment_method_key,
    final_fare, surge_multiplier, promotion_amount, platform_fee, driver_payout,
    completed_flag, cancelled_flag, created_at
)
VALUES
('tc04churn001a', 'TC04-TRIP-C01', md5('TC04-RIDER-CHURN-001'), md5('DRV-A'), md5('VEH-A'), md5('NYC'),
 2026050109, md5('0'), md5('tc04'), 14.00, 1.0, 0, 3.50, 10.50, 1, 0, '2026-05-01 09:00:00'),
('tc04churn001b', 'TC04-TRIP-C02', md5('TC04-RIDER-CHURN-001'), md5('DRV-A'), md5('VEH-A'), md5('NYC'),
 2026050210, md5('0'), md5('tc04'), 12.50, 1.0, 0, 3.13, 9.37, 1, 0, '2026-05-02 10:00:00'),
('tc04churn001c', 'TC04-TRIP-C03', md5('TC04-RIDER-CHURN-001'), md5('DRV-A'), md5('VEH-A'), md5('NYC'),
 2026050309, md5('0'), md5('tc04'), 11.00, 1.0, 0, 2.75, 8.25, 1, 0, '2026-05-03 09:00:00'),
('tc04churn001d', 'TC04-TRIP-C04', md5('TC04-RIDER-CHURN-001'), md5('DRV-A'), md5('VEH-A'), md5('NYC'),
 2026050408, md5('0'), md5('tc04'), 18.00, 1.0, 0, 4.50, 13.50, 1, 0, '2026-05-04 08:00:00'),
('tc04churn001e', 'TC04-TRIP-C05', md5('TC04-RIDER-CHURN-001'), md5('DRV-A'), md5('VEH-A'), md5('NYC'),
 2026050511, md5('0'), md5('tc04'), 15.00, 1.0, 0, 3.75, 11.25, 1, 0, '2026-05-05 11:00:00'),
('tc04churn001f', 'TC04-TRIP-C06', md5('TC04-RIDER-CHURN-001'), md5('DRV-B'), md5('VEH-B'), md5('NYC'),
 2026061617, md5('0'), md5('tc04'), 22.00, 1.0, 0, 5.50, 16.50, 1, 0, '2026-06-16 17:45:00'),
('tc04active001a', 'TC04-TRIP-A01', md5('TC04-RIDER-ACTIVE-001'), md5('DRV-C'), md5('VEH-C'), md5('CHI'),
 2026061008, md5('0'), md5('tc04'), 16.00, 1.0, 0, 4.00, 12.00, 1, 0, '2026-06-10 08:00:00'),
('tc04active001b', 'TC04-TRIP-A02', md5('TC04-RIDER-ACTIVE-001'), md5('DRV-C'), md5('VEH-C'), md5('CHI'),
 2026061208, md5('0'), md5('tc04'), 13.50, 1.0, 0, 3.38, 10.12, 1, 0, '2026-06-12 08:00:00'),
('tc04active001c', 'TC04-TRIP-A03', md5('TC04-RIDER-ACTIVE-001'), md5('DRV-C'), md5('VEH-C'), md5('CHI'),
 2026061408, md5('0'), md5('tc04'), 17.00, 1.0, 0, 4.25, 12.75, 1, 0, '2026-06-14 08:00:00'),
('tc04active001d', 'TC04-TRIP-A04', md5('TC04-RIDER-ACTIVE-001'), md5('DRV-C'), md5('VEH-C'), md5('CHI'),
 2026061608, md5('0'), md5('tc04'), 19.00, 1.0, 0, 4.75, 14.25, 1, 0, '2026-06-16 08:00:00')
ON CONFLICT DO NOTHING;
